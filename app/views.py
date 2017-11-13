from flask import Flask, request, make_response, render_template
import json
from datetime import datetime

from app import app
from .logger import create_logger
from .utils import read_yaml, spawn_python_process, check_process, kill_process,
                    latest_file

log = create_logger(__name__, log_level='DEBUG')

CONF = read_yaml('app/private.yml')
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
    return 'Success'

@app.route('/on', methods=["GET", "POST"])
def on():
    global PID
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    #TODO: turn into a decorator
    if data['user_id'] != CONF['ian_uid']:
        return 'No access to the ON command'

    # check if process is already running, if not, start it
    print (PID)
    if PID is None:
        PID = spawn_python_process('pycam.py')
        return ('Spawned PID: {0}. Keep track of this PID in order to kill it '
                'later with the /off command'.format(PID)
                )
    else:
        return 'Already ON'

@app.route('/off', methods=["GET", "POST"])
def off():
    global PID
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    if data['user_id'] != CONF['ian_uid']:
        return 'No access to the OFF command'

    if PID is not None:
        if check_process(PID) == False:
            return 'Already OFF'
        try:
            int(data['text'])
        except ValueError:
            return 'Must supply the integer PID'

        if int(data['text']) != PID:
            return 'Invalid PID to kill! Type {0} to confirm kill'.format(PID)
        else:
            killed = kill_process(PID)
            if killed:
                PID = None
                return 'Success'
            else:
                return 'Failed to kill process'
    else:
        return 'Already OFF'

    log.info('OFF slack command received with data: %s' % data)
    text = data['text']

@app.route('/status', methods=["GET", "POST"])
def status():
    global PID

    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    if PID is not None:
        if check_process(PID) == False:
            return 'PiCam Status: OFF'
        else:
            return 'PiCam Status: ON'
    else:
        return 'PiCam Status: OFF'


def _validate_slack(token):
        # ============ Slack Token Verification =========== #
    # We can verify the request is coming from Slack by checking that the
    # verification token in the request matches our app's settings
    if CONF['rpi_cam_app']['verification_token'] != token:
        return False
    return True

@app.route("last_image", methods=["GET", "POST"])
def last_image():
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    if 'text' in data.keys():
        text = data['text']
        if text.lower() == 'o' or text.lower() == 'u':
            ftype = ('Occupied' if text.lower() == 'o' else 'Unoccupied')
        else:
            return "Please specify 'O', 'U' or don't pass in anything"
    # TODO: get channel the message came from
    latest_file = latest_file()

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
    return 'Hello world: {0}'.format(timestamp.strftime('%Y-%m-%d %H:%M:%S'))
