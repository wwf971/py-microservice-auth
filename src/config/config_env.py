

from _utils_import import Dict
import os
import json
from .config_struct import CONFIG_STRUCTURE
from .config_utils import get_config_save_dir_path, get_config_file_name

def get_config_env():
    """
    Read configuration from docker run environment variables.
    These will override default config values.
    
    Logic:
    1. Load existing config from JSON file (if exists)
    2. Read new values from environment variables
    3. Merge: env vars override persisted values
    4. Save merged config to JSON file
    5. Return the merged config
    
    This ensures config persists across container restarts while still allowing updates.
    """
    layer_name = "env"
    config_dir = get_config_save_dir_path()
    config_file = config_dir + get_config_file_name(layer_name)
    
    # Step 1: Load existing config from JSON file
    existing_config = Dict()
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                existing_config = Dict(json.load(f))
    except Exception as e:
        print(f"Warning: Failed to load {config_file}: {e}")
    
    # Step 2: Read new values from environment variables
    env_config = Dict()
    for field in CONFIG_STRUCTURE:
        value = os.getenv(field.name)
        if value is not None:
            # Convert value to the appropriate type
            env_config[field.name] = field.type(value)
    
    # Step 3: Merge configs (env vars override persisted values)
    merged_config = Dict(existing_config)
    merged_config.update(env_config)
    
    # Step 4: Save merged config to JSON file
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(dict(merged_config), f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: Failed to save {config_file}: {e}")
    
    # Step 5: Return the merged config
    return merged_config






