from __future__ import annotations

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
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey, ForeignKeyConstraint, create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import bcrypt
import random
import time
from datetime import datetime

Base = declarative_base()

PERMISSION_CODE_USER_READ = 1001
PERMISSION_CODE_USER_CREATE = 1002
PERMISSION_CODE_USER_EDIT = 1003
PERMISSION_CODE_USER_DELETE = 1004
PERMISSION_CODE_USER_MANAGE = 1099

PERMISSION_CODE_TOKEN_READ = 1101
PERMISSION_CODE_TOKEN_ISSUE = 1102
PERMISSION_CODE_TOKEN_REVOKE = 1103
PERMISSION_CODE_TOKEN_DELETE = 1104
PERMISSION_CODE_TOKEN_MANAGE = 1199

TOKEN_STATUS_VALID = 1
TOKEN_STATUS_EXPIRED = -1
TOKEN_STATUS_REVOKED = -2
TOKEN_STATUS_RETAINED = -3

PERMISSION_META_DEFAULT = [
    (PERMISSION_CODE_USER_READ, "User Read", "Read users and their permission assignments."),
    (PERMISSION_CODE_USER_CREATE, "User Create", "Create users."),
    (PERMISSION_CODE_USER_EDIT, "User Edit", "Edit users and user permission assignments."),
    (PERMISSION_CODE_USER_DELETE, "User Delete", "Delete users."),
    (PERMISSION_CODE_USER_MANAGE, "User Manage", "All user management permissions."),
    (PERMISSION_CODE_TOKEN_READ, "Token Read", "Read token records."),
    (PERMISSION_CODE_TOKEN_ISSUE, "Token Issue", "Issue tokens for users."),
    (PERMISSION_CODE_TOKEN_REVOKE, "Token Revoke", "Actively invalidate tokens."),
    (PERMISSION_CODE_TOKEN_DELETE, "Token Delete", "Delete token records."),
    (PERMISSION_CODE_TOKEN_MANAGE, "Token Manage", "All token management permissions."),
]

PERMISSION_INCLUDE_DEFAULT = [
    (PERMISSION_CODE_USER_MANAGE, PERMISSION_CODE_USER_READ),
    (PERMISSION_CODE_USER_MANAGE, PERMISSION_CODE_USER_CREATE),
    (PERMISSION_CODE_USER_MANAGE, PERMISSION_CODE_USER_EDIT),
    (PERMISSION_CODE_USER_MANAGE, PERMISSION_CODE_USER_DELETE),
    (PERMISSION_CODE_USER_MANAGE, PERMISSION_CODE_TOKEN_MANAGE),
    (PERMISSION_CODE_TOKEN_MANAGE, PERMISSION_CODE_TOKEN_READ),
    (PERMISSION_CODE_TOKEN_MANAGE, PERMISSION_CODE_TOKEN_ISSUE),
    (PERMISSION_CODE_TOKEN_MANAGE, PERMISSION_CODE_TOKEN_REVOKE),
    (PERMISSION_CODE_TOKEN_MANAGE, PERMISSION_CODE_TOKEN_DELETE),
]

class User(Base):
    __tablename__ = "users"
    uid = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

class PermissionMeta(Base):
    __tablename__ = "permission_meta"
    permission_code = Column(Integer, primary_key=True)
    display_name = Column(String, nullable=False)
    description = Column(String, nullable=False)

class PermissionInclude(Base):
    __tablename__ = "permission_include"
    permission_code = Column(Integer, ForeignKey("permission_meta.permission_code", ondelete="CASCADE"), primary_key=True)
    permission_code_included = Column(Integer, ForeignKey("permission_meta.permission_code", ondelete="CASCADE"), primary_key=True)

class UserPermission(Base):
    __tablename__ = "user_permission"
    uid = Column(Integer, ForeignKey("users.uid", ondelete="CASCADE"), primary_key=True)
    permission_code = Column(Integer, ForeignKey("permission_meta.permission_code", ondelete="CASCADE"), primary_key=True)

class ServicePermissionMeta(Base):
    __tablename__ = "service_permission_meta"
    service_id = Column(String, primary_key=True)
    permission_code = Column(Integer, primary_key=True)
    display_name = Column(String, nullable=False)
    description = Column(String, nullable=False)

class ServicePermissionInclude(Base):
    __tablename__ = "service_permission_include"
    service_id = Column(String, primary_key=True)
    permission_code = Column(Integer, primary_key=True)
    permission_code_included = Column(Integer, primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["service_id", "permission_code"],
            ["service_permission_meta.service_id", "service_permission_meta.permission_code"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["service_id", "permission_code_included"],
            ["service_permission_meta.service_id", "service_permission_meta.permission_code"],
            ondelete="CASCADE",
        ),
    )

class UserServicePermission(Base):
    __tablename__ = "user_service_permission"
    uid = Column(Integer, ForeignKey("users.uid", ondelete="CASCADE"), primary_key=True)
    service_id = Column(String, primary_key=True)
    permission_code = Column(Integer, primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["service_id", "permission_code"],
            ["service_permission_meta.service_id", "service_permission_meta.permission_code"],
            ondelete="CASCADE",
        ),
    )

class JWTToken(Base):
    __tablename__ = "jwt_tokens"
    jti = Column(String(36), primary_key=True, unique=True, nullable=False)
        # jwt token id
    uid = Column(Integer, ForeignKey('users.uid', ondelete="CASCADE"), nullable=False)
    
    # Unix timestamps as 64-bit integers
    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()), nullable=False)
    created_at_timezone = Column(Integer, default=0)  # integer from -12 to +12
    expires_at = Column(BigInteger, nullable=False)
    
    jwt_token = Column(String, nullable=False)
    
    status_code = Column(Integer, default=TOKEN_STATUS_VALID, nullable=False)
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


def get_db_config(config, db_id=None):
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
    
    db_list = config.get('DATABASE_LIST', [])
    if not db_list:
        raise ValueError("DATABASE_LIST is empty in config")
    
    # Get database ID
    if db_id is None:
        db_id = config.get('CURRENT_DATABASE_ID', 0)
    
    logger.info(f"Getting database URL for ID: {db_id}")
    logger.info(f"Available databases: {[db.get('id') for db in db_list]}")
    
    # Find database config by ID
    db_config = None
    for db in db_list:
        if db.get('id') == db_id:
            db_config = db
            break
    
    if not db_config:
        raise ValueError(f"Database with ID {db_id} not found in DATABASE_LIST")
    
    return db_config


def ensure_postgresql_db_exists(db_config):
    import logging
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    logger = logging.getLogger(__name__)
    db_name = db_config.get('database')
    if not db_name:
        raise ValueError("PostgreSQL database name is required")

    connection = psycopg2.connect(
        host=db_config.get('host') or '127.0.0.1',
        port=int(db_config.get('port') or 5432),
        dbname=os.environ.get('DB_BOOTSTRAP_NAME', 'postgres'),
        user=db_config.get('username') or 'postgres',
        password=db_config.get('password') or 'postgres',
        connect_timeout=5,
    )
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with connection.cursor() as cursor:
            cursor.execute("select 1 from pg_database where datname = %s", (db_name,))
            if cursor.fetchone():
                return
            logger.info(f"Creating PostgreSQL database: {db_name}")
            cursor.execute(sql.SQL("create database {}").format(sql.Identifier(db_name)))
    finally:
        connection.close()


def test_db_connection(db_config):
    db_type = str(db_config.get('type', 'sqlite')).lower()

    if db_type == 'postgresql':
        import psycopg2
        connection = psycopg2.connect(
            host=db_config.get('host') or '127.0.0.1',
            port=int(db_config.get('port') or 5432),
            dbname=db_config.get('database') or 'postgres',
            user=db_config.get('username') or 'postgres',
            password=db_config.get('password') or 'postgres',
            connect_timeout=5,
        )
        connection.close()
        return {"code": 0, "message": "connection ok"}

    if db_type == 'sqlite':
        import os
        from sqlalchemy import create_engine, text
        path = db_config.get('path', '/data/auth.db')
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        engine = create_engine(f"sqlite:///{path}", echo=False)
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        engine.dispose()
        return {"code": 0, "message": "connection ok"}

    if db_type == 'mysql':
        import pymysql
        connection = pymysql.connect(
            host=db_config.get('host') or '127.0.0.1',
            port=int(db_config.get('port') or 3306),
            database=db_config.get('database') or '',
            user=db_config.get('username') or '',
            password=db_config.get('password') or '',
            connect_timeout=5,
        )
        connection.close()
        return {"code": 0, "message": "connection ok"}

    raise ValueError(f"Unsupported db type: {db_type}")


def get_db_url(config, db_id=None):
    import logging
    logger = logging.getLogger(__name__)
    db_config = get_db_config(config, db_id)
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
        return URL.create(
            "postgresql+psycopg2",
            username=db_config.get('username'),
            password=db_config.get('password'),
            host=db_config.get('host'),
            port=int(db_config.get('port') or 5432),
            database=db_config.get('database'),
        )
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
    
    db_config = get_db_config(config, db_id)
    if str(db_config.get('type', 'sqlite')).lower() == 'postgresql':
        ensure_postgresql_db_exists(db_config)

    db_url = get_db_url(config, db_id)
    logger.info(f"Initializing db with URL: {db_url}")
    
    # Ensure directory exists for SQLite
    if str(db_config.get('type', 'sqlite')).lower() == 'sqlite':
        db_file_path = db_config.get('path', '/data/auth.db')
        _utils_file.create_dir_for_file_path(db_file_path)
        logger.info(f"SQLite database file path: {db_file_path}")
    
    engine = create_engine(
        db_url,
        echo=False,
        pool_size=config.get('DATABASE_POOL_SIZE', 5),
        max_overflow=config.get('DATABASE_MAX_OVERFLOW', 10),
        pool_timeout=config.get('DATABASE_POOL_TIMEOUT', 30),
        pool_recycle=config.get('DATABASE_POOL_RECYCLE', 3600),
    )
    
    db_migrate_jwt_tokens(engine)

    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        db_seed_builtin_permissions(session)
        db_sync_config_manage_users(config, session)
        db_grant_first_user_manage_permission(session)
    finally:
        session.close()
    return engine, SessionLocal


def db_migrate_jwt_tokens(engine):
    inspector = inspect(engine)
    if "jwt_tokens" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("jwt_tokens")}
    with engine.begin() as connection:
        if "status_code" not in columns:
            connection.execute(text(
                "alter table jwt_tokens add column status_code integer default 1 not null"
            ))
        now = int(time.time())
        if "is_revoked" in columns:
            connection.execute(text(
                """
                update jwt_tokens
                set status_code = case
                    when revoked_at is not null then -2
                    when is_revoked = true then -2
                    when expires_at <= :now then -1
                    else 1
                end
                """
            ), {"now": now})
            connection.execute(text(
                "alter table jwt_tokens drop column is_revoked"
            ))
        else:
            connection.execute(text(
                """
                update jwt_tokens
                set status_code = case
                    when revoked_at is not null then -2
                    when expires_at <= :now then -1
                    else status_code
                end
                """
            ), {"now": now})


def db_seed_builtin_permissions(session):
    for permission_code, display_name, description in PERMISSION_META_DEFAULT:
        item = session.query(PermissionMeta).filter_by(permission_code=permission_code).first()
        if item:
            item.display_name = display_name
            item.description = description
        else:
            session.add(PermissionMeta(
                permission_code=permission_code,
                display_name=display_name,
                description=description,
            ))

    for permission_code, permission_code_included in PERMISSION_INCLUDE_DEFAULT:
        item = session.query(PermissionInclude).filter_by(
            permission_code=permission_code,
            permission_code_included=permission_code_included,
        ).first()
        if not item:
            session.add(PermissionInclude(
                permission_code=permission_code,
                permission_code_included=permission_code_included,
            ))

    session.commit()


def db_grant_first_user_manage_permission(session):
    is_permission_assigned = session.query(UserPermission).first() is not None
    if is_permission_assigned:
        return

    user = session.query(User).order_by(User.uid.asc()).first()
    if not user:
        return

    session.add(UserPermission(uid=user.uid, permission_code=PERMISSION_CODE_USER_MANAGE))
    session.commit()


def db_sync_config_manage_users(config, session):
    user_list = config.get("AUTH_USERS") or []
    for user_item in user_list:
        role_list = user_item.get("roles") or []
        if "manage" not in role_list:
            continue

        username = str(user_item.get("username") or "").strip()
        password = str(user_item.get("password") or "")
        if not username or not password:
            continue

        bcrypt_rounds = config.get("BCRYPT_ROUNDS", 12)
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=bcrypt_rounds),
        ).decode("utf-8")

        user = db_get_user_by_username(session, username)
        if user:
            user.password = password_hash
        else:
            user = User(uid=gen_uid(config, session), name=username, password=password_hash)
            session.add(user)
            session.flush()

        permission = session.query(UserPermission).filter_by(
            uid=user.uid,
            permission_code=PERMISSION_CODE_USER_MANAGE,
        ).first()
        if not permission:
            session.add(UserPermission(
                uid=user.uid,
                permission_code=PERMISSION_CODE_USER_MANAGE,
            ))

    session.commit()


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
        session.query(UserPermission).filter(UserPermission.uid == user.uid).delete()
        session.query(UserServicePermission).filter(UserServicePermission.uid == user.uid).delete()
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
        status_code=TOKEN_STATUS_VALID,
    )
    session.add(new_token)
    session.commit()


def db_get_jwt_token(session, jti: str):
    """Get JWT token record from database by JTI."""
    token = session.query(JWTToken).filter_by(jti=jti).first()
    if token:
        db_refresh_jwt_token_status(session, token)
    return token


def db_refresh_jwt_token_status(session, token, now: int | None = None):
    now = int(time.time()) if now is None else now
    if token.status_code > 0 and token.expires_at <= now:
        token.status_code = TOKEN_STATUS_EXPIRED
        session.commit()
    return token.status_code


def db_refresh_expired_jwt_tokens(session, now: int | None = None) -> int:
    now = int(time.time()) if now is None else now
    updated_count = session.query(JWTToken).filter(
        JWTToken.status_code > 0,
        JWTToken.expires_at <= now,
    ).update({JWTToken.status_code: TOKEN_STATUS_EXPIRED}, synchronize_session=False)
    session.commit()
    return updated_count


def db_revoke_jwt_token(session, jti: str, revoked_at: int | None = None) -> bool:
    token = db_get_jwt_token(session, jti)
    if not token:
        return False
    revoked_at = int(time.time()) if revoked_at is None else revoked_at
    token.status_code = TOKEN_STATUS_REVOKED
    token.revoked_at = revoked_at
    session.commit()
    return True


def db_cleanup_jwt_tokens(session, retention_seconds: int, now: int | None = None) -> dict:
    now = int(time.time()) if now is None else now
    expired_count = db_refresh_expired_jwt_tokens(session, now)
    retention_seconds = max(0, int(retention_seconds))
    delete_before_expires_at = now - retention_seconds
    tokens_to_delete = session.query(JWTToken).filter(
        JWTToken.status_code < 0,
        JWTToken.expires_at <= delete_before_expires_at,
    ).all()
    retained_count = len(tokens_to_delete)
    for token in tokens_to_delete:
        token.status_code = TOKEN_STATUS_RETAINED
    session.commit()
    for token in tokens_to_delete:
        session.delete(token)
    session.commit()
    return {
        "expired_count": expired_count,
        "retained_count": retained_count,
        "deleted_count": retained_count,
    }


def db_delete_jwt_token(session, jti: str) -> bool:
    token = db_get_jwt_token(session, jti)
    if not token:
        return False
    session.delete(token)
    session.commit()
    return True


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
    tokens = session.query(JWTToken).filter(
        JWTToken.uid == uid,
    ).order_by(JWTToken.created_at.desc()).all()
    for token in tokens:
        db_refresh_jwt_token_status(session, token)
    return tokens


def db_get_permission_meta(session) -> list:
    return session.query(PermissionMeta).order_by(PermissionMeta.permission_code.asc()).all()


def db_get_permission_include(session) -> list:
    return session.query(PermissionInclude).order_by(
        PermissionInclude.permission_code.asc(),
        PermissionInclude.permission_code_included.asc(),
    ).all()


def db_get_user_permissions(session, uid: int) -> list:
    return session.query(UserPermission).filter(
        UserPermission.uid == uid,
    ).order_by(UserPermission.permission_code.asc()).all()


def db_set_user_permissions(session, uid: int, permission_codes: list[int]):
    session.query(UserPermission).filter(UserPermission.uid == uid).delete()
    for permission_code in sorted(set(permission_codes or [])):
        permission_meta = session.query(PermissionMeta).filter_by(permission_code=permission_code).first()
        if not permission_meta:
            raise ValueError(f"Unknown permission code: {permission_code}")
        session.add(UserPermission(uid=uid, permission_code=permission_code))
    session.commit()


def db_get_service_permission_meta(session) -> list:
    return session.query(ServicePermissionMeta).order_by(
        ServicePermissionMeta.service_id.asc(),
        ServicePermissionMeta.permission_code.asc(),
    ).all()


def db_get_service_permission_include(session) -> list:
    return session.query(ServicePermissionInclude).order_by(
        ServicePermissionInclude.service_id.asc(),
        ServicePermissionInclude.permission_code.asc(),
        ServicePermissionInclude.permission_code_included.asc(),
    ).all()


def db_get_user_service_permissions(session, uid: int) -> list:
    return session.query(UserServicePermission).filter(
        UserServicePermission.uid == uid,
    ).order_by(
        UserServicePermission.service_id.asc(),
        UserServicePermission.permission_code.asc(),
    ).all()


def db_set_user_service_permissions(session, uid: int, service_permission_items: list[dict]):
    session.query(UserServicePermission).filter(UserServicePermission.uid == uid).delete()
    service_permission_seen = set()
    for item in service_permission_items or []:
        service_id = str(item.get("service_id", "")).strip()
        permission_code = int(item.get("permission_code"))
        service_permission_key = (service_id, permission_code)
        if service_permission_key in service_permission_seen:
            continue
        service_permission_seen.add(service_permission_key)
        permission_meta = session.query(ServicePermissionMeta).filter_by(
            service_id=service_id,
            permission_code=permission_code,
        ).first()
        if not permission_meta:
            raise ValueError(f"Unknown service permission: {service_id}::{permission_code}")
        session.add(UserServicePermission(
            uid=uid,
            service_id=service_id,
            permission_code=permission_code,
        ))
    session.commit()


def db_upsert_service_permission_meta(session, service_id: str, permission_code: int, display_name: str, description: str):
    item = session.query(ServicePermissionMeta).filter_by(
        service_id=service_id,
        permission_code=permission_code,
    ).first()
    if item:
        item.display_name = display_name
        item.description = description
    else:
        item = ServicePermissionMeta(
            service_id=service_id,
            permission_code=permission_code,
            display_name=display_name,
            description=description,
        )
        session.add(item)
    session.commit()
    return item


def db_set_service_permission_include(session, service_id: str, permission_code: int, permission_codes_included: list[int]):
    session.query(ServicePermissionInclude).filter(
        ServicePermissionInclude.service_id == service_id,
        ServicePermissionInclude.permission_code == permission_code,
    ).delete()
    for permission_code_included in sorted(set(permission_codes_included or [])):
        permission_meta = session.query(ServicePermissionMeta).filter_by(
            service_id=service_id,
            permission_code=permission_code_included,
        ).first()
        if not permission_meta:
            raise ValueError(f"Unknown included service permission: {service_id}::{permission_code_included}")
        session.add(ServicePermissionInclude(
            service_id=service_id,
            permission_code=permission_code,
            permission_code_included=permission_code_included,
        ))
    session.commit()


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

