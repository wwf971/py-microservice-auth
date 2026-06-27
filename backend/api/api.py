"""
Authentication API - Business logic layer.
Uses api_db for database operations.
"""

from __future__ import annotations

import bcrypt
import time
import uuid

# Import database layer
from api.api_db import (
    init_database,
    gen_uid,
    db_get_user_by_username,
    db_get_user_by_uid,
    db_add_user,
    db_delete_user,
    db_store_jwt_token,
    db_get_jwt_token,
    db_delete_jwt_token,
    db_revoke_jwt_token,
    db_cleanup_jwt_tokens,
    db_get_all_users,
    db_get_user_tokens,
    db_get_permission_meta,
    db_get_permission_include,
    db_get_user_permissions,
    db_set_user_permissions,
    db_get_service_permission_meta,
    db_get_service_permission_include,
    db_get_user_service_permissions,
    db_set_user_service_permissions,
    db_upsert_service_permission_meta,
    db_set_service_permission_include,
    db_get_active_key_pair,
    db_store_key_pair,
    db_get_key_pair_by_id,
)
from api.permission import (
    has_permission,
    has_service_permission,
    validate_service_id,
)


def login_user(config, username: str, password: str) -> dict:
    """
    Authenticate user with username and password, return JWT token.
    
    Args:
        config: Configuration dictionary
        username: Username
        password: Plain text password
        
    Returns:
        dict: {"success": bool, "message": str, "token": str or None, "expires_at": int or None}
    """
    engine, SessionLocal = init_database(config)
    session = SessionLocal()
    
    try:
        # Find user by username
        user = db_get_user_by_username(session, username)
        
        if not user:
            return {
                "success": False,
                "message": "Invalid username or password",
                "token": None,
                "expires_at": None
            }
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return {
                "success": False,
                "message": "Invalid username or password",
                "token": None,
                "expires_at": None
            }
        
        # Generate JWT token
        _jti, token, expires_at = issue_jwt_token(config, session, user.uid)
        
        return {
            "success": True,
            "message": "Login successful",
            "token": token,
            "expires_at": expires_at
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Login error: {str(e)}",
            "token": None,
            "expires_at": None
        }
    finally:
        session.close()


def add_user(config, session, username: str, password: str, permission_codes: list[int] | None = None, service_permissions: list[dict] | None = None) -> dict:
    """
    Add a new user to the database with hashed password.
    
    Args:
        config: Configuration dictionary
        session: Database session
        username: Username
        password: Plain text password
        
    Returns:
        dict: {"success": bool, "message": str, "uid": int or None}
    """
    if not username or not password:
        return {
            "success": False,
            "message": "Username and password are required",
            "uid": None
        }
    
    # Check if user already exists
    existing_user = db_get_user_by_username(session, username)
    if existing_user:
        return {
            "success": False,
            "message": f"User '{username}' already exists",
            "uid": None
        }
    
    try:
        # Hash the password
        bcrypt_rounds = config.get('BCRYPT_ROUNDS', 12)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=bcrypt_rounds))
        
        # Generate unique uid
        uid = gen_uid(config, session)
        
        # Add user to database
        db_add_user(config, session, username, password_hash.decode('utf-8'), uid)
        db_set_user_permissions(session, uid, permission_codes or [])
        db_set_user_service_permissions(session, uid, service_permissions or [])
        
        return {
            "success": True,
            "message": f"User '{username}' created successfully",
            "uid": uid
        }
    except Exception as e:
        session.rollback()
        return {
            "success": False,
            "message": f"Error creating user: {str(e)}",
            "uid": None
        }



def get_uid_of_username(config, session, username: str) -> int:
    """
    Get uid from username.
    
    Args:
        config: Configuration dictionary
        session: Database session
        username: Username to look up
        
    Returns:
        int: uid if found, -1 if not found
    """
    user = db_get_user_by_username(session, username)
    if user:
        return user.uid
    return -1

def get_username_of_uid(config, session, uid: int) -> str:
    """
    Get username from uid.
    
    Args:
        config: Configuration dictionary
        session: Database session
        uid: User ID to look up
        
    Returns:
        str: username if found, None if not found
    """
    user = db_get_user_by_uid(session, uid)
    if user:
        return user.name
    return None


def delete_user(config, session, username: str=None, uid: int=None) -> dict:
    """
    Delete a user. Provide either username or uid.
    
    Args:
        config: Configuration dictionary
        session: Database session
        username: Username to delete
        uid: User ID to delete
        
    Returns:
        dict: {"success": bool, "message": str}
    """
    if not username and not uid:
        return {
            "success": False,
            "message": "Username or UID is required"
        }
    
    try:
        identifier = f"username '{username}'" if username else f"UID {uid}"
        
        success = db_delete_user(session, username=username, uid=uid)
        
        if success:
            return {
                "success": True,
                "message": f"User with {identifier} deleted successfully"
            }
        else:
            return {
                "success": False,
                "message": f"User with {identifier} not found"
            }
    except Exception as e:
        session.rollback()
        return {
            "success": False,
            "message": f"Error deleting user: {str(e)}"
        }

def generate_rsa_key_pair():
    """
    Generate a new RSA key pair for JWT signing.
    
    Returns:
        tuple: (private_key_pem, public_key_pem) as strings
    """
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Serialize private key to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Get public key and serialize to PEM format
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem


def get_or_create_key_pair(session):
    """
    Get active key pair from database, or generate and store a new one if none exists.
    
    Args:
        session: Database session
        
    Returns:
        tuple: (private_key_pem, public_key_pem) as strings
    """
    from datetime import datetime, timezone
    
    # Try to get existing active key pair
    key_pair = db_get_active_key_pair(session)
    
    if key_pair:
        return key_pair.private_key, key_pair.public_key
    
    # No key pair exists, generate new one
    private_key, public_key = generate_rsa_key_pair()
    
    # Get current time and timezone
    now = datetime.now(timezone.utc)
    created_at = int(now.timestamp())
    # Get timezone offset in hours
    local_now = datetime.now()
    utc_now = datetime.utcnow()
    timezone_offset = int((local_now - utc_now).total_seconds() / 3600)
    # Clamp to -12 to +12
    timezone_offset = max(-12, min(12, timezone_offset))
    
    # Store in database
    db_store_key_pair(session, private_key, public_key, created_at, timezone_offset)
    
    return private_key, public_key


def get_private_key(config, session):
    """
    Get the private key for JWT signing.
    First tries config, then falls back to database.
    
    Args:
        config: Configuration dictionary
        session: Database session
        
    Returns:
        str: Private key in PEM format
    """
    # Try config first
    private_key = config.get('JWT_PRIVATE_KEY')
    
    if private_key:
        # Load from file if it's a path
        if not private_key.strip().startswith('-----BEGIN'):
            try:
                with open(private_key, 'r') as f:
                    return f.read()
            except:
                pass  # Fall through to database
        else:
            return private_key
    
    # Fall back to database
    private_key, _ = get_or_create_key_pair(session)
    return private_key


def get_public_key(config, session):
    """
    Get the public key for JWT verification.
    First tries config, then falls back to database.
    
    Args:
        config: Configuration dictionary
        session: Database session
        
    Returns:
        str: Public key in PEM format
    """
    # Try config first
    public_key = config.get('JWT_PUBLIC_KEY')
    
    if public_key:
        # Load from file if it's a path
        if not public_key.strip().startswith('-----BEGIN'):
            try:
                with open(public_key, 'r') as f:
                    return f.read()
            except:
                pass  # Fall through to database
        else:
            return public_key
    
    # Fall back to database
    _, public_key = get_or_create_key_pair(session)
    return public_key


def get_jwks(config, session) -> dict:
    import base64
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    public_key_pem = get_public_key(config, session)
    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValueError("JWKS is only supported for RSA public keys")

    numbers = public_key.public_numbers()

    def base64url_uint(value: int) -> str:
        byte_length = (value.bit_length() + 7) // 8
        value_bytes = value.to_bytes(byte_length, "big")
        return base64.urlsafe_b64encode(value_bytes).decode("ascii").rstrip("=")

    key_pair = db_get_active_key_pair(session)
    kid = str(key_pair.id) if key_pair else "active"
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": kid,
                "alg": config.get("JWT_ALGORITHM", "RS256"),
                "n": base64url_uint(numbers.n),
                "e": base64url_uint(numbers.e),
            }
        ]
    }


def issue_jwt_token(config, session, uid: int) -> tuple:
    """
    Issue JWT token for a user.
    
    Args:
        config: Configuration dictionary
        session: Database session
        uid: User ID
        
    Returns:
        tuple: (jti: str, token: str, expires_at: int)
    """
    import jwt
    
    # Generate unique JWT ID
    jti = str(uuid.uuid4())
    
    # Calculate expiration
    expiration_hours = config.get('JWT_EXPIRATION_HOURS', 24)
    created_at = int(time.time())
    expires_at = created_at + (expiration_hours * 3600)
    
    # Create JWT claims
    claims = {
        'uid': uid,
        'jti': jti,
        'iat': created_at,  # issued at
        'exp': expires_at  # expiration
    }
    
    # Get private key
    private_key = get_private_key(config, session)
    algorithm = config.get('JWT_ALGORITHM', 'RS256')
    
    # Generate token
    token = jwt.encode(claims, private_key, algorithm=algorithm)
    
    # Get timezone offset
    from datetime import datetime
    local_now = datetime.now()
    utc_now = datetime.utcnow()
    timezone_offset = int((local_now - utc_now).total_seconds() / 3600)
    timezone_offset = max(-12, min(12, timezone_offset))
    
    # Store token in database
    db_store_jwt_token(session, jti, uid, token, created_at, expires_at, timezone_offset)
    
    return jti, token, expires_at


def issue_temp_token(config, session, token: str) -> dict:
    public_key = get_public_key(config, session)
    algorithm = config.get("JWT_ALGORITHM", "RS256")
    result = verify_jwt_token_with_public_key(token, public_key, algorithm)
    if not result["valid"]:
        return {"success": False, "message": "Invalid token", "token": "", "expires_at": 0}

    claims = result["claims"] or {}
    jti = claims.get("jti")
    if claims.get("token_type") == "temp" or not jti:
        return {"success": False, "message": "Stored token required", "token": "", "expires_at": 0}

    token_record = db_get_jwt_token(session, jti)
    if not token_record or token_record.status_code <= 0:
        return {"success": False, "message": "Invalid token", "token": "", "expires_at": 0}

    user = db_get_user_by_uid(session, claims.get("uid"))
    if not user:
        return {"success": False, "message": "User not found", "token": "", "expires_at": 0}

    import jwt
    created_at = int(time.time())
    expires_at = created_at + int(config.get("JWT_TEMP_TOKEN_EXPIRATION_SECONDS", 900))
    claims = {
        "uid": user.uid,
        "iat": created_at,
        "exp": expires_at,
        "token_type": "temp",
    }
    private_key = get_private_key(config, session)
    algorithm = config.get("JWT_ALGORITHM", "RS256")
    temp_token = jwt.encode(claims, private_key, algorithm=algorithm)
    return {
        "success": True,
        "message": "Temporary token issued",
        "token": temp_token,
        "expires_at": expires_at,
    }

def verify_jwt_token_with_public_key(jwt_token: str, public_key: str, algorithm: str = "RS256") -> dict:
    """
    Verify JWT token using a public key (no database required).
    This function can be exposed to other microservices for token verification.
    
    Args:
        jwt_token: JWT token string to verify
        public_key: Public key in PEM format (string or file path)
        algorithm: JWT algorithm (default: RS256)
        
    Returns:
        dict: {
            "valid": bool,
            "claims": dict or None,
            "error": str or None,
            "expired": bool
        }
    """
    import jwt as pyjwt
    
    try:
        # Check if public_key is a file path
        if public_key and not public_key.strip().startswith('-----BEGIN'):
            try:
                with open(public_key, 'r') as f:
                    public_key = f.read()
            except:
                pass  # Assume it's already a PEM string
        
        # Decode and verify token
        claims = pyjwt.decode(
            jwt_token,
            public_key,
            algorithms=[algorithm]
        )
        
        # Check expiration manually (jwt.decode already checks, but let's be explicit)
        exp = claims.get('exp', 0)
        current_time = int(time.time())
        
        if exp < current_time:
            return {
                "valid": False,
                "claims": None,
                "error": "Token expired",
                "expired": True
            }
        
        return {
            "valid": True,
            "claims": claims,
            "error": None,
            "expired": False
        }
        
    except pyjwt.ExpiredSignatureError:
        return {
            "valid": False,
            "claims": None,
            "error": "Token expired",
            "expired": True
        }
    except pyjwt.InvalidTokenError as e:
        return {
            "valid": False,
            "claims": None,
            "error": f"Invalid token: {str(e)}",
            "expired": False
        }
    except Exception as e:
        return {
            "valid": False,
            "claims": None,
            "error": f"Verification error: {str(e)}",
            "expired": False
        }


def get_uid_from_token(jwt_token: str, public_key: str, algorithm: str = "RS256") -> int:
    """
    Extract UID from JWT token without database access.
    Convenience function for other microservices.
    
    Args:
        jwt_token: JWT token string
        public_key: Public key in PEM format
        algorithm: JWT algorithm (default: RS256)
        
    Returns:
        int: UID if valid, None otherwise
    """
    result = verify_jwt_token_with_public_key(jwt_token, public_key, algorithm)
    
    if result["valid"] and result["claims"]:
        return result["claims"].get("uid")
    
    return None


def verify_jwt_token(config, session, jwt_token: str) -> bool:
    """
    Verify JWT token with database revocation check.
    For internal use - checks both cryptographic validity and revocation status.
    
    Args:
        config: Configuration dictionary
        session: Database session
        jwt_token: JWT token string
        
    Returns:
        bool: True if valid and not revoked, False otherwise
    """
    public_key = get_public_key(config, session)
    algorithm = config.get('JWT_ALGORITHM', 'RS256')

    result = verify_jwt_token_with_public_key(jwt_token, public_key, algorithm)
    
    if not result["valid"]:
        return False
    
    # Check if token is revoked in database
    claims = result["claims"]
    jti = claims.get("jti")
    token_type = claims.get("token_type")

    if token_type == "temp":
        return True

    if jti:
        token_record = db_get_jwt_token(session, jti)
        if not token_record or token_record.status_code <= 0:
            return False
    else:
        return False
    
    return True

def get_token_user(config, session, jwt_token: str) -> dict | None:
    public_key = get_public_key(config, session)
    algorithm = config.get('JWT_ALGORITHM', 'RS256')
    result = verify_jwt_token_with_public_key(jwt_token, public_key, algorithm)

    if not result["valid"]:
        return None

    claims = result["claims"]
    jti = claims.get("jti")
    token_type = claims.get("token_type")
    uid = claims.get("uid")
    if not uid:
        return None

    if token_type == "temp":
        pass
    elif jti:
        token_record = db_get_jwt_token(session, jti)
        if not token_record or token_record.status_code <= 0:
            return None
    else:
        return None

    user = db_get_user_by_uid(session, uid)
    if not user:
        return None

    return {
        "uid": user.uid,
        "username": user.name,
        "permission_codes": [item.permission_code for item in db_get_user_permissions(session, user.uid)],
        "service_permissions": [
            {"service_id": item.service_id, "permission_code": item.permission_code}
            for item in db_get_user_service_permissions(session, user.uid)
        ],
    }

def get_all_users(config, session) -> list:
    """
    Get all users from database with their JWT tokens.
    
    Args:
        config: Configuration dictionary
        session: Database session
        
    Returns:
        list: List of dicts containing user info
            [{"uid": int, "username": str, "password_hash": str, "jwt_token_ids": [str]}]
    """
    users = db_get_all_users(session)
    result = []
    
    for user in users:
        tokens = db_get_user_tokens(session, user.uid)
        jwt_token_ids = [token.jti for token in tokens]
        
        permission_codes = [item.permission_code for item in db_get_user_permissions(session, user.uid)]
        service_permissions = [
            {"service_id": item.service_id, "permission_code": item.permission_code}
            for item in db_get_user_service_permissions(session, user.uid)
        ]

        result.append({
            "uid": user.uid,
            "username": user.name,
            "password_hash": user.password,
            "jwt_token_ids": jwt_token_ids,
            "permission_codes": permission_codes,
            "service_permissions": service_permissions,
        })
    
    return result


def get_permission_data(config, session) -> dict:
    return {
        "permissions": [
            {
                "permission_code": item.permission_code,
                "display_name": item.display_name,
                "description": item.description,
            }
            for item in db_get_permission_meta(session)
        ],
        "permission_includes": [
            {
                "permission_code": item.permission_code,
                "permission_code_included": item.permission_code_included,
            }
            for item in db_get_permission_include(session)
        ],
        "service_permissions": [
            {
                "service_id": item.service_id,
                "permission_code": item.permission_code,
                "display_name": item.display_name,
                "description": item.description,
            }
            for item in db_get_service_permission_meta(session)
        ],
        "service_permission_includes": [
            {
                "service_id": item.service_id,
                "permission_code": item.permission_code,
                "permission_code_included": item.permission_code_included,
            }
            for item in db_get_service_permission_include(session)
        ],
    }


def update_user_permissions(config, session, uid: int, permission_codes: list[int], service_permissions: list[dict]) -> dict:
    user = db_get_user_by_uid(session, uid)
    if not user:
        return {"success": False, "message": f"User with UID {uid} not found"}

    try:
        db_set_user_permissions(session, uid, permission_codes or [])
        db_set_user_service_permissions(session, uid, service_permissions or [])
        return {"success": True, "message": "User permissions updated"}
    except Exception as e:
        session.rollback()
        return {"success": False, "message": str(e)}


def declare_service_permission(
    config,
    session,
    service_id: str,
    permission_code: int,
    display_name: str,
    description: str,
    permission_codes_included: list[int] | None = None,
) -> dict:
    service_id = (service_id or "").strip()
    if not validate_service_id(service_id):
        return {"success": False, "message": "Invalid service id"}

    if permission_code <= 0:
        return {"success": False, "message": "Permission code must be positive"}

    try:
        db_upsert_service_permission_meta(
            session,
            service_id,
            permission_code,
            display_name or str(permission_code),
            description or "",
        )
        db_set_service_permission_include(session, service_id, permission_code, permission_codes_included or [])
        return {"success": True, "message": "Service permission declared"}
    except Exception as e:
        session.rollback()
        return {"success": False, "message": str(e)}


def check_user_permission(config, session, uid: int, permission_code: int) -> bool:
    permission_codes = [item.permission_code for item in db_get_user_permissions(session, uid)]
    permission_include_by_code = {}
    for item in db_get_permission_include(session):
        permission_include_by_code.setdefault(item.permission_code, []).append(item.permission_code_included)
    return has_permission(permission_codes, permission_code, permission_include_by_code)


def check_user_service_permission(config, session, uid: int, service_id: str, permission_code: int) -> bool:
    service_permissions = [
        {"service_id": item.service_id, "permission_code": item.permission_code}
        for item in db_get_user_service_permissions(session, uid)
    ]
    permission_include_by_service_code = {}
    for item in db_get_service_permission_include(session):
        include_by_code = permission_include_by_service_code.setdefault(item.service_id, {})
        include_by_code.setdefault(item.permission_code, []).append(item.permission_code_included)
    return has_service_permission(
        service_permissions,
        service_id,
        permission_code,
        permission_include_by_service_code,
    )

def get_token_info(config, session, jti: str) -> dict | None:
    """
    Get JWT token information by JTI.
    
    Args:
        config: Configuration dictionary
        session: Database session
        jti: JWT Token ID
        
    Returns:
        dict: Token info dict or None if not found
    """
    token = db_get_jwt_token(session, jti)
    
    if not token:
        return None
    
    return {
        "jti": token.jti,
        "uid": token.uid,
        "token": token.jwt_token,
        "created_at": token.created_at,
        "created_at_timezone": token.created_at_timezone,
        "expires_at": token.expires_at,
        "status_code": token.status_code,
        "revoked_at": token.revoked_at if token.revoked_at else None
    }


def revoke_token(config, session, jti: str) -> dict:
    try:
        is_token_revoked = db_revoke_jwt_token(session, jti)
        if not is_token_revoked:
            return {"success": False, "message": "Token not found"}
        return {"success": True, "message": "Token revoked"}
    except Exception as e:
        session.rollback()
        return {"success": False, "message": str(e)}


def revoke_token_by_value(config, session, token: str) -> dict:
    import jwt

    try:
        claims = jwt.decode(token, options={"verify_signature": False})
        jti = claims.get("jti")
        if not jti:
            return {"success": False, "message": "Token id not found"}
        return revoke_token(config, session, jti)
    except Exception as e:
        session.rollback()
        return {"success": False, "message": str(e)}


def delete_token(config, session, jti: str) -> dict:
    try:
        is_deleted = db_delete_jwt_token(session, jti)
        if not is_deleted:
            return {"success": False, "message": "Token not found"}
        return {"success": True, "message": "Token deleted"}
    except Exception as e:
        session.rollback()
        return {"success": False, "message": str(e)}


def cleanup_tokens(config, session) -> dict:
    try:
        retention_seconds = int(config.get("JWT_TOKEN_RETENTION_SECONDS", 7 * 24 * 3600))
        result = db_cleanup_jwt_tokens(session, retention_seconds)
        return {"success": True, "message": "Token cleanup completed", **result}
    except Exception as e:
        session.rollback()
        return {"success": False, "message": str(e)}


def get_database_list(config) -> list:
    """
    Get list of all database connections.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        list: List of database configurations
    """
    return config.get('DATABASE_LIST', [])


def get_current_database_id(config) -> int:
    """
    Get currently active database ID.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        int: Current database ID
    """
    return config.get('CURRENT_DATABASE_ID', 0)


def add_database(config, name: str, db_type: str, **kwargs) -> dict:
    """
    Add a new database connection to the list.
    
    Args:
        config: Configuration dictionary
        name: Database name/label
        db_type: Database type (sqlite, postgresql, mysql)
        **kwargs: Additional database parameters (host, port, database, username, password, path)
        
    Returns:
        dict: {"success": bool, "message": str, "database": dict or None}
    """
    database_list = config.get('DATABASE_LIST', [])
    
    # Generate new ID
    max_id = max([db.get('id', 0) for db in database_list], default=0)
    new_id = max_id + 1
    
    # Create new database config
    new_db = {
        "id": new_id,
        "name": name,
        "type": db_type.lower(),
        "is_default": False,
        "is_removable": True
    }
    
    if db_type.lower() == 'sqlite':
        new_db.update({
            "path": kwargs.get('path', f'/data/auth_{new_id}.db'),
            "host": None,
            "port": None,
            "database": None,
            "username": None,
            "password": None
        })
    else:
        new_db.update({
            "path": None,
            "host": kwargs.get('host'),
            "port": kwargs.get('port'),
            "database": kwargs.get('database'),
            "username": kwargs.get('username'),
            "password": kwargs.get('password')
        })
    
    database_list.append(new_db)
    config['DATABASE_LIST'] = database_list
    
    return {
        "success": True,
        "message": f"Database '{name}' added successfully",
        "database": new_db
    }


def remove_database(config, db_id: int) -> dict:
    """
    Remove a database connection from the list.
    
    Args:
        config: Configuration dictionary
        db_id: Database ID to remove
        
    Returns:
        dict: {"success": bool, "message": str}
    """
    database_list = config.get('DATABASE_LIST', [])
    
    # Find database
    db_to_remove = None
    for db in database_list:
        if db.get('id') == db_id:
            db_to_remove = db
            break
    
    if not db_to_remove:
        return {
            "success": False,
            "message": f"Database with ID {db_id} not found"
        }
    
    if not db_to_remove.get('is_removable', True):
        return {
            "success": False,
            "message": "Cannot remove the default local database"
        }
    
    # Check if it's the current database
    if config.get('CURRENT_DATABASE_ID') == db_id:
        return {
            "success": False,
            "message": "Cannot remove the currently active database. Switch to another database first."
        }
    
    # Remove database
    database_list = [db for db in database_list if db.get('id') != db_id]
    config['DATABASE_LIST'] = database_list
    
    return {
        "success": True,
        "message": f"Database removed successfully"
    }


def update_database(config, db_id: int, **kwargs) -> dict:
    """
    Update database connection details.
    
    Args:
        config: Configuration dictionary
        db_id: Database ID to update
        **kwargs: Fields to update
        
    Returns:
        dict: {"success": bool, "message": str, "database": dict or None}
    """
    database_list = config.get('DATABASE_LIST', [])
    
    # Find database
    db_to_update = None
    db_index = None
    for i, db in enumerate(database_list):
        if db.get('id') == db_id:
            db_to_update = db
            db_index = i
            break
    
    if not db_to_update:
        return {
            "success": False,
            "message": f"Database with ID {db_id} not found",
            "database": None
        }
    
    # Update allowed fields
    allowed_fields = ['name', 'host', 'port', 'database', 'username', 'password', 'path']
    for field in allowed_fields:
        if field in kwargs:
            db_to_update[field] = kwargs[field]
    
    database_list[db_index] = db_to_update
    config['DATABASE_LIST'] = database_list
    
    return {
        "success": True,
        "message": "Database updated successfully",
        "database": db_to_update
    }


def change_current_database(config, db_id: int) -> dict:
    """
    Change the currently active database.
    This will trigger a database connection restart in the gRPC server.
    
    Args:
        config: Configuration dictionary
        db_id: Database ID to switch to
        
    Returns:
        dict: {"success": bool, "message": str}
    """
    database_list = config.get('DATABASE_LIST', [])
    
    # Check if database exists
    db_exists = any(db.get('id') == db_id for db in database_list)
    
    if not db_exists:
        return {
            "success": False,
            "message": f"Database with ID {db_id} not found"
        }
    
    # Update current database ID
    config['CURRENT_DATABASE_ID'] = db_id
    
    return {
        "success": True,
        "message": f"Switched to database ID {db_id}. Database connection will be restarted."
    }