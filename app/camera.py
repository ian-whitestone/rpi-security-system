"""
Main camera module; handles motion detection and returning frames to clients.

Based off Miguel Grinberg's fantastic tutorial:
https://blog.miguelgrinberg.com/post/flask-video-streaming-revisited
"""
import os
import threading
from _thread import get_ident
import logging
import io
import time
from datetime import datetime, timedelta

import picamera
import cv2
from picamera.array import PiRGBArray
import numpy as np
import imutils
from app import utils

LOGGER = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(__file__)
CONF = utils.read_yaml(os.path.join(CURR_DIR, 'config.yml'))
IMG_DIR = os.path.join(CURR_DIR, 'imgs')

class CameraEvent(object):
    """An Event-like class that signals all active clients when a new frame is
    available.

    Taken directly from:
    https://github.com/miguelgrinberg/flask-video-streaming
    """
    def __init__(self):
        self.events = {}

    def wait(self):
        """Invoked from each client's thread to wait for the next frame."""
        ident = get_ident()
        if ident not in self.events:
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
        return self.events[ident][0].wait()

    def set(self):
        """Invoked by the camera thread when a new frame is available."""
        now = time.time()
        remove = None
        for ident, event in self.events.items():
            if not event[0].isSet():
                # if this client's event is not set, then set it
                # also update the last set timestamp to now
                event[0].set()
                event[1] = now
            else:
                # if the client's event is already set, it means the client
                # did not process a previous frame
                # if the event stays set for more than 5 seconds, then assume
                # the client is gone and remove it
                if now - event[1] > 5:
                    remove = ident
        if remove:
            del self.events[remove]

    def clear(self):
        """Invoked from each client's thread after a frame was processed."""
        self.events[get_ident()][0].clear()


class BaseCamera(object):
    thread = None  # background thread that reads frames from camera
    frame = None  # current frame is stored here by background thread
    event = CameraEvent()

    last_occ_uploaded = datetime.now() # last occupied image upload
    # last un-occupied image upload
    last_unocc_uploaded = datetime.now() - timedelta(minutes=10)
    motion_counter = 0 # number of consecutive motion frames detected
    frames_hist = [] # list of frames & metadata for storage

    def __init__(self):
        """Start the background camera thread if it isn't running yet."""
        LOGGER.info("Initializing base camera class")
        if BaseCamera.thread is None:
            BaseCamera.last_access = time.time()

            # start background frame thread
            BaseCamera.thread = threading.Thread(target=self._thread,
                                                 daemon=True)
            BaseCamera.thread.start()


    def get_frame(self):
        """Return the current camera frame."""
        BaseCamera.last_access = time.time()

        # wait for a signal from the camera thread
        BaseCamera.event.wait()
        BaseCamera.event.clear()

        return BaseCamera.frame

    @staticmethod
    def frames():
        """"Generator that returns frames from the camera."""
        raise RuntimeError('Must be implemented by subclasses.')

    def _thread(self):
        """Camera background thread."""
        while True:
            if utils.redis_get('camera_status'):
                frames_iterator = self.frames()
                for frame in frames_iterator:
                    BaseCamera.frame = frame
                    BaseCamera.event.set()  # send signal to clients

                    if not utils.redis_get('camera_status'):
                        LOGGER.info('Stopping camera thread')
                        frames_iterator.close()
                        break
            else:
                time.sleep(2)
        BaseCamera.thread = None


class Camera(BaseCamera):

    def __init__(self):
        self.resolution = CONF['resolution']
        self.fps = CONF['fps']
        self.min_area = CONF['min_area']
        self.delta_thresh = CONF["delta_thresh"]
        self.occ_min_upload_seconds = CONF["occ_min_upload_seconds"]
        self.unocc_min_upload_seconds = CONF["unocc_min_upload_seconds"]
        self.min_motion_frames = CONF['min_motion_frames']
        self.frame_width = CONF['frame_width']
        self.vflip = CONF['vflip']
        self.hflip = CONF['hflip']
        self.alpha = CONF['alpha']
        self.dilate_iterations = CONF['dilate_iterations']
        self.ksize = tuple(CONF['ksize'])
        self.frame_store_cnt = CONF['frame_store_cnt']
        super(Camera, self).__init__()

    def frames(self):
        LOGGER.info('Starting camera thread')
        BaseCamera.last_occ_uploaded = datetime.now() + timedelta(minutes=1)
        with picamera.PiCamera() as camera:
            LOGGER.debug('Warming up camera')
            time.sleep(2)

            camera.vflip = self.vflip
            camera.hflip = self.hflip
            camera.resolution = tuple(self.resolution)
            camera.framerate = self.fps
            avg = None

            raw_capture = PiRGBArray(camera, size=tuple(self.resolution))
            for f in camera.capture_continuous(raw_capture, 'bgr',
                                               use_video_port=True):

                timestamp = datetime.now()
                # # return current frame
                frame = f.array

                frame = imutils.resize(frame, width=self.frame_width)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, self.ksize, 0)

                if avg is None:
                    LOGGER.info("Starting background model...")
                    avg = gray.copy().astype("float")
                    raw_capture.truncate(0)
                    continue

                cv2.accumulateWeighted(gray, avg, self.alpha)

                response = self.process_frame(frame, gray, avg, timestamp)
                self.process_response(response)
                gray = cv2.cvtColor(response['frame'], cv2.COLOR_BGR2GRAY)
                top = np.concatenate((gray, avg), axis=1)
                bottom = np.concatenate((response['frameDelta'],
                                         response['thresh']), axis=1)
                double = np.concatenate((top, bottom), axis=0)
                ret, jpeg = cv2.imencode('.jpg', double)

                # reset stream for next frame
                raw_capture.truncate(0)

                yield jpeg.tobytes()

    def process_frame(self, frame, gray, avg, timestamp):
        """Process the latest image

        Args:
            frame (numpy.ndarray): Original frame
            gray (numpy.ndarray): Grayscale, blurred frame
            avg (numpy.ndarray): Running average of the images
            timestamp (datetime.datetime): timestmap from when the frame was
                fetched

        Returns:
            dict: Processed frame and occupied status
        """

        occupied = False
        # keep a grayscale copy of orig frame for saving image series
        frame_orig = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

        # threshold the delta image, dilate the thresholded image to fill
        # in holes, then find contours on thresholded image
        thresh = cv2.threshold(frameDelta, self.delta_thresh, 255,
                               cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=self.dilate_iterations)
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[1]

        # loop over the contours
        for c in cnts:
            # if the contour is too small, ignore it
            if cv2.contourArea(c) < self.min_area:
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frameDelta, (x, y), (x + w, y + h),
                              (255, 255, 0), 2)
                continue

            # compute the bounding box for the contour, draw it on the
            # frame, and update the text
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(frameDelta, (x, y), (x + w, y + h), (255, 255, 0), 2)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 2)
            occupied = True

        # draw the text and timestamp on the frame
        ts = timestamp.strftime("%Y-%m-%d-%H:%M:%S")
        text = ('occupied' if occupied else 'unoccupied')
        cv2.putText(frame, "Classification: {}".format(text), (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, ts, (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
        response = {
            'frame': frame,
            'frameDelta': frameDelta,
            'thresh': thresh,
            'ts': timestamp,
            'occupied': occupied
        }
        self.store_frame(frame_orig, occupied, timestamp)
        return response

    def store_frame(self, frame, occupied, timestamp):
        """Save the frame in the frames collector. Store the last X frames
        as specified by frame_store_cnt. This image series is kept to tune
        the model/motion settings.

        Args:
            frame (numpy.ndarray): Original grayscale frame
            occupied (bool): Occupied indicator
            timestamp (datetime.datetime): Timestamp of last image
        """
        frame_dict = {
            'frame': frame,
            'occupied': (1 if occupied else 0),
            'ts': timestamp
        }
        BaseCamera.frames_hist.append(frame_dict)

        if len(BaseCamera.frames_hist) > self.frame_store_cnt:
            BaseCamera.frames_hist.pop(0)
        return

    def process_response(self, response):
        """Process the results from the last frame processing

        Args:
            response (dict): Response from the last frame processing
        """
        occupied = response['occupied']
        frame = response['frame']
        timestamp = response['ts']

        # Build filepath
        text = ('occupied' if occupied else 'unoccupied')
        ts = response['ts'].strftime("%Y-%m-%d_%H:%M:%S.%f")
        filename = '{}_{}.jpg'.format(text, ts)
        filepath = os.path.join(IMG_DIR, filename)
        if occupied:
            LOGGER.debug('Room is occupied!')
            # check to see if enough time has passed between uploads
            future_check = timestamp > BaseCamera.last_occ_uploaded
            elapsed = (timestamp - BaseCamera.last_occ_uploaded).seconds
            if elapsed >= self.occ_min_upload_seconds and future_check:
                LOGGER.debug('%s secs have elasped since last motion. %s '
                             'occ_min_upload_seconds has passed, incrementing '
                             'motion counter', elapsed,
                             self.occ_min_upload_seconds)
                BaseCamera.motion_counter += 1

                # check to see if the number of frames with consistent
                # motion is high enough
                if BaseCamera.motion_counter >= self.min_motion_frames:
                    LOGGER.debug('%s consecutive motion frames detected',
                                 self.min_motion_frames)
                    # update the last uploaded timestamp and reset the
                    # motion counter
                    BaseCamera.last_occ_uploaded = timestamp
                    BaseCamera.motion_counter = 0

                    if utils.redis_get('save_images'):
                        utils.save_image(filepath, frame)
                        write_thread = threading.Thread(
                            target=utils.save_image_series,
                            args=(BaseCamera.frames_hist,),
                            daemon=True
                        )
                        write_thread.start()

                    if utils.redis_get('camera_notifications'):
                        LOGGER.info('Uploading to slack')
                        response = utils.slack_upload(
                            filepath, title=os.path.basename(filepath))
                        utils.slack_post_interactive(response)
        else:
            BaseCamera.motion_counter = 0
            elapsed = (timestamp - BaseCamera.last_unocc_uploaded).seconds
            if elapsed >= self.unocc_min_upload_seconds:
                BaseCamera.last_unocc_uploaded = timestamp
                if utils.redis_get('save_images'):
                    utils.save_image(filepath, frame)
                    write_thread = threading.Thread(
                        target=utils.save_image_series,
                        args=(BaseCamera.frames_hist,),
                        daemon=True
                    )
                    write_thread.start()
        return
