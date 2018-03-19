import eventlet
eventlet.monkey_patch()

from flask_socketio import SocketIO
from flask import Flask

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = "eventlet"
app = Flask('socket')


#turn the flask app into a socketio app
socketio = SocketIO(app, async_mode=async_mode)

from data_feeds import views
