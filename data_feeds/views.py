"""
Socket IO App

Based off of: https://github.com/shanealynn/async_flask
"""

from random import random
import os
import time

import yaml
import redis
from data_feeds import socketio
from flask_socketio import emit
from flask import Flask, render_template
from threading import Thread, Event


CURR_DIR = os.path.dirname(__file__)

def read_yaml(yaml_file):
    """Read a yaml file.

    Args:
        yaml_file (str): Full path of the yaml file.

    Returns:
        data (dict): Dictionary of yaml_file contents. None is returned if an
        error occurs while reading.
    """

    with open(yaml_file) as file_in:
        data = yaml.safe_load(file_in)

    return data

CONF = read_yaml(os.path.join(CURR_DIR, 'private.yml'))
thread = Thread()



class SocketEmitter(Thread):
    def __init__(self, delay, channel):
        self.delay = delay
        self.channel = channel
        self.is_running = False
        super().__init__()


    def emit(self, number):
        """
        Emit data
        """
        print('Emitting {} to {}'.format(number, self.channel))
        socketio.emit('newnumber', {'number': number},
                      namespace=self.channel)
        time.sleep(self.delay)

class Temp(SocketEmitter):
    """Measure the raspberry pi internal temperature and emit

    Attributes:
        is_running (bool): Indicate whether the thread is active
    """

    def generate(self):
        while self.is_running:
            number = self.measure_temp()
            self.emit(number)

    def measure_temp(self):
        temp = os.popen("vcgencmd measure_temp").readline()
        parsed_temp = temp.replace("temp=", "").split("'C")[0]
        return float(parsed_temp)

    def run(self):
        self.is_running = True
        self.generate()

    def stop(self):
        self.is_running = False

class RedisListener(SocketEmitter):
    """Subscribe to a redis channel, emit messages when received

    Attributes:
        is_running (bool): Indicate whether the thread is active
    """
    def __init__(self, delay, socket_channel, redis_channel):
        self.redis = self.connect_redis()
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe([redis_channel])
        super().__init__(delay, socket_channel)

    def connect_redis(self):
        return redis.StrictRedis(
            host=CONF['redis']['host'],
            port=CONF['redis']['port'],
            db=CONF['redis']['db'],
            charset="utf-8",
            decode_responses=True
        )

    def generate(self):
        for i, item in enumerate(self.pubsub.listen()):
            if i == 0:
                continue

            if not self.is_running:
                self.pubsub.unsubscribe()
                print(self, "unsubscribed and finished")
                break
            else:
                number = float(item['data'])
                self.emit(number)

    def run(self):
        self.is_running = True
        self.generate()

    def stop(self):
        self.is_running = False

@socketio.on('connect', namespace='/test1')
def connect():
    # need visibility of the global thread object
    global thread
    print('Client connected test1')

    if not thread.isAlive():
        print ("Starting Thread")
        thread = RedisListener(delay=0, socket_channel='/test1',
                               redis_channel='pir')
        # thread = Temp(delay=2.5, channel='/test1')
        thread.start()

@socketio.on('disconnect', namespace='/test1')
def disconnect():
    print('Client disconnected test1')
    thread.stop()
