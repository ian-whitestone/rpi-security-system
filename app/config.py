import os
import logging
from datetime import datetime

import yaml

CURR_DIR = os.path.dirname(__file__)
IMG_DIR = os.path.join(CURR_DIR, 'imgs')
CONF_DIR = os.path.join(CURR_DIR, 'config')
LOG_DIR = os.path.join(CURR_DIR, 'logs')
TRAIN_DIR = os.path.join(CURR_DIR, 'train-data')

MAIN_CONF_PATH = os.path.join(CONF_DIR, 'config.yml')
PRIVATE_CONF_PATH = os.path.join(CONF_DIR, 'private.yml')

def read_yaml(yaml_file):
    """Read a yaml file.

    Args:
        yaml_file (str): Full path of the yaml file.

    Returns:
        data (dict): Dictionary of yaml_file contents. None is returned if an
        error occurs while reading.
    """

    with open(yaml_file) as file_in:
        data = yaml.safe_load(file_in)

    return data

def load_config():
    return read_yaml(MAIN_CONF_PATH)

def load_private_config():
    return read_yaml(PRIVATE_CONF_PATH)

def init_logging():
    """Initialize the logging setup

    """
    log_conf = read_yaml(os.path.join(CONF_DIR, 'logging.yml'))

    # log_base_file = datetime.now().strftime("%Y-%m-%d-%H-%M")
    # log_file = os.path.join(LOG_DIR, log_base_file)
    # log_conf['handlers']['file']['filename'] = log_file
    
    logging.config.dictConfig(log_conf)