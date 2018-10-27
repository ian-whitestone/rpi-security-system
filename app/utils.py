"""
Utils module, contains utility functions used throughout the postgrez codebase.
"""
import logging
import logging.config
import glob
import os
import sys
import subprocess
import ast
import signal
import time
import shutil

import cv2
import psutil
import boto3
from slackclient import SlackClient
import redis
import pantilthat

try:
    from app import config
except:
    import config

LOGGER = logging.getLogger(__name__)
CONF = config.load_private_config()
REDIS_CONN = redis.StrictRedis(
    host=CONF['redis']['host'],
    port=CONF['redis']['port'],
    db=CONF['redis']['db'],
    charset="utf-8",
    decode_responses=True
)

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

def save_image(filepath, frame):
    """Save an image
    Args:
        filepath (str): Filepath to save image to
        frame (numpy.ndarray): Image to save
    """
    LOGGER.debug('Saving image to %s' % filepath)
    cv2.imwrite(filepath, frame)
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

def slack_post_interactive(response):
    """Ingest the picture upload response and add a follow up message with
    buttons to tag the image

    Args:
        response (dict): Slack response from the image upload
    """
    if response['ok']:
        file_id = response['file']['id']
        file_title = response['file']['title']
        slack_client = SlackClient(CONF['app_token'])
        response = slack_client.api_call(
            "chat.postMessage",
            as_user=True,
            channel=CONF['alerts_channel'],
            text='Tag Image {}'.format(file_title),
            attachments= [{
                    "text": "How should this image be tagged",
                    "callback_id": "tag_image",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    'actions': [
                        {
                            "name": "occupied",
                            "text": "Occupied",
                            "type": "button",
                            "style": "primary",
                            "value": str({
                                'occupied': True,
                                'file_id': file_id,
                                'file_title': file_title
                            })
                        },
                        {
                            "name": "unoccupied",
                            "text": "Unoccupied",
                            "type": "button",
                            "style": "danger",
                            "value": str({
                                'occupied': False,
                                'file_id': file_id,
                                'file_title': file_title
                            })
                        }
                    ]
                }]
            )

    else:
        LOGGER.error('Failed image upload %s', response)

def slack_delete_file(file_id):
    """Delete a file in slack

    Args:
        file_id (str): File to delete

    Returns:
        dict: Slack response object
    """
    slack_client = SlackClient(CONF['ian_token'])
    response = slack_client.api_call(
        'files.delete',
        file=file_id
    )
    return response

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

    Returns:
        dict: Slack response object
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

    return response

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
    list_of_files = [f for f in list_of_files if os.path.isfile(f)]
    if list_of_files:
        last_file = max(list_of_files, key=os.path.getctime)
    else:
        LOGGER.error('No files in directory')

    return last_file

def search_path(path, filetypes=None):
    """Recursively search a path, optionally matching specific filetypes, and
    return all filenames.

    Args:
        path (str): Path to search
        filetypes (list, optional): Filetypes to return

    Returns:
        files (list): List of files
    """
    files = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        if filetypes:
            files.extend([os.path.join(dirpath, file) for file in filenames
                          if file.endswith(tuple(filetypes))])
        else:
            files.extend([os.path.join(dirpath, file) for file in filenames])
    return files

def upload_to_s3(s3_bucket, local, key):
    """Upload a list of files to S3.

    Args:
        s3_bucket (str): Name of the S3 bucket.
        files (list): List of files to upload
    """
    LOGGER.info("Attempting to load %s to s3 bucket: s3://%s, key: %s", local,
                s3_bucket, key)
    s3 = boto3.resource('s3')
    data = open(local, 'rb')
    s3.Bucket(s3_bucket).put_object(
        Key=key, Body=data, ServerSideEncryption='AES256')

def clean_dir(path, exclude=None):
    """Clear folders and files in a specified path

    Args:
        path (str): Path to clean files/folders
        exclude (list, optiona): Filenames to exclude from deletion
    """
    if not exclude:
        exclude = []

    for file in os.listdir(path):
        full_path = os.path.join(path, file)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
            assert not os.path.isdir(full_path)
        elif os.path.isfile(full_path) and file not in exclude:
            os.remove(full_path)
            assert not os.path.isfile(full_path)

def measure_temp():
    temp = os.popen("vcgencmd measure_temp").readline()
    parsed_temp = temp.replace("temp=", "").split("'C")[0]
    return float(parsed_temp)
