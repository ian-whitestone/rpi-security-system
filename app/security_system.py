"""
Main camera module; handles motion detection based on background subtraction.

Based off Adrian Rosebrock's excellent tutorials here:

http://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
"""
import os
import logging
import threading
import time
from datetime import datetime, timedelta

import picamera
import cv2
from picamera.array import PiRGBArray
import numpy as np
import imutils
import RPi.GPIO as GPIO

import utils
import config

LOGGER = logging.getLogger('security_system')
CONF = config.load_config()

config.init_logging()

class MotionDetector():

    def __init__(self):
        """Initialize the MotionDetector class
        """
        LOGGER.debug('Initializing motion detector class')
        # GPIO PIN the PIR motion sensor is attached to
        self.PIR = 21
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PIR, GPIO.IN)

        # Camera Configuration
        self.resolution = CONF['resolution']
        self.fps = CONF['fps']
        self.frame_width = CONF['frame_width']
        self.vflip = CONF['vflip']
        self.hflip = CONF['hflip']
        self.alpha = CONF['alpha']
        self.dilate_iterations = CONF['dilate_iterations']
        self.ksize = tuple(CONF['ksize'])
        self.delta_thresh = CONF["delta_thresh"]

    def read_pir(self):
        """Read signal from PIR motion sensor

        Returns:
            int: 1 if motion is present, 0 otherwise
        """
        return GPIO.input(self.PIR)

    def stream(self):
        """Loop through frames in the camera feed, process them, and return the
        contours from the frame delta (difference between current frame and
        background image) and the value of the PIR motion sensor.

        Yields:
            tuple: (Latest frame, list of contours meta info, the value from the PIR sensor)
        """
        LOGGER.info('Starting camera process')

        with picamera.PiCamera() as camera:
            LOGGER.debug('Warming up camera')
            time.sleep(2)

            camera.vflip = self.vflip
            camera.hflip = self.hflip
            camera.resolution = tuple(self.resolution)
            camera.framerate = self.fps
            avg = None

            raw_capture = PiRGBArray(camera, size=tuple(self.resolution))
            for frame in camera.capture_continuous(raw_capture, 'bgr',
                                                   use_video_port=True):
                # return current frame
                frame = frame.array

                gray = self.process_frame(frame)

                if avg is None:
                    LOGGER.info("Starting background model...")
                    avg = gray.copy().astype("float")
                    raw_capture.truncate(0)
                    continue

                # Update the background image
                cv2.accumulateWeighted(gray, avg, self.alpha)

                contours = self.compare_frame(gray, avg)
                pir_value = self.read_pir()

                # reset stream for next frame
                raw_capture.truncate(0)

                yield (frame, contours, pir_value)

    def process_frame(self, frame):
        """Convert the latest frame to grayscale and blur it

        Args:
            frame (numpy.ndarray): Original frame

        Returns:
            numpy.ndarray: Blurred, grayscale frame
        """
        frame = imutils.resize(frame, width=self.frame_width)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, self.ksize, 0)
        return gray

    def compare_frame(self, frame, avg):
        """Compare the latest frame to the background image

        1) Take the difference between the background average and the latest frame
        2) Threshold it
        3) Dilute it
        4) Find contours and return metadata about them (area and coordinates)

        Args:
            frame (numpy.ndarray): Blurred, grayscale frame
            avg (numpy.ndarray): Running average of the images

        Returns:
            list: List of metadata for delta areas
        """


        frame_delta = cv2.absdiff(frame, cv2.convertScaleAbs(avg))

        # threshold the delta image, dilate the thresholded image to fill
        # in holes, then find contours on thresholded image
        thresh = cv2.threshold(frame_delta, self.delta_thresh, 255,
                               cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=self.dilate_iterations)
        contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
        contours = contours[1]

        contours_meta = []

        # loop over the contours
        for contour in contours:
            meta = {}
            meta['coords'] = cv2.boundingRect(contour)
            meta['size'] = cv2.contourArea(contour)
            contours_meta.append(meta)
        return contours_meta


class SecuritySystem(MotionDetector):

    def __init__(self):
        """Initialize the SecuritySystem class"""
        LOGGER.debug('Initializing security system class')
        
        # Timestamp formats
        self.ts_format_1 = "%Y-%m-%d %H:%M:%S"
        self.ts_format_2 = "%Y-%m-%d-%H-%M-%S.%f"

        # last time notification was sent in slack
        self.last_notified = datetime.now() + timedelta(minutes=1)

        # last time image was saved
        self.last_save = datetime.now() - timedelta(minutes=10)

        # number of consecutive motion frames detected
        self.motion_counter = 0

        # list of frames & metadata for storage
        self.frames_hist = []

        # Training settings
        self.train = CONF['train']
        self.bucket = CONF['bucket']

        # Notification/image saving options
        self.min_save_seconds = CONF["min_save_seconds"]
        self.min_notify_seconds = CONF['min_notify_seconds']

        # Tune-able parameters
        self.min_area = CONF['min_area']
        self.min_motion_frames = CONF['min_motion_frames']
        self.frame_store_cnt = CONF['frame_store_cnt']

        super(SecuritySystem, self).__init__()

    def save_last_image(self, frame, timestamp, img_name, add_text=False):
        """Optinally overlay the timestamp on the latest image, then save it.
        
        Args:
            frame (numpy.ndarray): Image to save
            timestamp (datetime.datetime): Timestamp
            img_name (str): Name to use in the file
            add_text (bool): Overlay timestamp on the image
        
        Returns:
            str: Filepath of the saved image
        """
        if add_text:
            ts = timestamp.strftime(self.ts_format_1)
            cv2.putText(frame, ts, (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
        filename = '{}.jpg'.format(img_name)
        fpath = os.path.join(config.IMG_DIR, filename)
        utils.save_image(fpath, frame)
        return fpath

    def classify(frame, contours, pir):
        """Classify whether the system should flag motion being detected
        
        Args:
            frame (numpy.ndarray): Image to save
            contours (list): List of contours meta
            pir (list): List of PIR motion sensor values
        
        Returns:
            bool: Motion classification
        """
        
        #TODO: IMPLEMENT ME!
        return False

    def save_pickle(self, frame, contours, pir, ts, classification):
        pass

    def run(self):
        while True:
            if utils.redis_get('camera_status'):
                stream_iterator = self.stream()

                for frame, contours, pir in stream_iterator:
                    timestamp = datetime.now()
                    ts = timestamp.strftime(self.ts_format_2)
                    
                    # Classify latest frame as occupied or not
                    occupied = self.classify(frame, contours, pir)

                    # Save latest image if enough time has elapsed since last save
                    last_save = (timestamp - self.last_save).seconds
                    if last_save >= self.min_save_seconds:
                        self.save_last_image(frame, timestamp, 'latest')
                        self.last_save = timestamp

                        # Save for backtesting & training
                        if not occupied and self.train:
                            self.save_pickle(frame, contours, pir, ts, False)

                    # Determine whether to notify in slack
                    last_notified = (timestamp - self.last_notified).seconds
                    if utils.redis_get('camera_notifications') and \
                        last_notified >= self.min_notify_seconds:                        
                        fpath = self.save_last_image(frame, timestamp, ts)
                        self.last_notified = timestamp
                        response = utils.slack_upload(
                            fpath, title=os.path.basename(fpath))
                        os.remove(fpath)

                        # Save for backtesting & training
                        if self.train:
                            utils.slack_post_interactive(response)
                            self.save_pickle(frame, contours, pir, ts, True)


                    if not utils.redis_get('camera_status'):
                        LOGGER.info('Stopping camera thread')
                        stream_iterator.close()
                        break
            else:
                time.sleep(2)

if __name__ == '__main__':
    LOGGER.info('Running security system')
    system = SecuritySystem()
    system.run()
