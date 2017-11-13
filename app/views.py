from flask import Flask, request, make_response, render_template
import json

from app import app
from .logger import create_logger
from .utils import read_yaml

log = create_logger(__name__, log_level='DEBUG')

CONF = read_yaml('app/private.yml')

@app.route('/hello', methods=["GET", "POST"])
def hello():
    # immutable multi-dict
    imd = request.form
    data = imd.to_dict(flat=False)
    log.info('hello slach command received with data: %s' % data)
    token = data['token'][0]
    text = data['text'][0]
    
    if _validate_slack(token) == False:
        return 'Error'
    
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
