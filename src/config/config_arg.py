
from _utils_import import Dict
import argparse
from .config_struct import CONFIG_GROUPS

def get_config_args(args=None):
    """
    Read configuration from command line arguments.
    These will override default config but be overridden by environment variables.
    
    Args:
        args: List of arguments to parse. If None, uses sys.argv
    
    Returns:
        Dict containing parsed config values
    """
    parser = argparse.ArgumentParser(
        description='Docker Auth Service Configuration',
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
    config = Dict()
    for key, value in vars(parsed_args).items():
        if value is not None:
            config[key] = value
    
    return config


# Parse command line arguments when module is imported
config_arg = get_config_args()
