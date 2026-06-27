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
    grpc_port = config.get('PORT_SERVICE_GRPC', 9532)
    grpc_address = f'localhost:{grpc_port}'
    
    logger.info(f"HTTP API will call gRPC at {grpc_address}")
    
    @app.route('/api/login', methods=['POST'])
    @app.route('/api/token', methods=['POST'])
    def login_endpoint():
        """Login endpoint - authenticates user and returns JWT token"""
        from api.api import login_user
        
        try:
            data = request.json or {}
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return jsonify({
                    "code": -1,
                    "message": "Username and password are required",
                    "data": None
                }), 400
            
            # Authenticate user and get JWT token
            result = login_user(config, username, password)
            
            if result["success"]:
                logger.info(f"HTTP login successful for user: {username}")
                return jsonify({
                    "code": 0,
                    "message": result["message"],
                    "data": {
                        "token": result["token"],
                        "expires_at": result["expires_at"],
                        "username": username
                    }
                }), 200
            else:
                logger.warning(f"HTTP login failed for user: {username} - {result['message']}")
                return jsonify({
                    "code": -1,
                    "message": result["message"],
                    "data": None
                }), 401
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({
                "code": -1,
                "message": f"Internal error: {str(e)}",
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

    @app.route('/api/issue_temp_token', methods=['POST'])
    @app.route('/api/temporary-token', methods=['POST'])
    def issue_temp_token_endpoint():
        try:
            data = request.json or {}
            token = data.get('token') or data.get('session_token')

            if not token:
                return jsonify({
                    "code": -1,
                    "message": "Token required",
                    "data": None
                }), 400

            with grpc.insecure_channel(grpc_address) as channel:
                stub = service_pb2_grpc.AuthServiceStub(channel)
                response = stub.IssueTempToken(
                    service_pb2.IssueTempTokenRequest(token=token)
                )

            if response.success:
                return jsonify({
                    "code": 0,
                    "message": response.message,
                    "data": {
                        "token": response.token,
                        "expires_at": response.expires_at
                    }
                }), 200
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
            logger.error(f"Error in issue_temp_token: {e}")
            return jsonify({
                "code": -3,
                "message": str(e),
                "data": None
            }), 500

    def get_jwks_response():
        try:
            with grpc.insecure_channel(grpc_address) as channel:
                stub = service_pb2_grpc.AuthServiceStub(channel)
                response = stub.GetJwks(service_pb2.GetJwksRequest())
            if not response.success:
                return jsonify({"code": -1, "message": response.message}), 500
            import json
            return jsonify(json.loads(response.jwks_json)), 200
        except Exception as e:
            logger.error(f"Error getting JWKS: {e}")
            return jsonify({"code": -1, "message": str(e)}), 500

    @app.route('/api/jwks', methods=['GET'])
    def get_jwks_api():
        return get_jwks_response()

    @app.route('/.well-known/jwks.json', methods=['GET'])
    def get_jwks_standard():
        return get_jwks_response()
    
    logger.info("Auth routes registered with Flask app")
