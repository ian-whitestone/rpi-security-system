"""
Flask views module
"""
import time
import json
from datetime import datetime
import os
import random
import subprocess
import logging
from functools import wraps

from flask import request, make_response, render_template, Response, jsonify
from app import panner as pantilthat
from app import app
from app import utils
from app.camera import Camera
from app.gpio_data import GPIOData

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(__file__)
IMG_DIR = os.path.join(CURR_DIR, 'imgs')
TEMPLATES_DIR = os.path.join(CURR_DIR, 'templates')
CONF = utils.read_yaml(os.path.join(CURR_DIR, 'private.yml'))


def slack_verification(user=None):
    """Verify post request came from Slack by checking the token sent with the
    request. Optionally verify that the request came from a specific user

    Args:
        user (str, optional): User ID to verify, defaults to None and does not
            verify which user sent the request
    """
    def actual_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = utils.parse_slash_post(request.form)
            token = data.get('token', None)
            if not utils.validate_slack(token):
                return 'Un-authenticated'
            if user:
                if data.get('user_id', None) != user:
                    return 'No access to the ON command'
            return func(*args, **kwargs)
        return wrapper
    return actual_decorator

@app.route('/initialize', methods=["POST"])
@slack_verification(CONF['ian_uid'])
def initialize():
    """Initialize the security system app
    """
    # set redis variables
    LOGGER.info('Initializing camera redis variables')
    pantilthat.pan(40)
    pantilthat.tilt(10)
    utils.redis_set('home', False)
    utils.redis_set('auto_detect_status', True)
    utils.redis_set('camera_status', True)
    utils.redis_set('camera_notifications', True)
    utils.redis_set('save_images', True)
    utils.led(True)
    # kick of camera background process
    camera = Camera()

    LOGGER.info('Initializing GPIO redis variables')
    utils.redis_set('gpio_status', True)
    # kick of GPIO background process
    gpio = GPIOData()

    # kick off other background processes (image uploading, sensors etc.)
    # TODO: implement
    LOGGER.info('Initialization complete')
    return "Initialization completed"

@app.route('/hello', methods=["GET", "POST"])
@slack_verification()
def hello():
    """An example slash command function.

    Returns:
        str: Response sent back to slack
    """
    data = utils.parse_slash_post(request.form)
    LOGGER.info('hello slack command received with data: %s', data)
    return 'Hello {0}'.format(data['user_name'])

@app.route('/top', methods=["GET", "POST"])
@slack_verification()
def top():
    with open('top.log', 'w') as outfile:
      subprocess.call("top -n1 -b -c", shell=True, stdout=outfile)

    with open('top.log', 'r') as f:
        contents = "".join([next(f) for x in range(20)])
    return contents

@app.route('/status', methods=["GET", "POST"])
@slack_verification()
def status():
    """Get the status of the current redis configuration and camera position

    Returns:
        str: Response to slack
    """
    summary = """**PI SUMMARY**:
    pi_temperature: {}
    camera_position: Panned to {}. Tilted to {}
    camera_status: {}
    camera_notifications: {}
    save_images: {}
    gpio_status: {}
    auto_detect_status: {}
    home: {}
    """
    return summary.format(
        utils.measure_temp(),
        utils.get_pan(),
        utils.get_tilt(),
        utils.redis_get('camera_status'),
        utils.redis_get('camera_notifications'),
        utils.redis_get('save_images'),
        utils.redis_get('gpio_status'),
        utils.redis_get('auto_detect_status'),
        utils.redis_get('home')
    )

@app.route('/interactive', methods=["POST"])
def interactive():
    data = utils.parse_slash_post(request.form)

    payload = json.loads((data['payload']))
    action = payload['actions'][0]
    action_value = eval(action['value'])
    tag = action_value['occupied']
    file_title = action_value['file_title']
    # TODO: update database
    utils.slack_delete_file(action_value['file_id'])
    return 'Response for {} logged'.format(file_title)

@app.route('/pycam_on', methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def pycam_on():
    """Turn on the pycam process.

    Returns:
        str: Response to slack
    """
    if utils.redis_get('camera_status'):
        response = 'Pycam is already running'
    else:
        utils.redis_set('camera_status', True)
        utils.led(True)
        response = "Pycam has been turned on"
    return response

@app.route('/pycam_off', methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def pycam_off():
    """Turn off the pycam process.

    Returns:
        str: Response to slack
    """
    utils.redis_set('camera_status', False)
    utils.led(False)
    return "Pycam has been turned off"

@app.route('/gpio_on', methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def gpio_on():
    """Turn on the gpio data recording process.

    Returns:
        str: Response to slack
    """
    if utils.redis_get('gpio_status'):
        response = 'GPIO data is already running'
    else:
        utils.redis_set('gpio_status', True)
        response = "GPIO data has been turned on"
    return response

@app.route('/gpio_off', methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def gpio_off():
    """Turn off the gpio data recording process.

    Returns:
        str: Response to slack
    """
    utils.redis_set('gpio_status', False)
    return "GPIO data has been turned off"

@app.route('/auto_detect_on', methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def auto_detect_on():
    """Turn on the who is home auto detection process.

    Returns:
        str: Response to slack
    """
    if utils.redis_get('auto_detect_status'):
        response = 'Auto detect is already running'
    else:
        utils.redis_set('auto_detect_status', True)
        response = "Auto detect has been turned on"
    return response

@app.route('/auto_detect_off', methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def auto_detect_off():
    """Turn off the who is home auto detection process.

    Returns:
        str: Response to slack
    """
    utils.redis_set('auto_detect_status', False)
    return "Auto detect has been turned off"

@app.route('/save_images_on', methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def save_images_on():
    """Turn on the image saving process.

    Returns:
        str: Response to slack
    """
    utils.redis_set('save_images', True)
    return "Image saving been turned on"

@app.route('/save_images_off', methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def save_images_off():
    """Turn off the image saving process.

    Returns:
        str: Response to slack
    """
    utils.redis_set('save_images', False)
    return "Image saving been turned off"

@app.route('/notifications_off', methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def notifications_off():
    """Disable motion detected notifications

    Returns:
        str: Response to slack
    """
    utils.redis_set('camera_notifications', False)
    return "Notications have been disabled"

@app.route('/notifications_on', methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def notifications_on():
    """Enable motion detected notifications

    Returns:
        str: Response to slack
    """
    utils.redis_set('camera_notifications', True)
    return "Notications have been enable"

@app.route('/light_on', methods=["POST"])
@slack_verification()
def light_on():
    """Turn on light

    Returns:
        str: Response to slack
    """
    data = utils.parse_slash_post(request.form)
    light = data.get('text', '').strip().lower()
    if light not in ['kitchen', 'bedroom', 'other', 'led']:
        return 'Please specify kitchen, bedroom, led or other'
    code_map = {
        'kitchen': 4478403,
        'bedroom': 4470259,
        'other': 4478723
    }
    if light in ['kitchen', 'bedroom', 'other']:
        utils.codesend(code_map[light])
    else:
        utils.led(True)
    return 'Light {} turned on'.format(light)

@app.route('/light_off', methods=["POST"])
@slack_verification()
def light_off():
    """Turn off light

    Returns:
        str: Response to slack
    """
    data = utils.parse_slash_post(request.form)
    light = data.get('text', '').strip().lower()
    if light not in ['kitchen', 'bedroom', 'other', 'led']:
        return 'Please specify kitchen, bedroom, led or other'
    code_map = {
        'kitchen': 4478412,
        'bedroom': 4478268,
        'other': 4478732
    }
    if light in ['kitchen', 'bedroom', 'other']:
        utils.codesend(code_map[light])
    else:
        utils.led(False)
    return 'Light {} turned off'.format(light)

@app.route('/rotate', methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def rotate():
    """Rotate the camera

    Returns:
        str: Response to slack
    """
    data = utils.parse_slash_post(request.form)
    args = data['text'].split()

    if len(args) != 2:
        return ("Incorrect input. Please provide as two integers separated by "
                " a space. i.e. '0 0'")
    try:
        pan = int(args[0])
        tilt = int(args[1])
    except ValueError:
        return 'Did not receive integer arguments'

    curr_status = utils.redis_get('camera_status')
    if curr_status:
        utils.redis_set('camera_status', False)
        time.sleep(1)

    pantilthat.pan(pan)
    pantilthat.tilt(tilt)

    if curr_status:
        utils.redis_set('camera_status', True)

    response = 'Successfully panned to {0} and tilted to {1}'.format(pan, tilt)
    return response


@app.route('/current_position', methods=["GET", "POST"])
def current_position():
    """Get the current position of the camera.

    Returns:
        str: Response to slack
    """
    return 'Panned to {0}. Tilted to {1}'.format(utils.get_pan(),
                                                 utils.get_tilt())

@app.route('/web_rotate', methods=["GET", "POST"])
def web_rotate():
    """Rotate the camera for the live stream site

    Returns:
        str: Dummy response
    """
    pan = utils.get_pan()
    tilt = utils.get_tilt()
    rotate_dir = request.args.get('rotate')
    action = {
        'L': ('pan', pan + 20),
        'R': ('pan', pan + -20),
        'U': ('tilt', tilt + -20),
        'D': ('tilt', tilt + 20)
        }

    move = action[rotate_dir]
    rotate_function = getattr(pantilthat, move[0])
    rotate_function(move[1])
    return "Success"


@app.route("/last_image", methods=["GET", "POST"])
@slack_verification(CONF['ian_uid'])
def last_image():
    """Return the last image taken, optionally filtering for the last occupied
    or unnoccupied image

    Returns:
        str: Response to slack
    """
    data = utils.parse_slash_post(request.form)
    if data['text'] != '':
        text = data['text']
        if text.lower() == 'o' or text.lower() == 'u':
            ftype = ('occupied*' if text.lower() == 'o' else 'unoccupied*')
        else:
            return "Please specify 'O', 'U' or don't pass in anything"
    else:
        ftype = '*'
    # TODO: get channel the message came from
    latest_image = utils.latest_file(IMG_DIR, ftype)
    if latest_image:
        utils.slack_upload(latest_image, channel=data['channel_id'])
        response = 'Returned image: {0}'.format(os.path.basename(latest_image))
    else:
        response = 'No images found'
    return response


def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    mimetype = 'multipart/x-mixed-replace; boundary=frame'
    return Response(gen(Camera()), mimetype=mimetype)


@app.route('/raspberries')
def index():
    """Return the homepage html

    Returns:
        str: Homepage html
    """
    return render_template('index.html')


@app.route("/listening", methods=["GET", "POST"])
def hears():
    """
    This route listens for incoming events from Slack and uses the event
    handler helper function to route events to our Bot.

    Modified from: https://github.com/slackapi/Slack-Python-Onboarding-Tutorial
    """

    str_response = request.data.decode('utf-8')
    slack_event = json.loads(str_response)
    LOGGER.info('slack event: %s', slack_event)

    # ============= Slack URL Verification ============ #
    # In order to verify the url of our endpoint, Slack will send a challenge
    # token in a request and check for this token in the response our endpoint
    # sends back.
    #       For more info: https://api.slack.com/events/url_verification
    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200,
                             {"content_type": "application/json"})

    token = slack_event.get("token")
    if not validate_slack(token):
        message = "Invalid Slack verification token"
        # By adding "X-Slack-No-Retry" : 1 to our response headers, we turn off
        # Slack's automatic retries during development.
        return make_response(message, 403, {"X-Slack-No-Retry": 1})

    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                         you're looking for.", 404, {"X-Slack-No-Retry": 1})
