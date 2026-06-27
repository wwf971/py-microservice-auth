from __future__ import annotations

from pathlib import Path
from typing import Any, List

import os
import time
import yaml

from third_party.utils_python_global import Dict


class UniqueKeyLoader(yaml.SafeLoader):
  pass


def _construct_mapping_without_duplicate_keys(loader: UniqueKeyLoader, node, deep=False):
  mapping = {}
  for key_node, value_node in node.value:
    key = loader.construct_object(key_node, deep=deep)
    if key in mapping:
      line_number = key_node.start_mark.line + 1
      column_number = key_node.start_mark.column + 1
      raise ValueError(f"duplicate config key '{key}' at {loader.name}:{line_number}:{column_number}")
    value = loader.construct_object(value_node, deep=deep)
    mapping[key] = value
  return mapping


UniqueKeyLoader.add_constructor(
  yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
  _construct_mapping_without_duplicate_keys,
)


def _deep_merge(base_value: Any, override_value: Any):
  if isinstance(base_value, dict) and isinstance(override_value, dict):
    data_merged = dict(base_value)
    for key, value in override_value.items():
      data_merged[key] = _deep_merge(data_merged.get(key), value)
    return data_merged
  return override_value if override_value is not None else base_value


def _load_yaml_config_file(file_path: Path):
  if not file_path.is_file():
    return {}
  with file_path.open("r", encoding="utf-8") as file:
    loader = UniqueKeyLoader(file)
    loader.name = str(file_path)
    try:
      data_loaded = loader.get_single_data() or {}
    finally:
      loader.dispose()
  return data_loaded if isinstance(data_loaded, dict) else {}


def _get_dir_base():
  dir_base_env = os.getenv("DIR_BASE")
  if dir_base_env:
    return Path(dir_base_env).expanduser().resolve()
  return Path(__file__).resolve().parents[2]


def load_project_config(dir_base: Path | None = None):
  dir_base = Path(dir_base or _get_dir_base())
  config_dir = dir_base / "config"
  config_default = _load_yaml_config_file(config_dir / "config.yaml")
  config_local = _load_yaml_config_file(config_dir / "config.0.yaml")
  config_merged = _deep_merge(config_default, config_local)
  config_dbs_local = config_local.get("config_dbs") or config_local.get("config_databases")
  if isinstance(config_dbs_local, dict) and len(config_dbs_local) > 0:
    config_merged["config_dbs"] = config_dbs_local
  return _normalize_config(config_merged, dir_base)


def _normalize_config(config_raw: dict, dir_base: Path):
  service = config_raw.get("service") or {}
  db = config_raw.get("db") or config_raw.get("database") or {}
  auth = config_raw.get("auth") or {}
  jwt = config_raw.get("jwt") or {}
  security = config_raw.get("security") or {}

  port_env = os.getenv("PORT")
  port_manage = int(port_env or service.get("port_manage") or 9530)
  port_service_http = port_manage + 1 if port_env else int(service.get("port_service_http") or port_manage + 1)
  port_service_grpc = port_manage + 2 if port_env else int(service.get("port_service_grpc") or port_manage + 2)
  port_aux = port_manage + 3 if port_env else int(service.get("port_aux") or port_manage + 3)
  db_list = _normalize_db_list(config_raw, db, dir_base)
  user_list = _normalize_user_list(auth.get("users") or [])
  user_manage = _get_manage_user(user_list)

  config = Dict(
    DATABASE_LIST=db_list,
    CURRENT_DATABASE_ID=int(db.get("current_db_id") or db.get("current_database_id") or 0),
    DATABASE_POOL_SIZE=int(db.get("pool_size") or 10),
    DATABASE_MAX_OVERFLOW=int(db.get("max_overflow") or 20),
    DATABASE_POOL_TIMEOUT=int(db.get("pool_timeout") or 30),
    DATABASE_POOL_RECYCLE=int(db.get("pool_recycle") or 3600),
    AUTH_USERS=user_list,
    MANAGE_USERNAME=user_manage.get("username") if user_manage else None,
    MANAGE_PASSWORD=user_manage.get("password") if user_manage else None,
    PORT_MANAGE=port_manage,
    PORT_SERVICE_HTTP=port_service_http,
    PORT_SERVICE_GRPC=port_service_grpc,
    PORT_AUX=port_aux,
    JWT_ALGORITHM=jwt.get("algorithm") or "RS256",
    JWT_EXPIRATION_HOURS=int(jwt.get("expiration_hours") or 24),
    JWT_TEMP_TOKEN_EXPIRATION_SECONDS=int(jwt.get("temporary_token_expiration_seconds") or 900),
    JWT_TOKEN_RETENTION_SECONDS=int(jwt.get("token_retention_seconds") or 604800),
    JWT_PRIVATE_KEY=jwt.get("private_key"),
    JWT_PUBLIC_KEY=jwt.get("public_key"),
    BCRYPT_ROUNDS=int(security.get("bcrypt_rounds") or 12),
  )
  return config


def _normalize_user_list(user_list_raw):
  if not isinstance(user_list_raw, list):
    return []
  user_list = []
  for user_item in user_list_raw:
    if not isinstance(user_item, dict):
      continue
    roles_raw = user_item.get("roles") or user_item.get("role") or []
    if isinstance(roles_raw, str):
      roles = [roles_raw]
    elif isinstance(roles_raw, list):
      roles = [str(role) for role in roles_raw]
    else:
      roles = []
    user_list.append({
      "username": str(user_item.get("username") or ""),
      "password": str(user_item.get("password") or ""),
      "roles": roles,
    })
  return user_list


def _get_manage_user(user_list):
  for user_item in user_list:
    if "manage" in user_item.get("roles", []):
      return user_item
  return None


def _normalize_db_list(config_raw: dict, db: dict, dir_base: Path):
  db_items_raw = config_raw.get("config_dbs") or config_raw.get("config_databases")
  if isinstance(db_items_raw, dict):
    db_list_raw = []
    for index, (db_key, db_item) in enumerate(db_items_raw.items()):
      if not isinstance(db_item, dict):
        continue
      db_list_raw.append({
        "id": db_item.get("id", index),
        "name": db_item.get("name") or db_item.get("label") or db_key,
        "type": db_item.get("type") or "postgresql",
        "host": db_item.get("host") or db_item.get("ip"),
        "port": db_item.get("port"),
        "database": db_item.get("database") or db_item.get("db_name") or db_item.get("database_name"),
        "username": db_item.get("username"),
        "password": db_item.get("password"),
        "path": db_item.get("path"),
        "is_default": db_item.get("is_default", index == 0),
        "is_removable": db_item.get("is_removable", index != 0),
      })
  else:
    db_list_raw = db.get("dbs") or db.get("databases") or []

  if not isinstance(db_list_raw, list):
    db_list_raw = []

  db_list = []
  for db_item in db_list_raw:
    if not isinstance(db_item, dict):
      continue
    db_item_normalized = dict(db_item)
    db_type = str(db_item_normalized.get("type") or "postgresql").lower()
    db_item_normalized["type"] = db_type
    if db_type == "sqlite":
      db_path = db_item_normalized.get("path") or "./data/auth.db"
      if not os.path.isabs(db_path):
        db_item_normalized["path"] = str((dir_base / db_path).resolve())
    db_item_normalized.setdefault("host", "127.0.0.1")
    db_item_normalized["port"] = int(db_item_normalized.get("port") or 5432)
    db_item_normalized.setdefault("database", "service_auth")
    db_item_normalized.setdefault("username", "postgres")
    db_item_normalized.setdefault("password", "postgres")
    db_item_normalized.setdefault("is_default", False)
    db_item_normalized.setdefault("is_removable", True)
    db_list.append(db_item_normalized)

  if len(db_list) == 0:
    db_list.append({
      "id": 0,
      "name": "auth-postgres",
      "type": "postgresql",
      "path": None,
      "host": "127.0.0.1",
      "port": 5432,
      "database": "service_auth",
      "username": "postgres",
      "password": "postgres",
      "is_default": True,
      "is_removable": False,
    })
  return db_list


def compose_config(config_chain: List[dict] | None = None) -> dict:
  config = load_project_config()
  return Dict(
    config=config,
    config_chain=[],
  )


def set_config_user(config_update):
  raise RuntimeError("Runtime config editing is disabled. Edit config/config.0.yaml and restart the service.")


def store_config_to_local_db(config: Dict = None, db_file_path: str = None) -> int:
  return int(time.time())