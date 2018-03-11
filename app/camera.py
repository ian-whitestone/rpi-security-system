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

class CameraEvent(object):
    """An Event-like class that signals all active clients when a new frame is
    available.
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

    def __init__(self):
        """Start the background camera thread if it isn't running yet."""
        LOGGER.info("Initializing base camera class")
        if BaseCamera.thread is None:
            BaseCamera.last_access = time.time()

            # start background frame thread
            BaseCamera.thread = threading.Thread(target=self._thread)
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
                    time.sleep(0)

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
        self.save_images = CONF['save_images']
        self.vflip = CONF['vflip']
        self.hflip = CONF['hflip']
        super(Camera, self).__init__()

    def frames(self):
        LOGGER.info('Starting camera thread')
        with picamera.PiCamera() as camera:
            # let camera warm up
            time.sleep(2)
            camera.vflip = self.vflip
            camera.hflip = self.hflip
            camera.resolution = tuple(self.resolution)
            camera.framerate = self.fps
            avg = None

            raw_capture = PiRGBArray(camera, size=tuple(self.resolution))
            for f in camera.capture_continuous(raw_capture, 'bgr',
                                               use_video_port=True):
                # # return current frame
                frame = f.array

                frame = imutils.resize(frame, width=self.frame_width)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

                if avg is None:
                    LOGGER.info("Starting background model...")
                    avg = gray.copy().astype("float")
                    raw_capture.truncate(0)
                    continue

                cv2.accumulateWeighted(gray, avg, 0.1)

                frame, frameDelta, thresh = self.process_frame(frame, gray, avg)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                top = np.concatenate((gray, avg, frameDelta), axis=1)
                bottom = np.concatenate((gray, avg, thresh), axis=1)
                double = np.concatenate((top, bottom), axis=0)
                ret, jpeg = cv2.imencode('.jpg', double)
                yield jpeg.tobytes()

                # reset stream for next frame
                raw_capture.truncate(0)

    def process_frame(self, frame, gray, avg):
        occupied = False
        timestamp = datetime.now()
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

        # threshold the delta image, dilate the thresholded image to fill
        # in holes, then find contours on thresholded image
        thresh = cv2.threshold(frameDelta, self.delta_thresh, 255,
            cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[1]

        # loop over the contours
        for c in cnts:
            # if the contour is too small, ignore it
            if cv2.contourArea(c) < self.min_area:
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frameDelta, (x, y), (x + w, y + h), (255, 255, 0), 2)
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
        return frame, frameDelta, thresh
