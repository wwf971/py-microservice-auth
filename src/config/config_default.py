

from _utils_import import Dict


config = Dict(

# Database Configuration
# DATABASE_LIST stores multiple database connections
# The first entry (id=0) is always the local SQLite database and cannot be removed
DATABASE_LIST = [
    {
        "id": 0,
        "name": "Local SQLite",
        "type": "sqlite",
        "path": "../data/auth.db",  # Relative to src/ directory (where servers run)
        "host": None,
        "port": None,
        "database": None,
        "username": None,
        "password": None,
        "is_default": True,
        "is_removable": False
    }
],

# Currently active database ID
CURRENT_DATABASE_ID = 0,

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
# For production, generate RSA keys with:
#   openssl genrsa -out private_key.pem 2048
#   openssl rsa -in private_key.pem -pubout -out public_key.pem
JWT_ALGORITHM = "RS256",  # Use RSA for asymmetric signing
JWT_EXPIRATION_HOURS = 24,
JWT_PRIVATE_KEY = None,  # Path to private key file or PEM string (for signing)
JWT_PUBLIC_KEY = None,   # Path to public key file or PEM string (for verification)

# Security
BCRYPT_ROUNDS = 12,

MANAGE_USERNAME = "root",
MANAGE_PASSWORD = "password",
)


