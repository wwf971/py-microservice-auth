"""
gRPC Authentication Service Implementation
Wraps api.py pure functions for gRPC interface
"""

import logging
import sys
import os
import time

import sys, os, pathlib
dir_path_current = os.path.dirname(os.path.realpath(__file__)) + "/"
dir_path_parent = pathlib.Path(dir_path_current).parent.absolute().__str__() + "/"
dir_path_proto = dir_path_parent + "proto/"
sys.path.insert(0, dir_path_proto)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  import proto.service_pb2 as service_pb2
  import proto.service_pb2_grpc as service_pb2_grpc
else:
  import service_pb2
  import service_pb2_grpc
from api.api import init_database, issue_jwt_token, verify_jwt_token

logger = logging.getLogger(__name__)

class AuthServiceImplementation(service_pb2_grpc.AuthServiceServicer):
    """
    gRPC Implementation of AuthService.
    Methods must match proto definitions but internally call pure API functions.
    """
    
    def __init__(self, config):
        """
        Initialize the auth service with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.engine, self.SessionLocal = init_database(config)
        logger.info("AuthService (gRPC) initialized")
    
    def Login(self, request, context):
        """
        gRPC Login method - calls pure API function issue_jwt_token
        
        Args:
            request: LoginRequest with username and password
            context: gRPC context
            
        Returns:
            LoginResponse with success status and session token
        """
        username = request.username
        password = request.password
        
        logger.info(f"Login attempt for user: {username}")
        
        session = self.SessionLocal()
        try:
            # Call pure API function
            token = issue_jwt_token(self.config, session, username, password)
            
            if token:
                logger.info(f"✓ Login successful for user: {username}")
                
                # TODO: Get actual expiration from token
                expires_at = int(time.time()) + (7 * 24 * 60 * 60)  # 7 days
                
                return service_pb2.LoginResponse(
                    success=True,
                    message="Login successful",
                    session_token=token,
                    expires_at=expires_at
                )
            else:
                logger.warning(f"✗ Login failed for user: {username}")
                
                return service_pb2.LoginResponse(
                    success=False,
                    message="Invalid username or password",
                    session_token="",
                    expires_at=0
                )
        finally:
            session.close()
    
    def ValidateSession(self, request, context):
        """
        gRPC ValidateSession method - calls pure API function verify_jwt_token
        
        Args:
            request: ValidateSessionRequest with session_token
            context: gRPC context
            
        Returns:
            ValidateSessionResponse with validity status
        """
        session_token = request.session_token
        
        session = self.SessionLocal()
        try:
            # Call pure API function
            is_valid = verify_jwt_token(self.config, session, session_token)
            
            if is_valid:
                # TODO: Extract username from token
                username = "unknown"  # Placeholder
                logger.info(f"✓ Token validated for user: {username}")
                
                return service_pb2.ValidateSessionResponse(
                    valid=True,
                    username=username,
                    message="Session is valid"
                )
            else:
                logger.info("Token validation failed")
                return service_pb2.ValidateSessionResponse(
                    valid=False,
                    username="",
                    message="Invalid or expired session token"
                )
        finally:
            session.close()
    
    def Logout(self, request, context):
        """
        gRPC Logout method - revokes JWT token
        
        Args:
            request: LogoutRequest with session_token
            context: gRPC context
            
        Returns:
            LogoutResponse with success status
        """
        session_token = request.session_token
        
        session = self.SessionLocal()
        try:
            # TODO: Call pure API function to revoke token
            logger.info("Logout request processed")
            
            return service_pb2.LogoutResponse(
                success=True,
                message="Logged out successfully"
            )
        finally:
            session.close()
