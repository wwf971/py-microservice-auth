#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
SQL_PATH = Path(__file__).with_name("init_db.sql")

sys.path.insert(0, str(BACKEND_DIR))

from config import load_project_config

DROP_TABLES_SQL = """
drop table if exists user_service_permission cascade;
drop table if exists jwt_tokens cascade;
drop table if exists user_permission cascade;
drop table if exists service_permission_include cascade;
drop table if exists service_permission_meta cascade;
drop table if exists permission_include cascade;
drop table if exists permission_meta cascade;
drop table if exists key_pairs cascade;
drop table if exists users cascade;
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Drop auth-jwt tables and recreate schema from database/init_db.sql",
    )
    parser.add_argument(
        "--db-id",
        type=int,
        default=None,
        help="Database id from config. Default: CURRENT_DATABASE_ID",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    return parser.parse_args()


def get_db_config(config, db_id):
    db_list = config.get("DATABASE_LIST") or []
    if db_id is None:
        db_id = config.get("CURRENT_DATABASE_ID", 0)
    for db_item in db_list:
        if db_item.get("id") == db_id:
            return db_item
    raise ValueError(f"Database with id {db_id} not found")


def confirm(db_config):
    db_name = db_config.get("name") or db_config.get("id")
    db_type = db_config.get("type")
    print(f"This will delete all data in database '{db_name}' ({db_type}).")
    answer = input("Type 'yes' to continue: ").strip().lower()
    if answer != "yes":
        print("Cancelled.")
        sys.exit(1)


def ensure_postgresql_db_exists(db_config):
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    db_name = db_config.get("database")
    if not db_name:
        raise ValueError("PostgreSQL database name is required")

    connection = psycopg2.connect(
        host=db_config.get("host") or "127.0.0.1",
        port=int(db_config.get("port") or 5432),
        dbname=os.environ.get("DB_BOOTSTRAP_NAME", "postgres"),
        user=db_config.get("username") or "postgres",
        password=db_config.get("password") or "postgres",
    )
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with connection.cursor() as cursor:
            cursor.execute("select 1 from pg_database where datname = %s", (db_name,))
            if cursor.fetchone():
                return
            cursor.execute(sql.SQL("create database {}").format(sql.Identifier(db_name)))
    finally:
        connection.close()


def run_postgresql(db_config, sql_text):
    import psycopg2

    ensure_postgresql_db_exists(db_config)
    connection = psycopg2.connect(
        host=db_config.get("host") or "127.0.0.1",
        port=int(db_config.get("port") or 5432),
        dbname=db_config.get("database") or "service_auth",
        user=db_config.get("username") or "postgres",
        password=db_config.get("password") or "postgres",
    )
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(DROP_TABLES_SQL)
            cursor.execute(sql_text)
    finally:
        connection.close()


def run_sqlite(db_config, sql_text):
    import sqlite3

    db_path = db_config.get("path") or str(PROJECT_ROOT / "data" / "auth.db")
    if not os.path.isabs(db_path):
        db_path = str((PROJECT_ROOT / db_path).resolve())

    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(DROP_TABLES_SQL)
        connection.executescript(sql_text)
        connection.commit()
    finally:
        connection.close()


def seed_from_config(config, db_id):
    try:
        from api.api_db import init_database
    except ModuleNotFoundError as error:
        print("Schema created.")
        print("Seed step skipped because backend dependencies are missing:", error)
        print("Restart auth service to create manage users and key pair.")
        return

    init_database(config, db_id)


def main():
    args = parse_args()
    os.environ.setdefault("DIR_BASE", str(PROJECT_ROOT))

    config = load_project_config(PROJECT_ROOT)
    db_id = args.db_id if args.db_id is not None else config.get("CURRENT_DATABASE_ID", 0)
    db_config = get_db_config(config, db_id)

    if not args.yes:
        confirm(db_config)

    sql_text = SQL_PATH.read_text(encoding="utf-8")
    db_type = str(db_config.get("type", "sqlite")).lower()

    if db_type == "postgresql":
        run_postgresql(db_config, sql_text)
    elif db_type == "sqlite":
        run_sqlite(db_config, sql_text)
    else:
        print(f"Unsupported database type: {db_type}")
        sys.exit(1)

    seed_from_config(config, db_id)
    print(f"Database reinitialized: {db_config.get('name')} (id={db_config.get('id')})")


if __name__ == "__main__":
    main()
