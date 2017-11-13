"""
Utils module, contains utility functions used throughout the postgrez codebase.
"""

from .logger import create_logger
import yaml
import os
import re


log = create_logger(__name__, log_level='DEBUG')

def read_yaml(yaml_file):
    """Read a yaml file.
    Args:
        yaml_file (str): Full path of the yaml file.
    Returns:
        data (dict): Dictionary of yaml_file contents. None is returned if an
        error occurs while reading.
    Raises:
        Exception: If the yaml_file cannot be opened.
    """

    data = None
    try:
        with open(yaml_file) as f:
            # use safe_load instead load
            data = yaml.safe_load(f)
    except Exception as e:
        log.error('Unable to read file %s. Error: %s' % (yaml_file,e))

    return data
