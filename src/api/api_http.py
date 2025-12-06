"""
HTTP/Flask Authentication API Implementation
Calls gRPC service instead of directly accessing database
"""

import logging
import grpc
from flask import request, jsonify

import sys
import os

# Import proto
import sys, os, pathlib
dir_path_current = os.path.dirname(os.path.realpath(__file__)) + "/"
dir_path_parent = pathlib.Path(dir_path_current).parent.absolute().__str__() + "/"
dir_path_proto = dir_path_parent + "proto/"
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  import proto.service_pb2 as service_pb2
  import proto.service_pb2_grpc as service_pb2_grpc
else:
  sys.path.insert(0, dir_path_proto)
  import service_pb2
  import service_pb2_grpc

logger = logging.getLogger(__name__)


def register_auth_routes(app, config):
    """
    Register authentication routes with Flask app.
    HTTP server calls gRPC server for actual logic.
    
    Args:
        app: Flask application instance
        config: Configuration dictionary
    """
    
    # Get gRPC server address
    grpc_port = config.get('PORT_SERVICE_GRPC', 16200)
    grpc_address = f'localhost:{grpc_port}'
    
    logger.info(f"HTTP API will call gRPC at {grpc_address}")
    
    @app.route('/api/login', methods=['POST'])
    def issue_jwt_token():
        """
        Login endpoint - issues JWT token
        Calls gRPC Login method
        """
        try:
            data = request.json
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return jsonify({
                    "code": -1,
                    "message": "Username and password required",
                    "data": None
                }), 400
            
            # Call gRPC
            with grpc.insecure_channel(grpc_address) as channel:
                stub = service_pb2_grpc.AuthServiceStub(channel)
                response = stub.Login(
                    service_pb2.LoginRequest(username=username, password=password)
                )
            
            if response.success:
                return jsonify({
                    "code": 0,
                    "message": response.message,
                    "data": {
                        "session_token": response.session_token,
                        "expires_at": response.expires_at
                    }
                }), 200
            else:
                return jsonify({
                    "code": -1,
                    "message": response.message,
                    "data": None
                }), 401
                
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e}")
            return jsonify({
                "code": -2,
                "message": f"Service error: {e.code()}",
                "data": None
            }), 500
        except Exception as e:
            logger.error(f"Error in login: {e}")
            return jsonify({
                "code": -3,
                "message": str(e),
                "data": None
            }), 500
    
    @app.route('/api/verify_jwt_token', methods=['POST'])
    def verify_jwt_token():
        """
        Validate session token endpoint
        Calls gRPC ValidateSession method
        """
        try:
            data = request.json
            session_token = data.get('session_token')
            
            if not session_token:
                return jsonify({
                    "code": -1,
                    "message": "Session token required",
                    "data": None
                }), 400
            
            # Call gRPC
            with grpc.insecure_channel(grpc_address) as channel:
                stub = service_pb2_grpc.AuthServiceStub(channel)
                response = stub.ValidateSession(
                    service_pb2.ValidateSessionRequest(session_token=session_token)
                )
            
            if response.valid:
                return jsonify({
                    "code": 0,
                    "message": response.message,
                    "data": {
                        "valid": True,
                        "username": response.username
                    }
                }), 200
            else:
                return jsonify({
                    "code": -1,
                    "message": response.message,
                    "data": {
                        "valid": False
                    }
                }), 401
                
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e}")
            return jsonify({
                "code": -2,
                "message": f"Service error: {e.code()}",
                "data": None
            }), 500
        except Exception as e:
            logger.error(f"Error in verify_jwt_token: {e}")
            return jsonify({
                "code": -3,
                "message": str(e),
                "data": None
            }), 500
    
    @app.route('/api/logout', methods=['POST'])
    def logout():
        """
        Logout endpoint - revokes session
        Calls gRPC Logout method
        """
        try:
            data = request.json
            session_token = data.get('session_token')
            
            if not session_token:
                return jsonify({
                    "code": -1,
                    "message": "Session token required",
                    "data": None
                }), 400
            
            # Call gRPC
            with grpc.insecure_channel(grpc_address) as channel:
                stub = service_pb2_grpc.AuthServiceStub(channel)
                response = stub.Logout(
                    service_pb2.LogoutRequest(session_token=session_token)
                )
            
            if response.success:
                return jsonify({
                    "code": 0,
                    "message": response.message,
                    "data": None
                }), 200
            else:
                return jsonify({
                    "code": -1,
                    "message": response.message,
                    "data": None
                }), 400
                
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e}")
            return jsonify({
                "code": -2,
                "message": f"Service error: {e.code()}",
                "data": None
            }), 500
        except Exception as e:
            logger.error(f"Error in logout: {e}")
            return jsonify({
                "code": -3,
                "message": str(e),
                "data": None
            }), 500
    
    logger.info("Auth routes registered with Flask app")
