

from _utils_import import Dict
import os
import json
from .config_utils import get_config_save_dir_path, get_config_file_name


def get_config_user():
    """
    Get user configuration set via management page or API.
    This layer represents online configuration changes.
    
    Logic:
    1. Load config from JSON file (if exists)
    2. Return the config
    
    Returns:
        Dict containing user-configured values
    """
    layer_name = "user"
    config_dir = get_config_save_dir_path()
    config_file = config_dir + get_config_file_name(layer_name)
    
    # Load config from JSON file
    config = Dict()
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = Dict(json.load(f))
    except Exception as e:
        print(f"Warning: Failed to load {config_file}: {e}")
    
    return config


def set_config_user(config_update):
    """
    Update user configuration via management page or API.
    
    Logic:
    1. Load existing config from JSON file (if exists)
    2. Merge: new values override existing values
    3. Save merged config to JSON file
    4. Return the merged config
    
    Args:
        config_update: Dict containing config fields to update
    
    Returns:
        Dict containing the updated full config
    """
    layer_name = "user"
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
    
    # Step 2: Merge configs (new values override existing values)
    merged_config = Dict(existing_config)
    merged_config.update(config_update)
    
    # Step 3: Save merged config to JSON file
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(dict(merged_config), f, indent=2, default=str)
        print(f"Config user layer updated and saved to {config_file}")
    except Exception as e:
        print(f"Error: Failed to save {config_file}: {e}")
        raise
    
    # Step 4: Return the merged config
    return merged_config
