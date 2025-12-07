# pip install jwt bcrypt sqlalchemy
import sys, os, pathlib
dir_path_current = os.path.dirname(os.path.realpath(__file__)) + "/"
dir_path_src = pathlib.Path(dir_path_current).parent.absolute().__str__() + "/"
dir_path_third_party = dir_path_src + "third_party/"
sys.path += [
  dir_path_src,
]
from third_party.utils_python_global import _utils_file
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import bcrypt
import random
import time
from datetime import datetime

Base = declarative_base()
class User(Base):
    __tablename__ = "users"
    uid = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

class JWTToken(Base):
    __tablename__ = "jwt_tokens"
    jti = Column(String(36), primary_key=True, unique=True, nullable=False)
        # jwt token id
    uid = Column(Integer, ForeignKey('users.uid'), nullable=False)
    
    # Unix timestamps as 64-bit integers
    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()), nullable=False)
    created_at_timezone = Column(Integer, default=0)  # integer from -12 to +12
    expires_at = Column(BigInteger, nullable=False)
    
    jwt_token = Column(String, nullable=False)
    
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(BigInteger, nullable=True)
    
    user = relationship("User", backref="tokens")

# Build database URL from config
def get_database_url(config):
    """
    Build database URL based on DATABASE_TYPE in config.
    
    Args:
        config: Configuration dictionary
    """
    db_type = config.get('DATABASE_TYPE', 'sqlite').lower()
    if db_type == "sqlite":
        return f"sqlite:///{config.get('DATABASE_SQLITE_PATH', '/data/auth.db')}"
    elif db_type == "postgresql":
        return f"postgresql://{config['DATABASE_USER']}:{config['DATABASE_PASSWORD']}@{config['DATABASE_HOST']}:{config['DATABASE_PORT']}/{config['DATABASE_NAME']}"
    elif db_type == "mysql":
        return f"mysql+pymysql://{config['DATABASE_USER']}:{config['DATABASE_PASSWORD']}@{config['DATABASE_HOST']}:{config['DATABASE_PORT']}/{config['DATABASE_NAME']}"
    else:
        raise ValueError(f"Unsupported DATABASE_TYPE: {db_type}")


def init_database(config):
    """
    Initialize database engine and session maker.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        tuple: (engine, SessionLocal)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    DATABASE_URL = get_database_url(config)
    logger.info(f"Initializing database with URL: {DATABASE_URL}")
    
    # Ensure directory exists for SQLite
    if config.get('DATABASE_TYPE', 'sqlite').lower() == 'sqlite':
        db_file_path = config.get('DATABASE_SQLITE_PATH', '/data/auth.db')
        _utils_file.create_dir_for_file_path(db_file_path)
        logger.info(f"SQLite database file path: {db_file_path}")
    
    engine = create_engine(
        DATABASE_URL, 
        echo=False,
        pool_size=config.get('DATABASE_POOL_SIZE', 5),
        max_overflow=config.get('DATABASE_MAX_OVERFLOW', 10),
        pool_timeout=config.get('DATABASE_POOL_TIMEOUT', 30),
        pool_recycle=config.get('DATABASE_POOL_RECYCLE', 3600),
    )
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


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
        user = session.query(User).filter_by(name=username).first()
        
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
    existing_user = session.query(User).filter(User.name == username).first()
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
        
        # Create new user
        new_user = User(uid=uid, name=username, password=password_hash.decode('utf-8'))
        session.add(new_user)
        session.commit()
        
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


def gen_uid(config, session) -> int:
    """
    Generate a unique user ID.
    Uses random generation and checks database for uniqueness.
    
    Args:
        config: Configuration dictionary
        session: Database session
    """
    max_attempts = 100
    for _ in range(max_attempts):
        # Generate random 6-digit UID
        uid = random.randint(100000, 999999)
        
        # Check if UID already exists
        existing = session.query(User).filter(User.uid == uid).first()
        if not existing:
            return uid
    
    # Fallback: get max uid and increment
    max_uid = session.query(User.uid).order_by(User.uid.desc()).first()
    if max_uid:
        return max_uid[0] + 1
    return 100000

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
    user = session.query(User).filter(User.name == username).first()
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
    user = session.query(User).filter(User.uid == uid).first()
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
        if username:
            user = session.query(User).filter(User.name == username).first()
            identifier = f"username '{username}'"
        else:
            user = session.query(User).filter(User.uid == uid).first()
            identifier = f"UID {uid}"
        
        if user:
            # Also delete associated JWT tokens
            session.query(JWTToken).filter(JWTToken.uid == user.uid).delete()
            session.delete(user)
            session.commit()
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

def issue_jwt_token(config, session, uid: int) -> tuple:
    """
    Issue JWT token for a user.
    
    Args:
        config: Configuration dictionary
        session: Database session
        uid: User ID
        
    Returns:
        tuple: (token: str, expires_at: int) - JWT token and expiration timestamp
    """
    import jwt
    import uuid
    
    # Generate unique JWT ID
    jti = str(uuid.uuid4())
    
    # Calculate expiration
    expiration_hours = config.get('JWT_EXPIRATION_HOURS', 24)
    expires_at = int(time.time()) + (expiration_hours * 3600)
    
    # Create JWT payload
    payload = {
        'uid': uid,
        'jti': jti,
        'iat': int(time.time()),  # issued at
        'exp': expires_at  # expiration
    }
    
    # Generate token
    secret_key = config.get('JWT_SECRET_KEY', 'change-this-secret-key-in-production')
    algorithm = config.get('JWT_ALGORITHM', 'HS256')
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    
    # Store token in database
    new_token = JWTToken(
        jti=jti,
        uid=uid,
        jwt_token=token,
        created_at=int(time.time()),
        expires_at=expires_at,
        is_revoked=False
    )
    session.add(new_token)
    session.commit()
    
    return token, expires_at

def verify_jwt_token(config, session, jwt_token) -> bool:
    """
    Verify JWT token.
    
    Args:
        config: Configuration dictionary
        session: Database session
        jwt_token: JWT token string
        
    Returns:
        bool: True if valid, False otherwise
    """
    # TODO: implement JWT token verification
    return False


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
    users = session.query(User).all()
    result = []
    
    for user in users:
        # Get all JWT token IDs for this user
        tokens = session.query(JWTToken).filter(JWTToken.uid == user.uid).all()
        jwt_token_ids = [token.jti for token in tokens if not token.is_revoked]
        
        result.append({
            "uid": user.uid,
            "username": user.name,
            "password_hash": user.password,
            "jwt_token_ids": jwt_token_ids
        })
    
    return result
