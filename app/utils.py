"""
Utils module, contains utility functions used throughout the postgrez codebase.
"""
import logging
import glob
import os
import sys
import subprocess
import ast
import signal
import time
from datetime import datetime
import psutil

from slackclient import SlackClient
import yaml
import redis
from app import panner as pantilthat


LOGGER = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(__file__)

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

CONF = read_yaml(os.path.join(CURR_DIR, 'private.yml'))

REDIS_CONN = redis.StrictRedis(
    host=CONF['redis']['host'],
    port=CONF['redis']['port'],
    db=CONF['redis']['db'],
    charset="utf-8",
    decode_responses=True)

def pycam_logging(logger):
    """Initialize the pycam logging setup

    Args:
        logger (logging.Logger): logger object
    """
    log_base_file = datetime.now().strftime("%Y-%m-%d-%H-%M")
    log_file = os.path.join(CURR_DIR, 'logs', log_base_file)

    ## Define Handlers
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # create a logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return

def redis_get(key):
    """Fetch a key from redis

    Args:
        key (str): Key to fetch

    Returns:
        Value associated with redis key
    """
    str_obj = REDIS_CONN.get(key)

    # Need to research a better way of parsing underlying Python object types
    # from strings redis returns..
    try:
        value = ast.literal_eval(str_obj)
    except ValueError:
        value = str_obj
    except SyntaxError:
        value = str_obj
    return value

def redis_set(key, value):
    """Summary

    Args:
        key (str): Redis key name
        value (): Value to be associated with key
    """
    REDIS_CONN.set(key, value)
    return


def get_tilt():
    """Get the current tilt value

    Returns:
        int: Current tilt value
    """
    return pantilthat.get_tilt()

def get_pan():
    """Get the current pan value

    Returns:
        int: Current pan value
    """
    return pantilthat.get_pan()

def validate_slack(token):
    """Verify the request is coming from Slack by checking that the
    verification token in the request matches our app's settings

    Args:
        token (str): Slack token

    Returns:
        bool: Indicate whether token received matches known verification token
    """
    if CONF['rpi_cam_app']['verification_token'] != token:
        return False
    return True

def parse_slash_post(form):
    """Parses the Slack slash command data

    Args:
        form (ImmutableMultiDict): Info from the POST request, as an IMD object.

    Returns :
        data (dict): dictionary representation of the IMD if request was
            verified. Otherwise, returns False
    """
    raw_dict = form.to_dict(flat=False)
    data = {k:v[0] for k, v in raw_dict.items()}
    return data

def slack_post(message, channel=CONF['alerts_channel'],
               token=CONF['bot_token']):
    """Post a message to a channel

    Args:
        message (str): Message to post
        channel (str): Channel id. Defaults to alerts_channel specified in
            private.yml
        token (str): Token to use with SlackClient. Defaults to bot_token
            specified in private.yml
    """
    LOGGER.debug("Posting to slack")
    slack_client = SlackClient(token)
    response = slack_client.api_call(
        "chat.postMessage",
        as_user=True,
        channel=channel,
        text=message
        )
    if response['ok']:
        LOGGER.info('Posted succesfully')
    else:
        LOGGER.error('Unable to post, response: %s', response)

    return

def slack_upload(fname, title=None, channel=CONF['alerts_channel'],
                 token=CONF['bot_token']):
    """Upload a file to a channel

    Args:
        fname (str): Filepath
        title (str, optional): Title of the file. Defaults to fname
        channel (str): Channel id. Defaults to alerts_channel specified in
            private.yml
        token (str): Token to use with SlackClient. Defaults to bot_token
            specified in private.yml
    """
    if title is None:
        title = os.path.basename(fname)
    slack_client = SlackClient(token)
    response = slack_client.api_call(
        "files.upload",
        channels=channel,
        filename=fname,
        file=open(fname, 'rb'),
        title=title
        )

    if response['ok']:
        LOGGER.info('Uploaded succesfully')
    else:
        LOGGER.error('Unable to upload, response: %s', response)

def spawn_python_process(fname):
    """Spawn a python process.

    Args:
        fname (str): Name of the python job to start

    Returns:
        pid (int): process identification number of spawned process
    """
    pid = None
    try:
        LOGGER.info('Spawning python job %s', fname)
        process = subprocess.Popen(
            [sys.executable, fname],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
            )
        pid = process.pid
        LOGGER.info('Process succesfully spawned: %s', pid)
    except Exception as exc:
        LOGGER.error('Unable to spawn process due to error: \n %s', str(exc))
    return pid

def kill_python_process(pid):
    """Kill a running python process by name.

    Args:
        pid (int): process identification number of process to kill

    Returns:
        killed (bool): True if process was killed, otherwise False.
    """
    killed = False
    LOGGER.info('Attempting to kill %s', pid)
    try:
        if check_process(pid):
            LOGGER.info('Killing pid: %s', pid)
            os.kill(pid, signal.SIGKILL)
            time.sleep(2)
            status = check_process(pid)
            if not status:
                LOGGER.info('Successfully killed process')
                killed = True
        else:
            killed = True
    except Exception as exc:
        LOGGER.error('Unable to kill process due to error %s', str(exc))

    return killed

def check_process(pid):
    """Check if process is running.
    Args:
        pid (int): process identification number of process to check
    Returns:
        (bool): True if process is running, otherwise False
    """
    LOGGER.info('Checking if %s is running', pid)
    try:
        os.kill(pid, 0)
        proc = psutil.Process(pid)
        if proc.status() == psutil.STATUS_ZOMBIE:
            status = False
        else:
            LOGGER.info('Process %s is running', pid)
            status = True
    except OSError:
        status = False

    return status


def latest_file(path, ftype='*'):
    """Return the last file created in a directory.

    Args:
        path (str): Path of the directory
        ftype (str): Filetype to match. For example, supply '*.csv' to get the
            latest csv, or 'Master*'' to get the latest filename starting with
            'Master'. Defaults to '*' which matches all files.
    Returns:
        last_file (str): Last file created in the directory.
    """
    last_file = None
    if not os.path.isdir(path):
        LOGGER.error('Please supply a valid directory')
        return None

    if not path.endswith('/'):
        path += '/'

    list_of_files = glob.glob(path + ftype) # all filetypes
    if list_of_files:
        last_file = max(list_of_files, key=os.path.getctime)
    else:
        LOGGER.error('No files in directory')

    return last_file
