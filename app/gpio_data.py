import os
import logging
import threading
import time

import redis
import RPi.GPIO as GPIO
from app import utils

LOGGER = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(__file__)

REDIS_CONN = utils.REDIS_CONN


class GPIOData(object):
    thread = None  # background thread that reads GPIO data

    def __init__(self):
        self.pir = 21
        self.ultra_trig = 13
        self.ultra_echo = 19

        """Start the background thread if it isn't running yet."""
        LOGGER.info("Initializing GPIO data class")
        if GPIOData.thread is None:
            LOGGER.info('Starting GPIO thread')
            self.redis = REDIS_CONN
            # start thread
            GPIOData.thread = threading.Thread(target=self._thread,
                                               daemon=True)
            GPIOData.thread.start()
        else:
            LOGGER.info('GPIO thread has already been started')

    def _thread(self):
        while True:
            self.gpio_setup()
            if utils.redis_get('gpio_status'):
                LOGGER.info('Testing PIR: %s', self.measure_pir())
                LOGGER.info('Testing ULTRa: %s', self.measure_distance())
                while True:
                    if not utils.redis_get('gpio_status'):
                        LOGGER.info('Stopping GPIO data logging')
                        break
                    self.redis.publish('pir', self.measure_pir())
                    self.redis.publish('ultra', self.measure_distance())
                    time.sleep(0.2)
            else:
                time.sleep(2)
        GPIOData.thread = None


    def gpio_setup(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pir, GPIO.IN)
        GPIO.setup(self.ultra_trig, GPIO.OUT)
        GPIO.setup(self.ultra_echo, GPIO.IN)
        time.sleep(0.5)

    def measure_pir(self):
        return GPIO.input(self.pir)

    def measure_distance(self):
        # Send 10us pulse to trigger
        GPIO.output(self.ultra_trig, True)
        time.sleep(0.00001)
        GPIO.output(self.ultra_trig, False)

        loop_start = time.time()
        start = time.time()
        while GPIO.input(self.ultra_echo) == 0 and \
            (time.time() - loop_start) < 15:
            start = time.time()

        stop = time.time()
        while GPIO.input(self.ultra_echo) == 1 and \
            (time.time() - loop_start) < 15:
            stop = time.time()

        # if the signal was "timing out", return a bad value
        if (time.time() - loop_start) >= 15:
            return -999

        # Calculate pulse length
        elapsed = stop-start

        # Distance pulse travelled in that time is time
        # multiplied by the speed of sound (cm/s)
        distance = elapsed * 34000

        # That was the distance there and back so halve the value
        distance_cm = distance / 2
        distance_m = distance_cm / 100
        return distance_m
