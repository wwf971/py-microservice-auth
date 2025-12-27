#!/usr/bin/env python3
"""
gRPC Service Server

This server:
1. Waits for auxiliary server to be ready
2. Fetches configuration from auxiliary server
3. Starts the gRPC authentication service
4. Handles config_update requests by terminating
"""

import logging
import os
import sys
import time
from concurrent import futures
import grpc
import requests

# Add parent directory to path for imports
dir_path_current = os.path.dirname(os.path.abspath(__file__))
dir_path_third_party_global = os.path.join(dir_path_current, "third_party", "utils_python_global")
sys.path.insert(0, dir_path_current)
sys.path.insert(0, dir_path_third_party_global)

# Import the generated protobuf code
proto_path = os.path.join(os.path.dirname(__file__), 'proto')
sys.path.insert(0, proto_path)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  import proto.service_pb2 as service_pb2
  import proto.service_pb2_grpc as service_pb2_grpc
else:
  import service_pb2
  import service_pb2_grpc

# Import our service implementation
from api.api_grpc import AuthServiceImplementation
from utils import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global config
config_current = None


def wait_for_aux_port():
    """Wait for auxiliary server to write its port to file"""
    # Use relative path for dev, absolute for Docker
    is_docker = os.getenv('IS_DOCKER', 'true').lower() == 'true'
    if is_docker:
        data_dir = "/data"
    else:
        # Relative to project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        data_dir = os.path.join(project_root, "data")
    
    port_file = os.path.join(data_dir, "aux_port.txt")
    logger.info(f"server_grpc: Waiting for server_aux to write its port to file: {port_file}")
    
    while not os.path.exists(port_file):
        time.sleep(1)
    
    # Read port
    with open(port_file, 'r') as f:
        port = int(f.read().strip())
    
    logger.info(f"server_grpc: Found server_aux on port: {port}")
    return port


def fetch_config(aux_port: int, max_retries: int = 30):
    """
    Fetch configuration from auxiliary server
    
    Args:
        aux_port: Port of auxiliary server
        max_retries: Maximum number of retry attempts
    
    Returns:
        Configuration dictionary
    """
    url = f"http://localhost:{aux_port}/config"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                resp_data = response.json()
                if resp_data.get('code') == 0:
                    config = resp_data.get('data', {})
                    logger.info(f"Successfully fetched configuration ({len(config)} keys)")
                    return config
                else:
                    logger.warning(f"server_grpc: Failed to fetch config (attempt {attempt + 1}/{max_retries}): {resp_data.get('message')}")
            else:
                logger.warning(f"server_grpc: Failed to fetch config (attempt {attempt + 1}/{max_retries}): HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"server_grpc: Failed to fetch config (attempt {attempt + 1}/{max_retries}): {e}")
        
        time.sleep(2)
    
    raise RuntimeError(f"server_grpc: Failed to fetch configuration after {max_retries} attempts")


class ConfigUpdateServicer(service_pb2_grpc.AuthServiceServicer):
    """Extended servicer that includes config update handling"""
    
    def __init__(self, config):
        self.auth_service = AuthServiceImplementation(config)
        self.shutdown_event = None
    
    def set_shutdown_event(self, event):
        """Set the shutdown event for config updates"""
        self.shutdown_event = event
    
    def ConfigUpdate(self, request, context):
        """Handle config update request by terminating the server"""
        logger.info("server_grpc: Received config_update request - terminating server")
        
        if self.shutdown_event:
            self.shutdown_event.set()
        
        # Exit immediately.
        # grpc server will be relaunched by supervisor.
        sys.exit(0)
    
    # Delegate auth methods to the actual implementation
    def Login(self, request, context):
        return self.auth_service.Login(request, context)
    
    def ValidateSession(self, request, context):
        return self.auth_service.ValidateSession(request, context)
    
    def Logout(self, request, context):
        return self.auth_service.Logout(request, context)
    
    def IsAlive(self, request, context):
        return self.auth_service.IsAlive(request, context)
    
    def GetPID(self, request, context):
        return self.auth_service.GetPID(request, context)
    
    def ListUsers(self, request, context):
        return self.auth_service.ListUsers(request, context)
    
    def AddUser(self, request, context):
        return self.auth_service.AddUser(request, context)
    
    def DeleteUser(self, request, context):
        return self.auth_service.DeleteUser(request, context)
    
    def IssueToken(self, request, context):
        return self.auth_service.IssueToken(request, context)
    
    def GetTokenInfo(self, request, context):
        return self.auth_service.GetTokenInfo(request, context)
    
    def GetDatabaseList(self, request, context):
        return self.auth_service.GetDatabaseList(request, context)
    
    def AddDatabase(self, request, context):
        return self.auth_service.AddDatabase(request, context)
    
    def RemoveDatabase(self, request, context):
        return self.auth_service.RemoveDatabase(request, context)
    
    def UpdateDatabase(self, request, context):
        return self.auth_service.UpdateDatabase(request, context)
    
    def ChangeCurrentDatabase(self, request, context):
        return self.auth_service.ChangeCurrentDatabase(request, context)


def serve():
    """Start the gRPC server"""
    global config_current
    
    logger.info("server_grpc: Starting gRPC service server...")
    
    # Wait for auxiliary server
    aux_port = wait_for_aux_port()
    
    # Fetch configuration
    config_current = fetch_config(aux_port)
    
    # Get gRPC port from config
    grpc_port = config_current.get('PORT_SERVICE_GRPC', 50051)
    
    # Create server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Create and register servicer with config
    servicer = ConfigUpdateServicer(config_current)
    service_pb2_grpc.add_AuthServiceServicer_to_server(servicer, server)
    
    # Bind to port
    server.add_insecure_port(f'[::]:{grpc_port}')
    
    # Start server
    server.start()
    logger.info(f"server_grpc: Started on port {grpc_port}")
    
    try:
        # Wait for termination
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("server_grpc: Received keyboard interrupt, shutting down...")
        server.stop(0)


if __name__ == '__main__':
    serve()
