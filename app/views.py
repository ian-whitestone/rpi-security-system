from flask import Flask, request, make_response, render_template
import json
from datetime import datetime
import os
from app import panner as pantilthat
import random
import subprocess

from app import app
from .utils import read_yaml, spawn_python_process, check_process, \
                    latest_file, slack_upload, kill_process


currDir = os.path.dirname(__file__)
imgsDir = os.path.join(currDir, 'imgs')
templatesDir = os.path.join(currDir, 'templates')
CONF = read_yaml(os.path.join(currDir, 'private.yml'))
PID = None

def _parse_slash_post(form):
    """Verifies a request came from slack and parses the form in the POST
    request that comes from Slack when a custom slash command is used.

    Args:
        form (ImmutableMultiDict): Info from the POST request, as an IMD object.
    Returns :
        data (dict): dictionary representation of the IMD if request was
            verified. Otherwise, returns False
    """
    raw_dict = form.to_dict(flat=False)
    data = {k:v[0] for k,v in raw_dict.items()}

    if _validate_slack(data['token']) == False:
        return False

    return data

@app.route('/hello', methods=["GET", "POST"])
def hello():
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'
    log.info('hello slack command received with data: %s' % data)
    text = data['text']
    return 'Hello {0}'.format(data['user_name'])

@app.route('/on', methods=["GET", "POST"])
def on():
    global PID
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    #TODO: turn into a decorator
    if data['user_id'] != CONF['ian_uid']:
        return 'No access to the ON command'

    if PID is not None:
        if check_process(PID) == False:
            PID = None

    # check if process is already running, if not, start it
    if PID is None:
        PID = spawn_python_process(os.path.join(currDir, 'pycam.py'))
        return ('Spawned PID: {0}. Keep track of this PID in order to kill it '
                'later with the /off command'.format(PID))
    else:
        return 'PiCam is already ON'

def turn_off_pycam():
    global PID

    if PID is not None:
        if check_process(PID) == False:
            return 'PiCam is already OFF'

        killed = kill_process(PID)
        if killed:
            message = 'Successfully killed {0}'.format(PID)
            PID = None
            return message
        else:
            return 'Failed to kill process {0}'.format(PID)
    else:
        return 'PiCam is already OFF'

@app.route('/off', methods=["GET", "POST"])
def off():
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    if data['user_id'] != CONF['ian_uid']:
        return 'No access to the OFF command'

    return turn_off_pycam()


@app.route('/stream_on', methods=["GET", "POST"])
def stream_on():
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    if data['user_id'] != CONF['ian_uid']:
        return 'No access to the Stream ON command'

    turn_off_pycam()
    pwd = random.randint(1,10000)
    cmd = ["bash", os.path.join(currDir, "stream.sh"), str(pwd)]
    subprocess.Popen(cmd)
    return "Started video stream with password: {0}".format(pwd)

@app.route('/stream_off', methods=["GET", "POST"])
def stream_off():
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    if data['user_id'] != CONF['ian_uid']:
        return 'No access to the Stream OFF command'

    subprocess.Popen(['pkill', 'uv4l'])
    return "Successfully killed uv4l stream"

@app.route('/status', methods=["GET", "POST"])
def status():
    global PID

    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    if PID is not None:
        if check_process(PID) == False:
            PID = None
            return 'PiCam Status: OFF'
        else:
            return 'PiCam Status: ON. Running under {0}'.format(PID)
    else:
        return 'PiCam Status: OFF'

@app.route('/rotate', methods=["GET", "POST"])
def rotate():
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    args = data['text'].split()

    if len(args) != 2:
        return ("Incorrect input. Please provide as two integers separated by "
                    " a space. i.e. '0 0'")
    try:
        pan = int(args[0])
        tilt = int(args[1])
    except ValueError:
        return 'Did not receive integer arguments'

    turn_off_pycam()

    pantilthat.pan(pan)
    pantilthat.tilt(tilt)
    PID = spawn_python_process(os.path.join(currDir, 'pycam.py'))

    message = ('Successfully panned to {0} and tilted to {1}. Spawned new '
                'process - PID {2}'.format(pan, tilt, PID))
    return message

def get_tilt():
    return pantilthat.get_tilt()

def get_pan():
    return pantilthat.get_pan()

@app.route('/current_position', methods=["GET", "POST"])
def current_position():
    return 'Panned to {0}. Tilted to {1}'.format(get_pan(), get_tilt())

@app.route('/web_rotate', methods=["GET", "POST"])
def web_rotate():
    pan = get_pan()
    tilt = get_tilt()
    rotate = request.args.get('rotate')
    action = {
        'L': ('pan', pan + 5),
        'R': ('pan', pan + -5),
        'U': ('tilt', tilt + -5),
        'D': ('tilt', tilt + 5)
        }

    if rotate in action.keys():
        move = action[rotate]
        getattr(pantilthat, move[0])(move[1])
    return "Success"

def _validate_slack(token):
        # ============ Slack Token Verification =========== #
    # We can verify the request is coming from Slack by checking that the
    # verification token in the request matches our app's settings
    if CONF['rpi_cam_app']['verification_token'] != token:
        return False
    return True

@app.route("/last_image", methods=["GET", "POST"])
def last_image():
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    if data['text'] != '':
        text = data['text']
        if text.lower() == 'o' or text.lower() == 'u':
            ftype = ('Occupied*' if text.lower() == 'o' else 'Unoccupied*')
        else:
            return "Please specify 'O', 'U' or don't pass in anything"
    else:
        ftype = '*'
    # TODO: get channel the message came from
    last_image = latest_file(imgsDir, ftype)
    if last_image:
        slack_upload(last_image, channel=data['channel_id'])
        return 'Returned image: {0}'.format(os.path.basename(last_image))
    else:
        return 'No images found'

@app.route("/listening", methods=["GET", "POST"])
def hears():
    """
    This route listens for incoming events from Slack and uses the event
    handler helper function to route events to our Bot.

    Modified from: https://github.com/slackapi/Slack-Python-Onboarding-Tutorial
    """

    str_response = request.data.decode('utf-8')
    slack_event = json.loads(str_response)
    log.info('slack event: %s' % slack_event)

    # ============= Slack URL Verification ============ #
    # In order to verify the url of our endpoint, Slack will send a challenge
    # token in a request and check for this token in the response our endpoint
    # sends back.
    #       For more info: https://api.slack.com/events/url_verification
    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type":
                                                             "application/json"
                                                             })

    token = slack_event.get("token")
    if _validate_slack(token) == False:
        message = "Invalid Slack verification token"
        # By adding "X-Slack-No-Retry" : 1 to our response headers, we turn off
        # Slack's automatic retries during development.
        return make_response(message, 403, {"X-Slack-No-Retry": 1})

    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                         you're looking for.", 404, {"X-Slack-No-Retry": 1})


@app.route('/')
def index():
    timestamp = datetime.now()
    # return 'Hello world: {0}'.format(timestamp.strftime('%Y-%m-%d %H:%M:%S'))
    return render_template('index.html')
