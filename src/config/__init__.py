from third_party.utils_python_global import Dict, _utils_file
from sqlalchemy import create_engine, Column, Integer, BigInteger, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from typing import List
import json
import time
import os

Base = declarative_base()

class Config(Base):
  __tablename__ = 'configs'
  created_at = Column(BigInteger, primary_key=True)  # unix timestamp (64-bit signed integer)
  created_at_timezone = Column(Integer, nullable=False)  # timezone offset in hours: -12 to +12
  updated_at = Column(BigInteger, nullable=False)  # unix timestamp (64-bit signed integer)
  updated_at_timezone = Column(Integer, nullable=False)  # timezone offset in hours: -12 to +12
  config_json = Column(Text, nullable=False)
  config_chain_json = Column(Text, nullable=True)
  
  def __repr__(self):
    return f"<Config(created_at={self.created_at}, tz_offset={self.created_at_timezone})>"

def compose_config(config_chain: List[dict]) -> dict:
  try:
    from .config_default import config as config_default
  except Exception as e:
    print(f"Warning: Failed to load config_default: {e}")
    config_default = Dict()
  
  try:
    from .config_dev import config as config_dev
  except Exception as e:
    print(f"Warning: Failed to load config_dev: {e}")
    config_dev = Dict()
  
  try:
    from .config_arg import config_arg
  except Exception as e:
    print(f"Warning: Failed to load config_arg: {e}")
    config_arg = Dict()
  
  try:
    from .config_env import config_docker_run as config_env
  except Exception as e:
    print(f"Warning: Failed to load config_env: {e}")
    config_env = Dict()

  config_chain = [
    config_default,
    config_dev,
    config_arg,  # Command line args override dev config
    config_env,  # Environment vars override command line args
  ]

  # Final config with all overrides applied
  config = Dict()
  for _config in config_chain:
      config.update(_config)

  return Dict(
    config=config,
    config_chain=config_chain,
  )

def store_config_to_local_db(config: Dict = None, db_file_path: str = None) -> int:
  """
  Store parsed config to local SQLite database using SQLAlchemy.
  
  Args:
    config: Configuration dictionary. If None, compose_config() will be called.
    db_file_path: Path to SQLite database file. Required.
    
  Returns:
    Unix timestamp of the stored config
  """
  if db_file_path is None:
      raise ValueError("db_file_path is required")
  
  # Get config data if not provided
  if config is None:
    config_data = compose_config([])
    config = config_data.get('config', Dict())
    config_chain = config_data.get('config_chain', [])
  else:
    config_chain = []
  
  # Ensure directory exists
  _utils_file.create_dir_for_file_path(db_file_path)
  
  # Create database engine
  db_url = f"sqlite:///{db_file_path}"
  engine = create_engine(db_url, echo=False)
  
  # Create tables if they don't exist
  Base.metadata.create_all(engine)
  
  # Create session
  Session = sessionmaker(bind=engine)
  session = Session()
  
  try:
    # Get current timestamp and timezone offset
    unix_stamp_int_now = int(time.time())  # 64-bit signed integer (seconds since epoch)
    tz_offset = time.timezone // 3600 * -1  # Convert seconds to hours and invert sign
    
    # Serialize config to JSON
    config_json = json.dumps(dict(config), indent=2, default=str)
    config_chain_json = json.dumps([dict(c) for c in config_chain], indent=2, default=str) if config_chain else None
    
    # Create new config entry
    new_config = Config(
      created_at=unix_stamp_int_now,
      created_at_timezone=tz_offset,
      updated_at=unix_stamp_int_now,
      updated_at_timezone=tz_offset,
      config_json=config_json,
      config_chain_json=config_chain_json
    )
    
    # Add and commit
    session.add(new_config)
    session.commit()
    
    print(f"Config stored to database at timestamp: {unix_stamp_int_now}")
    return unix_stamp_int_now
    
  except Exception as e:
    session.rollback()
    print(f"Error storing config to database: {e}")
    raise
  finally:
    session.close()

def get_config_from_db(timestamp: int = None, db_file_path: str = None) -> Dict:
  """
  Retrieve config from local SQLite database.
  
  Args:
      timestamp: Specific unix timestamp to retrieve. If None, gets the most recent.
      db_file_path: Path to SQLite database file. Required.
      
  Returns:
      Dict containing the config data
  """
  if db_file_path is None:
      raise ValueError("db_file_path is required")
    
  # Ensure directory exists
  _utils_file.create_dir_for_file_path(db_file_path)
  
  db_url = f"sqlite:///{db_file_path}"
  engine = create_engine(db_url, echo=False)
  Session = sessionmaker(bind=engine)
  session = Session()
  
  try:
    if timestamp is not None:
      config_entry = session.query(Config).filter_by(created_at=timestamp).first()
    else:
      # Get most recent config
      config_entry = session.query(Config).order_by(Config.created_at.desc()).first()
    
    if config_entry is None:
      return Dict()
    
    # Parse JSON back to dict
    config = json.loads(config_entry.config_json)
    
    return Dict(
      created_at=config_entry.created_at,
      created_at_timezone=config_entry.created_at_timezone,
      config=Dict(config)
    )
    
  except Exception as e:
    print(f"Error retrieving config from database: {e}")
    raise
  finally:
    session.close()