

from _utils_import import Dict
import os
from .config_struct import CONFIG_STRUCTURE

def get_config_env():
    """
    Read configuration from docker run environment variables.
    These will override default config values.
    """
    config = Dict()
    
    # Iterate through all fields in config structure
    for field in CONFIG_STRUCTURE:
        value = os.getenv(field.name)
        if value is not None:
            # Convert value to the appropriate type
            config[field.name] = field.type(value)
    
    return config


from .config_default import config as config_default

config_docker_run = get_config_env()






