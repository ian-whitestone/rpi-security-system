from flask import Flask, request, make_response, render_template
import json

from app import app
from .logger import create_logger
from .utils import read_yaml

log = create_logger(__name__, log_level='DEBUG')

CONF = read_yaml('app/private.yml')

def _parse_slash_post(form):
    """Verifies a request came from slack and parses the form in the POST
    request that comes from Slack when a custom slash command is used.

    Args:
        form (ImmutableMultiDict): Info from the POST request, as an IMD object.
    Returns :
        data (dict): dictionary representation of the IMD if request was
            verified. Otherwise, returns False
    """
    raw_dict = imd.to_dict(flat=False)
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
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'

    ## validate user who sent the request, return no access 

    # check if process is already running, if not, start it
    # if already running, return "already running"

    log.info('ON slack command received with data: %s' % data)
    text = data['text']
    return 'Success'

@app.route('/off', methods=["GET", "POST"])
def off():
    ## validate user who sent the request
    data = _parse_slash_post(request.form)
    if data == False:
        return 'Error'
    log.info('OFF slack command received with data: %s' % data)
    text = data['text']
    return 'Success'

def _validate_slack(token):
        # ============ Slack Token Verification =========== #
    # We can verify the request is coming from Slack by checking that the
    # verification token in the request matches our app's settings
    if CONF['rpi_cam_app']['verification_token'] != token:
        return False
    return True


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
    return 'Hello world'
