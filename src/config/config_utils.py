

from third_party.utils_python_global import _utils_file
import os
import pathlib


def get_config_save_dir_path():
  """
  Get the directory path where config JSON files should be saved.
  Determines path based on IS_DOCKER environment variable.
  
  Returns:
    str: Directory path for config files
  """
  is_docker = os.getenv('IS_DOCKER', 'false').lower() == 'true'
  
  if is_docker:
    dir_path = "/data/config/"
  else:
    # Development environment: use ./data/config/ relative to project root
    dir_path_current = os.path.dirname(os.path.realpath(__file__)) + "/"
    dir_path_src = pathlib.Path(dir_path_current).parent.absolute().__str__() + "/"
    dir_path_project_root = pathlib.Path(dir_path_src).parent.absolute().__str__() + "/"
    dir_path = dir_path_project_root + "data/config/"
  
  _utils_file.create_dir_for_file_path(dir_path + "dummy.txt")
  return dir_path


def get_config_file_name(layer_name):
  """
  Get the standardized JSON filename for a config layer.
  
  Args:
    layer_name: Name of the config layer (e.g., 'env', 'arg', 'dev', 'default')
  
  Returns:
    str: Filename in format 'config_{layer_name}.json'
  """
  return f"config_{layer_name}.json"
  