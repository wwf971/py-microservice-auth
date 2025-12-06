"""
Central configuration structure definition.
All config modules (config_arg, config_env, etc.) use this structure.
"""

from typing import Dict, Any, Tuple, List

class ConfigField:
    """Metadata for a single configuration field"""
    def __init__(self, name: str, type_: type, description: str, group: str = None):
        self.name = name
        self.type = type_
        self.description = description
        self.group = group
    
    def __repr__(self):
        return f"ConfigField({self.name}, {self.type.__name__})"


# Define all configuration fields
CONFIG_STRUCTURE: List[ConfigField] = [
    # Database Configuration
    ConfigField(
        "DATABASE_TYPE",
        str,
        "Database type (sqlite/postgresql/mysql)",
        "Database Configuration"
    ),
    ConfigField(
        "DATABASE_HOST",
        str,
        "Database host",
        "Database Configuration"
    ),
    ConfigField(
        "DATABASE_PORT",
        int,
        "Database port",
        "Database Configuration"
    ),
    ConfigField(
        "DATABASE_NAME",
        str,
        "Name of the database to connect to (e.g., 'auth_db', 'myapp'). "
        "For PostgreSQL/MySQL, this is the specific database/schema name on the server.",
        "Database Configuration"
    ),
    ConfigField(
        "DATABASE_USER",
        str,
        "Database user",
        "Database Configuration"
    ),
    ConfigField(
        "DATABASE_PASSWORD",
        str,
        "Database password",
        "Database Configuration"
    ),
    ConfigField(
        "DATABASE_SQLITE_PATH",
        str,
        "SQLite database file path",
        "Database Configuration"
    ),
    
    # Connection Pool Settings
    ConfigField(
        "DATABASE_POOL_SIZE",
        int,
        "Database connection pool size",
        "Database Pool Configuration"
    ),
    ConfigField(
        "DATABASE_MAX_OVERFLOW",
        int,
        "Maximum overflow connections",
        "Database Pool Configuration"
    ),
    ConfigField(
        "DATABASE_POOL_TIMEOUT",
        int,
        "Pool connection timeout (seconds)",
        "Database Pool Configuration"
    ),
    ConfigField(
        "DATABASE_POOL_RECYCLE",
        int,
        "Pool recycle time (seconds)",
        "Database Pool Configuration"
    ),
    
    # Service Ports
    ConfigField(
        "PORT_SERVICE_GRPC",
        int,
        "gRPC service port",
        "Service Ports"
    ),
    ConfigField(
        "PORT_SERVICE_HTTP",
        int,
        "HTTP service port",
        "Service Ports"
    ),
    ConfigField(
        "PORT_MANAGE",
        int,
        "Management port",
        "Service Ports"
    ),
    ConfigField(
      "PORT_AUX",
      int,
      "Auxiliary process listens on this port",
      "Service Ports"
    ),
    # JWT Configuration
    ConfigField(
        "JWT_SECRET_KEY",
        str,
        "JWT secret key",
        "JWT Configuration"
    ),
    ConfigField(
        "JWT_ALGORITHM",
        str,
        "JWT algorithm (e.g., HS256)",
        "JWT Configuration"
    ),
    ConfigField(
        "JWT_EXPIRATION_HOURS",
        int,
        "JWT token expiration in hours",
        "JWT Configuration"
    ),
    
    # Security
    ConfigField(
        "BCRYPT_ROUNDS",
        int,
        "Bcrypt hashing rounds",
        "Security"
    ),
]


# Create convenient lookup dictionaries
CONFIG_FIELDS_BY_NAME: Dict[str, ConfigField] = {field.name: field for field in CONFIG_STRUCTURE}
CONFIG_GROUPS: Dict[str, List[ConfigField]] = {}
for field in CONFIG_STRUCTURE:
    if field.group not in CONFIG_GROUPS:
        CONFIG_GROUPS[field.group] = []
    CONFIG_GROUPS[field.group].append(field)
