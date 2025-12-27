
from _utils_import import Dict
import argparse
import json
import os
from .config_struct import CONFIG_GROUPS
from .config_utils import get_config_save_dir_path, get_config_file_name

def get_config_args(args=None):
    """
    Read configuration from command line arguments.
    These will override default config but be overridden by environment variables.
    
    Logic:
    1. Load existing config from JSON file (if exists)
    2. Read new values from command line arguments
    3. Merge: command line args override persisted values
    4. Save merged config to JSON file
    5. Return the merged config
    
    This ensures config persists across container restarts while still allowing updates.
    
    Args:
        args: List of arguments to parse. If None, uses sys.argv
    
    Returns:
        Dict containing parsed config values
    """
    layer_name = "arg"
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
    
    # Step 2: Read new values from command line arguments
    parser = argparse.ArgumentParser(
        description='Docker Auth Service Config',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Create argument groups and add arguments from config structure
    argument_groups = {}
    for group_name, fields in CONFIG_GROUPS.items():
        # Create argument group
        group = parser.add_argument_group(group_name)
        argument_groups[group_name] = group
        
        # Add arguments for each field in this group
        for field in fields:
            # Generate CLI argument name: DATABASE_HOST -> --database-host
            cli_arg = '--' + field.name.lower().replace('_', '-')
            
            kwargs = {
                'dest': field.name,
                'help': field.description
            }
            # Add type parameter for non-string types
            if field.type != str:
                kwargs['type'] = field.type
            
            group.add_argument(cli_arg, **kwargs)
    
    # Parse arguments
    parsed_args = parser.parse_args(args)
    
    # Convert to Dict, excluding None values
    args_config = Dict()
    for key, value in vars(parsed_args).items():
        if value is not None:
            args_config[key] = value
    
    # Step 3: Merge configs (command line args override persisted values)
    merged_config = Dict(existing_config)
    merged_config.update(args_config)
    
    # Step 4: Save merged config to JSON file
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(dict(merged_config), f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: Failed to save {config_file}: {e}")
    
    # Step 5: Return the merged config
    return merged_config
