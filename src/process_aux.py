#!/usr/bin/env python3
"""
Auxiliary Process - Config Manager and Log Aggregator

This process:
1. Parses and manages config
2. Provides config to other processes via REST API
3. Accepts logs from other servers
4. Monitors and can restart other processes
"""

import logging
import os
import sys
import time
from datetime import datetime, timezone
from flask import Flask, jsonify, request, send_from_directory
import requests

# Add parent directory to path for imports
import sys, os, pathlib
dir_path_current = os.path.dirname(os.path.realpath(__file__)) + "/"
dir_path_parent = pathlib.Path(dir_path_current).parent.absolute().__str__() + "/"
sys.path += [dir_path_parent]

from third_party.utils_python_global._utils_import import _utils_file
from config import compose_config, store_config_to_local_db

class CustomFormatter(logging.Formatter):
    """Custom formatter for timestamp format: 20251206_17382200+09"""
    
    def formatTime(self, record, datefmt=None):
        # Get current time with timezone info
        ct = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone()
        
        # Format: YYYYMMDD_HHMMSSms+TZ
        timestamp = ct.strftime('%Y%m%d_%H%M%S')
        milliseconds = f"{int(record.msecs):02d}"  # Get centiseconds (00-99)
        tz_offset = ct.strftime('%z')  # Format: +0900 or -0500
        tz_offset = tz_offset[:3]  # Convert +0900 to +09
        
        return f"{timestamp}{milliseconds}{tz_offset}"
    
    def format(self, record):
        record.custom_time = self.formatTime(record)
        return super().format(record)


def setup_logging(level=logging.INFO):
    """
    Configure logging with custom timestamp format.
    
    Args:
        level: Logging level (default: logging.INFO)
    """
    handler = logging.StreamHandler()
    handler.setFormatter(CustomFormatter('%(custom_time)s - %(name)s - %(levelname)s - %(message)s'))
    logging.root.addHandler(handler)
    logging.root.setLevel(level)


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global configuration
config_current = None

# Create two Flask apps - one for management UI, one for aux API
app_manage = Flask(__name__)  # Management UI server
app_aux = Flask(__name__)     # Auxiliary API server


def get_db_file_path():
    """Determine database file path based on environment"""
    is_docker = os.getenv('IS_DOCKER', 'true').lower() == 'true'
    if is_docker:
        return "/data/config.db"
    else:
        return dir_path_parent + "data/config.db"


def load_config():
    """Load and compose configuration from all sources"""
    global config_current
    
    try:
        # Log environment variable for debugging
        is_docker_env = os.getenv('IS_DOCKER', 'not-set')
        logger.info(f"IS_DOCKER environment variable: {is_docker_env}")
        
        config_data = compose_config([])
        config_current = config_data.get('config', {})
        
        # Log the actual DATABASE_SQLITE_PATH from config
        logger.info(f"DATABASE_SQLITE_PATH from config: {config_current.get('DATABASE_SQLITE_PATH', 'not-set')}")
        
        # Add unix_stamp_ms - current time in milliseconds
        config_current['unix_stamp_ms'] = int(time.time() * 1000)
        
        # Store config to database
        db_file_path = get_db_file_path()
        logger.info(f"Config database file path: {db_file_path}")
        store_config_to_local_db(config_current, db_file_path)
        
        logger.info(f"Configuration loaded successfully: {len(config_current)} keys, unix_stamp_ms={config_current['unix_stamp_ms']}")
        return config_current
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

# === Auxiliary API Routes (app_aux) ===

@app_aux.route('/config', methods=['GET'])
def get_config():
    """Return current configuration"""
    if config_current is None:
        return jsonify({"code": -1, "message": "Configuration not loaded", "data": None}), 500
    
    return jsonify({"code": 0, "message": "success", "data": config_current}), 200

def write_port_file(port: int):
    """Write PORT_AUX to file so other processes can find it"""
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
    try:
        _utils_file.create_dir_for_file_path(port_file)
        with open(port_file, 'w') as f:
            f.write(str(port))
        logger.info(f"Wrote PORT_AUX={port} to {port_file}")
    except Exception as e:
        logger.error(f"Failed to write port file: {e}")
        raise


@app_aux.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"code": 0, "message": "ok", "data": None}), 200


@app_aux.route('/pid', methods=['GET'])
def get_pid():
    """Return process PID"""
    return jsonify({"code": 0, "message": "ok", "data": {"pid": os.getpid()}}), 200


@app_aux.route('/log', methods=['POST'])
def receive_log():
    """Receive logs from other processes"""
    try:
        log_data = request.json
        logger.info(f"Received log from {log_data.get('source', 'unknown')}: {log_data.get('message', '')}")
        return jsonify({"code": 0, "message": "ok", "data": None}), 200
    except Exception as e:
        logger.error(f"Failed to process log: {e}")
        return jsonify({"code": -1, "message": str(e), "data": None}), 400


@app_aux.route('/trigger_update/<service>', methods=['POST'])
def trigger_update_endpoint(service: str):
    """Endpoint to trigger config update for a service"""
    success = trigger_config_update(service)
    if success:
        return jsonify({"code": 0, "message": "ok", "data": {"service": service}}), 200
    else:
        return jsonify({"code": -1, "message": "Failed to trigger update", "data": {"service": service}}), 500


# === Management UI Routes (app_manage) ===
# Serves on PORT_MANAGE (16202) with /manage/ prefix

@app_manage.route('/manage/')
@app_manage.route('/manage/<path:path>')
def serve_manage_ui(path='index.html'):
    """Serve management UI built with React"""
    manage_build_dir = os.path.join(os.path.dirname(__file__), 'manage', 'build')
    try:
        return send_from_directory(manage_build_dir, path)
    except:
        # Fallback to index.html for client-side routing
        return send_from_directory(manage_build_dir, 'index.html')


@app_manage.route('/manage/login', methods=['POST'])
def manage_login():
    """Management login endpoint"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        # Get management credentials from config
        manage_username = config_current.get('MANAGE_USERNAME')
        manage_password = config_current.get('MANAGE_PASSWORD')
        
        if not manage_username or not manage_password:
            return jsonify({
                "code": -1,
                "message": "Management credentials not configured. Please set MANAGE_USERNAME and MANAGE_PASSWORD in config.",
                "data": None
            }), 500
        
        # Validate credentials
        if username == manage_username and password == manage_password:
            logger.info(f"✓ Management login successful for user: {username}")
            # TODO: Generate proper token instead of simple string
            token = f"mgmt_{username}_{int(time.time())}"
            
            return jsonify({
                "code": 0,
                "message": "Login successful",
                "data": {
                    "token": token,
                    "username": username
                }
            }), 200
        else:
            logger.warning(f"✗ Management login failed for user: {username}")
            return jsonify({
                "code": -1,
                "message": "Invalid username or password",
                "data": None
            }), 401
            
    except Exception as e:
        logger.error(f"Error in manage_login: {e}")
        return jsonify({
            "code": -2,
            "message": str(e),
            "data": None
        }), 500


def check_server_alive(service: str):
    """
    Check if a service is alive and return its config unix_stamp_ms
    
    Args:
        service: 'grpc' or 'http'
        
    Returns:
        tuple: (is_alive: bool, unix_stamp_ms: int or None)
    """
    if service not in ['grpc', 'http']:
        logger.error(f"Invalid service: {service}")
        return False, None
    
    try:
        # Determine the port based on service
        if service == 'grpc':
            port = config_current.get('PORT_SERVICE_GRPC', 50051)
            check_port = port + 10000  # is_alive endpoint on grpc_port + 10000
        else:
            port = config_current.get('PORT_SERVICE_HTTP', 8000)
            check_port = port  # is_alive endpoint on same port for http
        
        # Send is_alive request
        url = f"http://localhost:{check_port}/is_alive"
        response = requests.get(url, timeout=2)
        
        if response.status_code == 200:
            data = response.json()
            unix_stamp_ms = data.get('unix_stamp_ms', None)
            logger.info(f"{service} server is alive with unix_stamp_ms={unix_stamp_ms}")
            return True, unix_stamp_ms
        else:
            logger.warning(f"{service} server is_alive check failed: HTTP {response.status_code}")
            return False, None
            
    except Exception as e:
        logger.debug(f"{service} server is_alive check failed: {e}")
        return False, None


def get_service_pid(service: str):
    """
    Get PID of a service.
    
    Args:
        service: 'grpc' or 'http'
        
    Returns:
        int: PID if successful, None otherwise
    """
    if service not in ['grpc', 'http']:
        logger.error(f"Invalid service: {service}")
        return None
    
    try:
        # Determine the port based on service
        if service == 'grpc':
            port = config_current.get('PORT_SERVICE_GRPC', 16200)
            check_port = port + 10000  # PID endpoint on grpc_port + 10000
        else:
            port = config_current.get('PORT_SERVICE_HTTP', 16201)
            check_port = port  # PID endpoint on same port for http
        
        # Send PID request
        url = f"http://localhost:{check_port}/pid"
        response = requests.get(url, timeout=2)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0:
                pid = data.get('data', {}).get('pid')
                logger.info(f"{service} PID: {pid}")
                return pid
        
        return None
            
    except Exception as e:
        logger.debug(f"Error getting PID for {service}: {e}")
        return None


def trigger_config_update(service: str):
    """
    Trigger config update for a specific service (grpc or http).
    If API call fails, wait 1 second and kill by PID.
    
    Args:
        service: 'grpc' or 'http'
    """
    if service not in ['grpc', 'http']:
        logger.error(f"Invalid service: {service}")
        return False
    
    try:
        # Determine the port based on service
        if service == 'grpc':
            port = config_current.get('PORT_SERVICE_GRPC')
        else:
            port = config_current.get('PORT_SERVICE_HTTP')
        
        if not port:
            logger.error(f"Port not configured for {service}")
            return False
        
        # First, try to get the PID
        pid = get_service_pid(service)
        
        # Send config_update request
        url = f"http://localhost:{port}/config_update"
        response = requests.post(url, timeout=5)
        
        if response.status_code == 200:
            logger.info(f"Successfully triggered config update for {service}")
            return True
        else:
            logger.warning(f"Failed to trigger config update for {service}: {response.status_code}")
            
            # If API failed and we have PID, kill by PID
            if pid:
                logger.info(f"Waiting 1 second before killing {service} by PID...")
                time.sleep(1)
                try:
                    os.kill(pid, 15)  # SIGTERM
                    logger.info(f"Sent SIGTERM to {service} (PID: {pid})")
                    return True
                except Exception as kill_error:
                    logger.error(f"Failed to kill {service} by PID: {kill_error}")
                    return False
            
            return False
            
    except Exception as e:
        logger.error(f"Error triggering config update for {service}: {e}")
        
        # Try to kill by PID as fallback
        if pid:
            logger.info(f"API call failed, waiting 1 second before killing {service} by PID...")
            time.sleep(1)
            try:
                os.kill(pid, 15)  # SIGTERM
                logger.info(f"Sent SIGTERM to {service} (PID: {pid})")
                return True
            except Exception as kill_error:
                logger.error(f"Failed to kill {service} by PID: {kill_error}")
        
        return False


def check_and_restart_servers_if_needed():
    """
    Check if grpc/http servers are alive and verify their config timestamps.
    If timestamps don't match, kill them so supervisor can restart.
    """
    logger.info("Checking if servers need restart due to config timestamp mismatch...")
    
    current_unix_stamp = config_current.get('unix_stamp_ms')
    
    # Check both servers
    for service in ['grpc', 'http']:
        is_alive, server_unix_stamp = check_server_alive(service)
        
        if is_alive:
            if server_unix_stamp != current_unix_stamp:
                logger.warning(
                    f"{service} server has mismatched config timestamp "
                    f"(server: {server_unix_stamp}, current: {current_unix_stamp}). "
                    f"Triggering restart..."
                )
                trigger_config_update(service)
            else:
                logger.info(f"{service} server config timestamp matches - no restart needed")
        else:
            logger.info(f"{service} server is not yet alive - will start normally")


def main():
    """Main entry point for auxiliary process"""
    logger.info("Starting auxiliary process...")
    
    # Load configuration
    load_config()
    
    # Get ports from config
    port_aux = config_current.get('PORT_AUX', 16203)
    port_manage = config_current.get('PORT_MANAGE', 16202)
    
    # Write port to file
    write_port_file(port_aux)
    
    # Wait a bit for servers to potentially start
    logger.info("Waiting 3 seconds for servers to initialize...")
    time.sleep(3)
    
    # Check if servers are alive and restart if timestamps don't match
    check_and_restart_servers_if_needed()
    
    # Start both Flask servers in separate threads
    import threading
    from werkzeug.serving import make_server
    
    # Create servers
    aux_server = make_server('0.0.0.0', port_aux, app_aux, threaded=True)
    manage_server = make_server('0.0.0.0', port_manage, app_manage, threaded=True)
    
    # Start auxiliary API server in thread
    aux_thread = threading.Thread(
        target=aux_server.serve_forever,
        daemon=True
    )
    aux_thread.start()
    logger.info(f"Auxiliary API server started on port {port_aux}")
    
    # Start management UI server in main thread
    logger.info(f"Management UI server starting on port {port_manage}")
    try:
        manage_server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
        aux_server.shutdown()
        manage_server.shutdown()


if __name__ == '__main__':
    main()
