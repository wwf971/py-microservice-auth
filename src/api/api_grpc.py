"""
gRPC Authentication Service Implementation
Wraps api.py pure functions for gRPC interface
"""

import logging
import sys
import os
import time
import grpc

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
from api.api import (
    init_database,
    login_user,
    verify_jwt_token,
    get_all_users,
    add_user,
    delete_user,
    issue_jwt_token,
    get_token_info,
)

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
        
        try:
            # Authenticate user and get JWT token
            result = login_user(self.config, username, password)
            
            if result["success"]:
                logger.info(f"✓ Login successful for user: {username}")
                return service_pb2.LoginResponse(
                    success=True,
                    message=result["message"],
                    session_token=result["token"],
                    expires_at=result["expires_at"]
                )
            else:
                logger.warning(f"✗ Login failed for user: {username} - {result['message']}")
                return service_pb2.LoginResponse(
                    success=False,
                    message=result["message"],
                    session_token="",
                    expires_at=0
                )
        except Exception as e:
            logger.error(f"Login error for user {username}: {e}")
            return service_pb2.LoginResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                session_token="",
                expires_at=0
            )
    
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
    
    def IsAlive(self, request, context):
        """Check if server is alive and return config timestamp"""
        return service_pb2.IsAliveResponse(
            alive=True,
            unix_stamp_ms=self.config.get('unix_stamp_ms', 0)
        )
    
    def GetPID(self, request, context):
        """Return process PID"""
        import os
        return service_pb2.GetPIDResponse(
            pid=os.getpid()
        )
    
    def ListUsers(self, request, context):
        """
        List all users with their JWT token IDs.
        For management UI purposes.
        """
        session = self.SessionLocal()
        try:
            users = get_all_users(self.config, session)
            
            # Convert to protobuf format
            user_infos = []
            for user in users:
                user_info = service_pb2.UserInfo(
                    uid=user['uid'],
                    username=user['username'],
                    password_hash=user['password_hash'],
                    jwt_token_ids=user['jwt_token_ids']
                )
                user_infos.append(user_info)
            
            logger.info(f"Listed {len(user_infos)} users")
            return service_pb2.ListUsersResponse(users=user_infos)
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return service_pb2.ListUsersResponse(users=[])
        finally:
            session.close()
    
    def AddUser(self, request, context):
        """
        Add a new user.
        
        Args:
            request: AddUserRequest with username and password
            context: gRPC context
            
        Returns:
            AddUserResponse with success status and UID
        """
        username = request.username
        password = request.password
        
        logger.info(f"Add user request for username: {username}")
        
        session = self.SessionLocal()
        try:
            result = add_user(self.config, session, username, password)
            
            if result["success"]:
                logger.info(f"✓ User '{username}' added with UID {result['uid']}")
                return service_pb2.AddUserResponse(
                    success=True,
                    message=result["message"],
                    uid=result["uid"]
                )
            else:
                logger.warning(f"✗ Failed to add user '{username}': {result['message']}")
                return service_pb2.AddUserResponse(
                    success=False,
                    message=result["message"],
                    uid=0
                )
        except Exception as e:
            logger.error(f"Error adding user '{username}': {e}")
            return service_pb2.AddUserResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                uid=0
            )
        finally:
            session.close()
    
    def DeleteUser(self, request, context):
        """
        Delete a user by UID.
        
        Args:
            request: DeleteUserRequest with uid
            context: gRPC context
            
        Returns:
            DeleteUserResponse with success status
        """
        uid = request.uid
        
        logger.info(f"Delete user request for UID: {uid}")
        
        session = self.SessionLocal()
        try:
            result = delete_user(self.config, session, uid=uid)
            
            if result["success"]:
                logger.info(f"✓ User with UID {uid} deleted")
                return service_pb2.DeleteUserResponse(
                    success=True,
                    message=result["message"]
                )
            else:
                logger.warning(f"✗ Failed to delete user with UID {uid}: {result['message']}")
                return service_pb2.DeleteUserResponse(
                    success=False,
                    message=result["message"]
                )
        except Exception as e:
            logger.error(f"Error deleting user with UID {uid}: {e}")
            return service_pb2.DeleteUserResponse(
                success=False,
                message=f"Internal error: {str(e)}"
            )
        finally:
            session.close()
    
    def IssueToken(self, request, context):
        """
        Issue a new JWT token for a user.
        
        Args:
            request: IssueTokenRequest with uid
            context: gRPC context
            
        Returns:
            IssueTokenResponse with token details
        """
        uid = request.uid
        
        logger.info(f"Issue token request for UID: {uid}")
        
        session = self.SessionLocal()
        try:
            jti, jwt_token = issue_jwt_token(self.config, session, uid=uid)
            
            logger.info(f"✓ Token issued for UID {uid}, JTI: {jti}")
            return service_pb2.IssueTokenResponse(
                success=True,
                message="Token issued successfully",
                jti=jti,
                token=jwt_token
            )
        except Exception as e:
            logger.error(f"Error issuing token for UID {uid}: {e}")
            return service_pb2.IssueTokenResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                jti="",
                token=""
            )
        finally:
            session.close()
    
    def GetTokenInfo(self, request, context):
        """
        Get JWT token information by JTI.
        
        Args:
            request: GetTokenInfoRequest with jti
            context: gRPC context
            
        Returns:
            GetTokenInfoResponse with token details
        """
        jti = request.jti
        
        logger.info(f"Get token info request for JTI: {jti}")
        
        session = self.SessionLocal()
        try:
            token_info = get_token_info(self.config, session, jti=jti)
            
            if token_info:
                logger.info(f"✓ Token info retrieved for JTI: {jti}")
                return service_pb2.GetTokenInfoResponse(
                    success=True,
                    message="Token info retrieved successfully",
                    jti=token_info['jti'],
                    uid=token_info['uid'],
                    token=token_info['token'],
                    created_at=token_info['created_at'],
                    expires_at=token_info['expires_at']
                )
            else:
                logger.warning(f"✗ Token not found for JTI: {jti}")
                return service_pb2.GetTokenInfoResponse(
                    success=False,
                    message="Token not found",
                    jti="",
                    uid=0,
                    token="",
                    created_at=0,
                    expires_at=0
                )
        except Exception as e:
            logger.error(f"Error getting token info for JTI {jti}: {e}")
            return service_pb2.GetTokenInfoResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                jti="",
                uid=0,
                token="",
                created_at=0,
                expires_at=0
            )
        finally:
            session.close()
