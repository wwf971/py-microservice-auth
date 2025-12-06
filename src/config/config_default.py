

from _utils_import import Dict


config = Dict(

# Database Configuration
DATABASE_TYPE = "sqlite",  # sqlite, postgresql, mysql
DATABASE_HOST = "localhost",
DATABASE_PORT = 5432,  # 5432 for postgres, 3306 for mysql
DATABASE_NAME = "auth_db",
DATABASE_USER = "auth_user",
DATABASE_PASSWORD = "",
DATABASE_SQLITE_PATH = "/data/auth.db",  # Will be overridden in non-Docker env

# Connection Pool Settings
DATABASE_POOL_SIZE = 10,
DATABASE_MAX_OVERFLOW = 20,
DATABASE_POOL_TIMEOUT = 30,
DATABASE_POOL_RECYCLE = 3600,

# Service Ports
PORT_SERVICE_GRPC = 16200, # the port that provides auth service
PORT_SERVICE_HTTP = 16201, # the port that provides auth service
PORT_MANAGE = 16202, # the port that provides manage UI
PORT_AUX = 16203, # auxiliary process API port

# JWT Configuration
JWT_SECRET_KEY = "change-this-secret-key-in-production",
JWT_ALGORITHM = "HS256",
JWT_EXPIRATION_HOURS = 24,

# Security
BCRYPT_ROUNDS = 12,

)

