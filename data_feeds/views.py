"""
Socket IO App

Based off of: https://github.com/shanealynn/async_flask
"""

from data_feeds import socketio
from flask_socketio import emit
from flask import Flask, render_template
from random import random
from time import sleep
from threading import Thread, Event

thread = Thread()

class RandomThread(Thread):
    def __init__(self, channel):
        self.delay = 5
        self.channel = channel
        super(RandomThread, self).__init__()

    def generate(self):
        """
        Generate a random number and emit to namespace
        """
        print ("Making random numbers")
        while self._is_running:
            number = round(random()*100, 3)
            print ('Emitting {} to {}'.format(number, self.channel))
            socketio.emit('newnumber', {'number': number}, namespace=self.channel)
            sleep(self.delay)

    def run(self):
        self._is_running = True
        self.generate()

    def stop(self):
        self._is_running = False

@socketio.on('connect', namespace='/test1')
def connect():
    # need visibility of the global thread object
    global thread
    print('Client connected test1')

    if not thread.isAlive():
        print ("Starting Thread")
        thread = RandomThread('/test1')
        thread.start()

@socketio.on('disconnect', namespace='/test1')
def disconnect():
    print('Client disconnected test1')
    thread.stop()
