"""
Utils module, contains utility functions used throughout the postgrez codebase.
"""
import yaml
import os
import re
import sys
import subprocess, signal
from slackclient import SlackClient

from .logger import create_logger

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

CONF = read_yaml('app/private.yml')

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
    sc = SlackClient(token)
    sc.api_call("chat.postMessage", channel=channel, text=message)
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
        title = fname
    sc = SlackClient(token)
    sc.api_call("files.upload", channel=channel, filename=fname, title=title)

def spawn_python_process(fname):
    """Spawn a python process.
    Args:
        fname (str): Name of the python job to start
    Returns:
        pid (int): process identification number of spawned process
    """
    pid = None
    try:
        log.info('Spawning python job %s' % fname)
        p = subprocess.Popen(
                [sys.executable, fname],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
                )
        pid = p.pid
        log.info('Process succesfully spawned: %s' % pid)
    except Exception as e:
        log.error('Unable to spawn process due to error: \n %s' % str(e))
    return pid

def kill_process(pid):
    """Kill a running process.
    Args:
        pid (int): process identification number of process to kill
    Returns:
        killed (bool): True if process was killed, otherwise False.
    """
    killed = False
    log.info('Attempting to kill %s' % pid)
    try:
        if check_process(pid):
            os.kill(pid, signal.SIGKILL)
            killed = check_process(pid)
            if killed:
                log.info('Successfully killed process')
        else:
            killed = True
    except Exception as e:
        log.error('Unable to kill process due to error %s' % str(e))

    return killed

def check_process(pid):
    """Check if process is running.
    Args:
        pid (int): process identification number of process to check
    Returns:
        status (bool): True if process is running, otherwise False
    """
    log.info('Checking if %s is running' % pid)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True
