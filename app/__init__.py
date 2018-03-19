import eventlet
eventlet.monkey_patch()

from flask_socketio import SocketIO
from flask import Flask

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = "eventlet"
socket_app = Flask('socket')
main_app = Flask('main')

#turn the flask app into a socketio app
socketio = SocketIO(socket_app, async_mode=async_mode)


from app import views
from app import socket_views
from app import utils

utils.init_logging()