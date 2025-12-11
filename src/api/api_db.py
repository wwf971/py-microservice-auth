"""
Database interaction layer for authentication service.
All functions here interact with the database.
"""

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


class KeyPair(Base):
    """RSA Key Pair model for JWT signing"""
    __tablename__ = 'key_pairs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    private_key = Column(String, nullable=False)
    public_key = Column(String, nullable=False)
    created_at = Column(BigInteger, nullable=False)  # Unix timestamp in seconds (64-bit signed int)
    created_at_timezone = Column(Integer, nullable=False)  # Timezone offset: -12 to +12
    is_active = Column(Boolean, default=True)  # Only one key pair should be active
    
    def __repr__(self):
        return f"<KeyPair(id={self.id}, created_at={self.created_at}, is_active={self.is_active})>"


def get_database_url(config, db_id=None):
    """
    Build database URL based on database configuration.
    
    Args:
        config: Configuration dictionary
        db_id: Database ID from DATABASE_LIST (None = use CURRENT_DATABASE_ID)
        
    Returns:
        str: Database URL
    """
    import logging
    logger = logging.getLogger(__name__)
    
    database_list = config.get('DATABASE_LIST', [])
    if not database_list:
        raise ValueError("DATABASE_LIST is empty in config")
    
    # Get database ID
    if db_id is None:
        db_id = config.get('CURRENT_DATABASE_ID', 0)
    
    logger.info(f"Getting database URL for ID: {db_id}")
    logger.info(f"Available databases: {[db.get('id') for db in database_list]}")
    
    # Find database config by ID
    db_config = None
    for db in database_list:
        if db.get('id') == db_id:
            db_config = db
            break
    
    if not db_config:
        raise ValueError(f"Database with ID {db_id} not found in DATABASE_LIST")
    
    db_type = db_config.get('type', 'sqlite').lower()
    
    if db_type == "sqlite":
        import os
        path = db_config.get('path', '/data/auth.db')
        # Convert to absolute path if relative
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        logger.info(f"SQLite database path: {path}")
        
        # Ensure directory exists
        db_dir = os.path.dirname(path)
        if db_dir and not os.path.exists(db_dir):
            logger.info(f"Creating directory: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
        
        return f"sqlite:///{path}"
    elif db_type == "postgresql":
        return f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    elif db_type == "mysql":
        return f"mysql+pymysql://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def init_database(config, db_id=None):
    """
    Initialize database engine and session maker.
    
    Args:
        config: Configuration dictionary
        db_id: Database ID from DATABASE_LIST (None = use CURRENT_DATABASE_ID)
        
    Returns:
        tuple: (engine, SessionLocal)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    DATABASE_URL = get_database_url(config, db_id)
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


def db_get_user_by_username(session, username: str):
    """Get user by username from database."""
    return session.query(User).filter_by(name=username).first()


def db_get_user_by_uid(session, uid: int):
    """Get user by UID from database."""
    return session.query(User).filter_by(uid=uid).first()


def db_add_user(config, session, username: str, password_hash: str, uid: int) -> bool:
    """
    Add user to database with hashed password.
    
    Args:
        config: Configuration dictionary
        session: Database session
        username: Username
        password_hash: Hashed password
        uid: User ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        new_user = User(uid=uid, name=username, password=password_hash)
        session.add(new_user)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e


def db_delete_user(session, username: str = None, uid: int = None) -> bool:
    """
    Delete user from database.
    
    Args:
        session: Database session
        username: Username to delete
        uid: User ID to delete
        
    Returns:
        bool: True if deleted, False if not found
    """
    if username:
        user = session.query(User).filter(User.name == username).first()
    else:
        user = session.query(User).filter(User.uid == uid).first()
    
    if user:
        # Also delete associated JWT tokens
        session.query(JWTToken).filter(JWTToken.uid == user.uid).delete()
        session.delete(user)
        session.commit()
        return True
    return False


def db_store_jwt_token(session, jti: str, uid: int, token: str, created_at: int, expires_at: int, timezone_offset: int):
    """
    Store JWT token in database.
    
    Args:
        session: Database session
        jti: JWT token ID
        uid: User ID
        token: JWT token string
        created_at: Creation timestamp
        expires_at: Expiration timestamp
        timezone_offset: Timezone offset (-12 to +12)
    """
    new_token = JWTToken(
        jti=jti,
        uid=uid,
        jwt_token=token,
        created_at=created_at,
        created_at_timezone=timezone_offset,
        expires_at=expires_at,
        is_revoked=False
    )
    session.add(new_token)
    session.commit()


def db_get_jwt_token(session, jti: str):
    """Get JWT token record from database by JTI."""
    return session.query(JWTToken).filter_by(jti=jti).first()


def db_get_all_users(session) -> list:
    """
    Get all users from database with their JWT tokens.
    
    Args:
        session: Database session
        
    Returns:
        list: List of User objects
    """
    return session.query(User).all()


def db_get_user_tokens(session, uid: int) -> list:
    """
    Get all non-revoked JWT tokens for a user.
    
    Args:
        session: Database session
        uid: User ID
        
    Returns:
        list: List of JWTToken objects
    """
    return session.query(JWTToken).filter(
        JWTToken.uid == uid,
        JWTToken.is_revoked == False
    ).all()


def db_get_active_key_pair(session):
    """
    Get the active RSA key pair.
    
    Args:
        session: Database session
        
    Returns:
        KeyPair: Active key pair object or None
    """
    return session.query(KeyPair).filter(KeyPair.is_active == True).first()


def db_store_key_pair(session, private_key: str, public_key: str, created_at: int, created_at_timezone: int):
    """
    Store a new RSA key pair and deactivate all others.
    
    Args:
        session: Database session
        private_key: PEM-encoded private key
        public_key: PEM-encoded public key
        created_at: Unix timestamp in seconds
        created_at_timezone: Timezone offset (-12 to +12)
        
    Returns:
        KeyPair: The newly created key pair
    """
    # Deactivate all existing key pairs
    session.query(KeyPair).update({KeyPair.is_active: False})
    
    # Create new key pair
    key_pair = KeyPair(
        private_key=private_key,
        public_key=public_key,
        created_at=created_at,
        created_at_timezone=created_at_timezone,
        is_active=True
    )
    session.add(key_pair)
    session.commit()
    
    return key_pair


def db_get_key_pair_by_id(session, key_id: int):
    """
    Get a key pair by ID.
    
    Args:
        session: Database session
        key_id: Key pair ID
        
    Returns:
        KeyPair: Key pair object or None
    """
    return session.query(KeyPair).filter(KeyPair.id == key_id).first()

