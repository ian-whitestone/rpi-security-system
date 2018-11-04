"""
Main camera module; handles motion detection based on background subtraction.

Inspired & based off Adrian Rosebrock's excellent pyimagesearch tutorials.
"""
import os
import logging
import threading
import time
from datetime import datetime, timedelta
import pickle

import picamera
import cv2
from picamera.array import PiRGBArray
import numpy as np
import imutils
import RPi.GPIO as GPIO

import utils
import config
from model import MotionModel

LOGGER = logging.getLogger('security_system')
CONF = config.load_config()

config.init_logging()


class MotionDetector():

    def __init__(self):
        """Initialize the MotionDetector class
        """
        LOGGER.debug('Initializing motion detector class')

        # Store last <frame_store_cnt> frames in memory
        self.frames = []
        self.frame_store_cnt = CONF['frame_store_cnt'] 

        # PIR motion sensor settings
        self.pir_store_cnt = CONF['pir_store_cnt']
        self.PIR = 21
        self.pir_values = []
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

    def store_pir(self, pir_value):
        """Store the latest PIR value and trim the list of stored PIR values
        so it has a length of <self.pir_store_cnt>
        
        Args:
            pir_value (int): PIR sensor reading
        """
        self.pir_values.append(pir_value)
        self.pir_values = self.pir_values[-1*self.pir_store_cnt:]

    def store_frame(self, frame):
        """Store the latest frame and trim the list of stored frames
        so it has a length of <self.frame_store_cnt>
        
        Args:
            frame (numpy.ndarray): Frame to store
        """
        self.frames.append(frame)
        self.frames = self.frames[-1*self.frame_store_cnt:]

    def stream(self):
        """Loop through frames in the camera feed, process them, and return the
        contours from the frame delta (difference between current frame and
        background image) and the value of the PIR motion sensor.

        Yields:
            tuple: (Latest frame, thresholded frame delta, list of contours meta info)
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

                # save it
                self.store_frame(frame)

                gray = self.process_frame(frame)

                if avg is None:
                    LOGGER.info("Starting background model...")
                    avg = gray.copy().astype("float")
                    raw_capture.truncate(0)
                    continue

                # Update the background image
                cv2.accumulateWeighted(gray, avg, self.alpha)

                contours, frame_delta = self.compare_frame(gray, avg)
                self.store_pir(self.read_pir())
                
                # reset stream for next frame
                raw_capture.truncate(0)

                yield (frame, frame_delta, contours)

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
            tuple: (List of metadata for delta areas, delta frame)
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
        return contours_meta, thresh


class SecuritySystem(MotionDetector):

    def __init__(self):
        """Initialize the SecuritySystem class"""
        LOGGER.debug('Initializing security system class')

        self.model = MotionModel()

        # Timestamp formats
        self.ts_format_1 = "%Y-%m-%d %H:%M:%S"
        self.ts_format_2 = "%Y-%m-%d-%H-%M-%S.%f"

        # last time notification was sent in slack
        self.last_notified = datetime.now()

        # last time image was saved
        self.last_save = datetime.now() - timedelta(minutes=10)

        # record of last X frames and their classifications
        self.motion_store_cnt = CONF['motion_classification_store_cnt']
        self.motion_counter = []

        # Training settings
        self.train = CONF['train']
        self.bucket = CONF['bucket']

        # Notification/image saving options
        self.min_save_seconds = CONF["min_save_seconds"]
        self.min_notify_seconds = CONF['min_notify_seconds']
        self.min_occupied_fraction = CONF['min_occupied_fraction']

        super(SecuritySystem, self).__init__()

    def clear_stored_data(self):
        """Clear all stored values used in classification or in backtesting

        This function will be called after the camera has been turned off.
        """
        self.pir_values = []
        self.frames = []
        self.motion_counter = []

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

    def save_pickle(
        self, frames, frame_delta, contours, pir, ts, classification):
        """Save data to a pickle file

        Args:
            frames ([numpy.ndarray]): list of frames
            frame_delta (numpy.ndarray): Thresholded, delta image
            contours (list): List of contours metadata
            pir (list): List of pir sensor values
            ts (str): Timestamp
            classification (boolean): Occupied classifcation
        """
        frame = frames[-1]
        data = {
            'frame': frame,
            'frames': frames,
            'frame_delta': frame_delta,
            'contours': contours,
            'pir': pir,
            'classification': classification,
            'ts': ts
        }
        text = 'occupied' if classification else 'unoccupied'
        filename = '{}_{}.pkl'.format(text, ts)
        filepath = os.path.join(config.TRAIN_DIR, filename)
        pickle.dump(data, open(filepath, "wb"))

    def run(self):
        while True:
            if utils.redis_get('camera_status'):
                stream_iterator = self.stream()

                for frame, frame_delta, contours in stream_iterator:
                    timestamp = datetime.now()
                    ts = timestamp.strftime(self.ts_format_2)

                    # Classify latest frame as occupied or not
                    occupied = self.model.classify(
                        frame, contours, self.pir_values)

                    self.motion_counter.append(1 if occupied else 0)
                    self.motion_counter = self.motion_counter[
                        -1*self.motion_store_cnt:]

                    # Save latest image if enough time has elapsed since last save
                    last_save = (timestamp - self.last_save).seconds
                    if last_save >= self.min_save_seconds:
                        LOGGER.debug('Saving latest image')
                        self.save_last_image(frame, timestamp, 'latest', True)
                        self.last_save = timestamp

                        # Save for backtesting & training
                        if not occupied and self.train:
                            self.save_pickle(
                                self.frames, frame_delta, contours,
                                self.pir_values, ts, classification=False
                            )

                    # Determine whether to notify in slack
                    last_notified = (timestamp - self.last_notified).seconds
                    notify_time_check = last_notified >= self.min_notify_seconds
                    notifications_on = utils.redis_get('camera_notifications')
                    enough_motion = np.mean(self.motion_counter) \
                        >= self.min_occupied_fraction

                    if notifications_on and notify_time_check and enough_motion:
                        LOGGER.info('Sending slack alert!')
                        fpath = self.save_last_image(frame, timestamp, ts)
                        self.last_notified = timestamp
                        response = utils.slack_upload(
                            fpath, title=os.path.basename(fpath))
                        os.remove(fpath)

                        # Save for backtesting & training
                        if self.train:
                            utils.slack_post_interactive(response)
                            self.save_pickle(
                                self.frames, frame_delta, contours,
                                self.pir_values, ts, classification=True
                            )


                    if not utils.redis_get('camera_status'):
                        LOGGER.info('Clearing stored data')
                        self.clear_stored_data()
                        LOGGER.info('Stopping camera thread')
                        stream_iterator.close()
                        break
            else:
                time.sleep(2)

if __name__ == '__main__':
    LOGGER.info('Running security system')
    system = SecuritySystem()
    system.run()
