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


def add_user(config, session, username: str, password: str) -> bool:
    """
    Add a new user to the database with hashed password.
    Returns True if successful, False if user already exists or error occurs.
    
    Args:
        config: Configuration dictionary
        session: Database session
        username: Username
        password: Plain text password
    """
    if not username or not password:
        return False
    
    # Check if user already exists
    existing_user = session.query(User).filter(User.name == username).first()
    if existing_user:
        return False
    
    # Hash the password
    bcrypt_rounds = config.get('BCRYPT_ROUNDS', 12)
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=bcrypt_rounds))
    
    # Generate unique uid
    uid = gen_uid(config, session)
    
    # Create new user
    new_user = User(uid=uid, name=username, password=password_hash.decode('utf-8'))
    session.add(new_user)
    session.commit()
    return True


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


def delete_user(config, session, username: str=None, uid: int=None) -> bool:
    """
    Delete a user. Provide either username or uid.
    
    Args:
        config: Configuration dictionary
        session: Database session
        username: Username to delete
        uid: User ID to delete
    """
    if not username and not uid:
        return False
    
    if username:
        user = session.query(User).filter(User.name == username).first()
    else:
        user = session.query(User).filter(User.uid == uid).first()
    
    if user:
        session.delete(user)
        session.commit()
        return True
    return False

def issue_jwt_token(config, session, username, password) -> str:
    """
    Issue JWT token after validating credentials.
    
    Args:
        config: Configuration dictionary
        session: Database session
        username: Username
        password: Password
        
    Returns:
        str: JWT token if successful, None otherwise
    """
    # TODO: implement JWT token issuance
    return None

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
