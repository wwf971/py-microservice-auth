"""
gRPC Authentication Service Implementation
Wraps api.py pure functions for gRPC interface
"""

import logging
import sys
import os
import time
import json
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
    get_username_of_uid,
    get_all_users,
    add_user,
    delete_user,
    issue_jwt_token,
    issue_temp_token,
    get_token_info,
    delete_token,
    revoke_token,
    revoke_token_by_value,
    cleanup_tokens,
    get_jwks,
    get_permission_data,
    update_user_permissions,
    declare_service_permission,
    check_user_permission,
    check_user_service_permission,
    get_public_key,
    verify_jwt_token_with_public_key,
    get_database_list,
    get_current_database_id,
    add_database,
    remove_database,
    update_database,
    change_current_database,
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
        self.engine = None
        self.SessionLocal = None
        self.db_init_error = None
        self.ensure_db_ready()
        logger.info("AuthService (gRPC) initialized")

    def ensure_db_ready(self):
        if self.SessionLocal is not None:
            return True
        try:
            self.engine, self.SessionLocal = init_database(self.config)
            self.db_init_error = None
            return True
        except Exception as e:
            self.db_init_error = str(e)
            logger.error(f"Auth db initialization failed: {e}")
            return False

    def open_session_or_fail(self, context=None):
        if not self.ensure_db_ready():
            message = f"Auth db is not ready: {self.db_init_error}"
            if context is not None:
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                context.set_details(message)
            raise RuntimeError(message)
        return self.SessionLocal()
    
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
        
        session = self.open_session_or_fail(context)
        try:
            is_valid = verify_jwt_token(self.config, session, session_token)
            
            if is_valid:
                public_key = get_public_key(self.config, session)
                result = verify_jwt_token_with_public_key(
                    session_token,
                    public_key,
                    self.config.get('JWT_ALGORITHM', 'RS256'),
                )
                uid = result.get("claims", {}).get("uid")
                username = get_username_of_uid(self.config, session, uid) if uid else ""
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
        
        session = self.open_session_or_fail(context)
        try:
            result = revoke_token_by_value(self.config, session, session_token)
            if not result["success"]:
                return service_pb2.LogoutResponse(
                    success=False,
                    message=result["message"],
                )
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
        session = self.open_session_or_fail(context)
        try:
            users = get_all_users(self.config, session)
            
            # Convert to protobuf format
            user_infos = []
            for user in users:
                user_info = service_pb2.UserInfo(
                    uid=user['uid'],
                    username=user['username'],
                    password_hash=user['password_hash'],
                    jwt_token_ids=user['jwt_token_ids'],
                    permission_codes=user.get('permission_codes', []),
                    service_permissions=[
                        service_pb2.ServicePermissionAssignment(
                            service_id=item.get('service_id', ''),
                            permission_code=item.get('permission_code', 0),
                        )
                        for item in user.get('service_permissions', [])
                    ],
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
        permission_codes = list(request.permission_codes)
        service_permissions = [
            {"service_id": item.service_id, "permission_code": item.permission_code}
            for item in request.service_permissions
        ]
        
        logger.info(f"Add user request for username: {username}")
        
        session = self.open_session_or_fail(context)
        try:
            result = add_user(self.config, session, username, password, permission_codes, service_permissions)
            
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
        
        session = self.open_session_or_fail(context)
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

    def UpdateUserPermissions(self, request, context):
        uid = request.uid
        permission_codes = list(request.permission_codes)
        service_permissions = [
            {"service_id": item.service_id, "permission_code": item.permission_code}
            for item in request.service_permissions
        ]

        session = self.open_session_or_fail(context)
        try:
            result = update_user_permissions(
                self.config,
                session,
                uid,
                permission_codes,
                service_permissions,
            )
            return service_pb2.UpdateUserPermissionsResponse(
                success=result["success"],
                message=result["message"],
            )
        except Exception as e:
            logger.error(f"Error updating permissions for UID {uid}: {e}")
            return service_pb2.UpdateUserPermissionsResponse(
                success=False,
                message=f"Internal error: {str(e)}",
            )
        finally:
            session.close()

    def GetPermissionData(self, request, context):
        session = self.open_session_or_fail(context)
        try:
            data = get_permission_data(self.config, session)
            return service_pb2.GetPermissionDataResponse(
                success=True,
                message="Permission data retrieved",
                permissions=[
                    service_pb2.PermissionMetaInfo(
                        permission_code=item["permission_code"],
                        display_name=item["display_name"],
                        description=item["description"],
                    )
                    for item in data["permissions"]
                ],
                permission_includes=[
                    service_pb2.PermissionIncludeInfo(
                        permission_code=item["permission_code"],
                        permission_code_included=item["permission_code_included"],
                    )
                    for item in data["permission_includes"]
                ],
                service_permissions=[
                    service_pb2.ServicePermissionMetaInfo(
                        service_id=item["service_id"],
                        permission_code=item["permission_code"],
                        display_name=item["display_name"],
                        description=item["description"],
                    )
                    for item in data["service_permissions"]
                ],
                service_permission_includes=[
                    service_pb2.ServicePermissionIncludeInfo(
                        service_id=item["service_id"],
                        permission_code=item["permission_code"],
                        permission_code_included=item["permission_code_included"],
                    )
                    for item in data["service_permission_includes"]
                ],
            )
        except Exception as e:
            logger.error(f"Error getting permission data: {e}")
            return service_pb2.GetPermissionDataResponse(
                success=False,
                message=f"Internal error: {str(e)}",
            )
        finally:
            session.close()

    def DeclareServicePermission(self, request, context):
        session = self.open_session_or_fail(context)
        try:
            result = declare_service_permission(
                self.config,
                session,
                request.service_id,
                request.permission_code,
                request.display_name,
                request.description,
                list(request.permission_codes_included),
            )
            return service_pb2.DeclareServicePermissionResponse(
                success=result["success"],
                message=result["message"],
            )
        except Exception as e:
            logger.error(f"Error declaring service permission: {e}")
            return service_pb2.DeclareServicePermissionResponse(
                success=False,
                message=f"Internal error: {str(e)}",
            )
        finally:
            session.close()

    def CheckPermission(self, request, context):
        session = self.open_session_or_fail(context)
        try:
            if request.service_id:
                is_permitted = check_user_service_permission(
                    self.config,
                    session,
                    request.uid,
                    request.service_id,
                    request.permission_code,
                )
            else:
                is_permitted = check_user_permission(
                    self.config,
                    session,
                    request.uid,
                    request.permission_code,
                )
            return service_pb2.CheckPermissionResponse(
                success=True,
                message="Permission checked",
                permitted=is_permitted,
            )
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return service_pb2.CheckPermissionResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                permitted=False,
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
        
        session = self.open_session_or_fail(context)
        try:
            jti, jwt_token, _expires_at = issue_jwt_token(self.config, session, uid=uid)
            
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
        
        session = self.open_session_or_fail(context)
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
                    expires_at=token_info['expires_at'],
                    status_code=token_info['status_code'],
                    revoked_at=token_info.get('revoked_at') or 0,
                    created_at_timezone=token_info.get('created_at_timezone') or 0,
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
                    expires_at=0,
                    status_code=0,
                    revoked_at=0,
                    created_at_timezone=0,
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
                expires_at=0,
                status_code=0,
                revoked_at=0,
                created_at_timezone=0,
            )
        finally:
            session.close()

    def DeleteToken(self, request, context):
        jti = request.jti
        logger.info(f"Delete token request for JTI: {jti}")

        session = self.open_session_or_fail(context)
        try:
            result = delete_token(self.config, session, jti=jti)
            return service_pb2.DeleteTokenResponse(
                success=result["success"],
                message=result["message"],
            )
        except Exception as e:
            logger.error(f"Error deleting token for JTI {jti}: {e}")
            return service_pb2.DeleteTokenResponse(
                success=False,
                message=f"Internal error: {str(e)}",
            )
        finally:
            session.close()

    def RevokeToken(self, request, context):
        jti = request.jti
        logger.info(f"Revoke token request for JTI: {jti}")

        session = self.open_session_or_fail(context)
        try:
            result = revoke_token(self.config, session, jti=jti)
            return service_pb2.RevokeTokenResponse(
                success=result["success"],
                message=result["message"],
            )
        except Exception as e:
            logger.error(f"Error revoking token for JTI {jti}: {e}")
            return service_pb2.RevokeTokenResponse(
                success=False,
                message=f"Internal error: {str(e)}",
            )
        finally:
            session.close()

    def CleanupTokens(self, request, context):
        session = self.open_session_or_fail(context)
        try:
            result = cleanup_tokens(self.config, session)
            return service_pb2.CleanupTokensResponse(
                success=result["success"],
                message=result["message"],
                expired_count=result.get("expired_count", 0),
                retained_count=result.get("retained_count", 0),
                deleted_count=result.get("deleted_count", 0),
            )
        except Exception as e:
            logger.error(f"Error cleaning tokens: {e}")
            return service_pb2.CleanupTokensResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                expired_count=0,
                retained_count=0,
                deleted_count=0,
            )
        finally:
            session.close()

    def IssueTempToken(self, request, context):
        session = self.open_session_or_fail(context)
        try:
            result = issue_temp_token(self.config, session, request.token)
            return service_pb2.IssueTempTokenResponse(
                success=result["success"],
                message=result["message"],
                token=result.get("token", ""),
                expires_at=result.get("expires_at", 0),
            )
        except Exception as e:
            logger.error(f"Error issuing temporary token: {e}")
            return service_pb2.IssueTempTokenResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                token="",
                expires_at=0,
            )
        finally:
            session.close()

    def GetJwks(self, request, context):
        session = self.open_session_or_fail(context)
        try:
            jwks = get_jwks(self.config, session)
            return service_pb2.GetJwksResponse(
                success=True,
                message="JWKS retrieved",
                jwks_json=json.dumps(jwks),
            )
        except Exception as e:
            logger.error(f"Error getting JWKS: {e}")
            return service_pb2.GetJwksResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                jwks_json="",
            )
        finally:
            session.close()
    
    def GetDatabaseList(self, request, context):
        """Get list of all database connections"""
        try:
            databases = get_database_list(self.config)
            current_db_id = get_current_database_id(self.config)
            
            # Convert to protobuf format
            db_infos = []
            for db in databases:
                db_info = service_pb2.DatabaseInfo(
                    id=db.get('id', 0),
                    name=db.get('name', ''),
                    type=db.get('type', ''),
                    host=db.get('host', '') if db.get('host') else '',
                    port=db.get('port', 0) if db.get('port') else 0,
                    database=db.get('database', '') if db.get('database') else '',
                    username=db.get('username', '') if db.get('username') else '',
                    password=db.get('password', '') if db.get('password') else '',
                    path=db.get('path', '') if db.get('path') else '',
                    is_default=db.get('is_default', False),
                    is_removable=db.get('is_removable', True)
                )
                db_infos.append(db_info)
            
            return service_pb2.GetDatabaseListResponse(
                success=True,
                message="Database list retrieved successfully",
                databases=db_infos,
                current_database_id=current_db_id
            )
        except Exception as e:
            logger.error(f"Error getting database list: {e}")
            return service_pb2.GetDatabaseListResponse(
                success=False,
                message=f"Error: {str(e)}",
                databases=[],
                current_database_id=0
            )
    
    def AddDatabase(self, request, context):
        """Add a new database connection"""
        try:
            kwargs = {}
            if request.host:
                kwargs['host'] = request.host
            if request.port:
                kwargs['port'] = request.port
            if request.database:
                kwargs['database'] = request.database
            if request.username:
                kwargs['username'] = request.username
            if request.password:
                kwargs['password'] = request.password
            if request.path:
                kwargs['path'] = request.path
            
            result = add_database(self.config, request.name, request.type, **kwargs)
            
            if result['success']:
                db = result['database']
                db_info = service_pb2.DatabaseInfo(
                    id=db.get('id', 0),
                    name=db.get('name', ''),
                    type=db.get('type', ''),
                    host=db.get('host', '') if db.get('host') else '',
                    port=db.get('port', 0) if db.get('port') else 0,
                    database=db.get('database', '') if db.get('database') else '',
                    username=db.get('username', '') if db.get('username') else '',
                    password=db.get('password', '') if db.get('password') else '',
                    path=db.get('path', '') if db.get('path') else '',
                    is_default=db.get('is_default', False),
                    is_removable=db.get('is_removable', True)
                )
                return service_pb2.AddDatabaseResponse(
                    success=True,
                    message=result['message'],
                    database=db_info
                )
            else:
                return service_pb2.AddDatabaseResponse(
                    success=False,
                    message=result['message']
                )
        except Exception as e:
            logger.error(f"Error adding database: {e}")
            return service_pb2.AddDatabaseResponse(
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def RemoveDatabase(self, request, context):
        """Remove a database connection"""
        try:
            result = remove_database(self.config, request.db_id)
            return service_pb2.RemoveDatabaseResponse(
                success=result['success'],
                message=result['message']
            )
        except Exception as e:
            logger.error(f"Error removing database: {e}")
            return service_pb2.RemoveDatabaseResponse(
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def UpdateDatabase(self, request, context):
        """Update database connection details"""
        try:
            kwargs = {}
            if request.name:
                kwargs['name'] = request.name
            if request.host:
                kwargs['host'] = request.host
            if request.port:
                kwargs['port'] = request.port
            if request.database:
                kwargs['database'] = request.database
            if request.username:
                kwargs['username'] = request.username
            if request.password:
                kwargs['password'] = request.password
            if request.path:
                kwargs['path'] = request.path
            
            result = update_database(self.config, request.db_id, **kwargs)
            
            if result['success'] and result.get('database'):
                db = result['database']
                db_info = service_pb2.DatabaseInfo(
                    id=db.get('id', 0),
                    name=db.get('name', ''),
                    type=db.get('type', ''),
                    host=db.get('host', '') if db.get('host') else '',
                    port=db.get('port', 0) if db.get('port') else 0,
                    database=db.get('database', '') if db.get('database') else '',
                    username=db.get('username', '') if db.get('username') else '',
                    password=db.get('password', '') if db.get('password') else '',
                    path=db.get('path', '') if db.get('path') else '',
                    is_default=db.get('is_default', False),
                    is_removable=db.get('is_removable', True)
                )
                return service_pb2.UpdateDatabaseResponse(
                    success=True,
                    message=result['message'],
                    database=db_info
                )
            else:
                return service_pb2.UpdateDatabaseResponse(
                    success=result['success'],
                    message=result['message']
                )
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            return service_pb2.UpdateDatabaseResponse(
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def ChangeCurrentDatabase(self, request, context):
        """Change the currently active database"""
        try:
            result = change_current_database(self.config, request.db_id)
            
            if result['success']:
                # Trigger database reconnection
                logger.info(f"Database switched to ID {request.db_id}. Reinitializing connection...")
                self.engine = None
                self.SessionLocal = None
                self.db_init_error = None
                if not self.ensure_db_ready():
                    return service_pb2.ChangeCurrentDatabaseResponse(
                        success=False,
                        message=f"Database switched, but connection failed: {self.db_init_error}"
                    )
                logger.info("Database connection reinitialized successfully")
            
            return service_pb2.ChangeCurrentDatabaseResponse(
                success=result['success'],
                message=result['message']
            )
        except Exception as e:
            logger.error(f"Error changing database: {e}")
            return service_pb2.ChangeCurrentDatabaseResponse(
                success=False,
                message=f"Error: {str(e)}"
            )
