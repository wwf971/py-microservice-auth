"""
Authentication API - Business logic layer.
Uses api_db for database operations.
"""

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
    db_get_all_users,
    db_get_user_tokens,
    db_get_active_key_pair,
    db_store_key_pair,
    db_get_key_pair_by_id,
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
        token, expires_at = issue_jwt_token(config, session, user.uid)
        
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


def add_user(config, session, username: str, password: str) -> dict:
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


def issue_jwt_token(config, session, uid: int) -> tuple:
    """
    Issue JWT token for a user.
    
    Args:
        config: Configuration dictionary
        session: Database session
        uid: User ID
        
    Returns:
        tuple: (jti: str, token: str) - JWT ID and token
    """
    import jwt
    
    # Generate unique JWT ID
    jti = str(uuid.uuid4())
    
    # Calculate expiration
    expiration_hours = config.get('JWT_EXPIRATION_HOURS', 24)
    created_at = int(time.time())
    expires_at = created_at + (expiration_hours * 3600)
    
    # Create JWT payload
    payload = {
        'uid': uid,
        'jti': jti,
        'iat': created_at,  # issued at
        'exp': expires_at  # expiration
    }
    
    # Get private key
    private_key = get_private_key(config, session)
    algorithm = config.get('JWT_ALGORITHM', 'RS256')
    
    # Generate token
    token = jwt.encode(payload, private_key, algorithm=algorithm)
    
    # Get timezone offset
    from datetime import datetime
    local_now = datetime.now()
    utc_now = datetime.utcnow()
    timezone_offset = int((local_now - utc_now).total_seconds() / 3600)
    timezone_offset = max(-12, min(12, timezone_offset))
    
    # Store token in database
    db_store_jwt_token(session, jti, uid, token, created_at, expires_at, timezone_offset)
    
    return jti, token

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
            "payload": dict or None,
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
        payload = pyjwt.decode(
            jwt_token,
            public_key,
            algorithms=[algorithm]
        )
        
        # Check expiration manually (jwt.decode already checks, but let's be explicit)
        exp = payload.get('exp', 0)
        current_time = int(time.time())
        
        if exp < current_time:
            return {
                "valid": False,
                "payload": None,
                "error": "Token expired",
                "expired": True
            }
        
        return {
            "valid": True,
            "payload": payload,
            "error": None,
            "expired": False
        }
        
    except pyjwt.ExpiredSignatureError:
        return {
            "valid": False,
            "payload": None,
            "error": "Token expired",
            "expired": True
        }
    except pyjwt.InvalidTokenError as e:
        return {
            "valid": False,
            "payload": None,
            "error": f"Invalid token: {str(e)}",
            "expired": False
        }
    except Exception as e:
        return {
            "valid": False,
            "payload": None,
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
    
    if result["valid"] and result["payload"]:
        return result["payload"].get("uid")
    
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
    # Get public key from config
    public_key = config.get('JWT_PUBLIC_KEY')
    algorithm = config.get('JWT_ALGORITHM', 'RS256')
    
    if not public_key:
        import logging
        logging.error("JWT_PUBLIC_KEY not configured")
        return False
    
    # Verify token cryptographically
    result = verify_jwt_token_with_public_key(jwt_token, public_key, algorithm)
    
    if not result["valid"]:
        return False
    
    # Check if token is revoked in database
    payload = result["payload"]
    jti = payload.get("jti")
    
    if jti:
        token_record = db_get_jwt_token(session, jti)
        if token_record and token_record.is_revoked:
            return False
    
    return True

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
        # Get all non-revoked JWT token IDs for this user
        tokens = db_get_user_tokens(session, user.uid)
        jwt_token_ids = [token.jti for token in tokens]
        
        result.append({
            "uid": user.uid,
            "username": user.name,
            "password_hash": user.password,
            "jwt_token_ids": jwt_token_ids
        })
    
    return result

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
        "is_revoked": token.is_revoked,
        "revoked_at": token.revoked_at if token.revoked_at else None
    }
