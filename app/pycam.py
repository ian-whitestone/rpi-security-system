"""
Module with the core pycam process for motion detection.
"""
import logging
import os
import time
from datetime import datetime, timedelta

from picamera.array import PiRGBArray
from picamera import PiCamera
import imutils
import cv2
import utils

LOGGER = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(__file__)
IMG_DIR = os.path.join(CURR_DIR, 'imgs')

utils.pycam_logging(LOGGER)

CONF = utils.read_yaml(os.path.join(CURR_DIR, 'config.yml'))


class PiCam():

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
        self._init_camera()
        self._looper()

    def _init_camera(self):
        LOGGER.info('Initializing PiCamera')
        try:
            self.camera = PiCamera()
            self.camera.resolution = tuple(self.resolution)
            self.camera.framerate = self.fps
            self.camera.vflip = CONF['vflip']
            self.camera.hflip = CONF['hflip']
            self.raw_capture = PiRGBArray(self.camera, size=tuple(self.resolution))
            LOGGER.info('Warming up camera')
            time.sleep(2.5)
        except Exception:
            LOGGER.exception("Unable to initialize camera due to error:")

    def looper():
        """Main camera controller process that monitors the redis camera_status
        variable to see if frames should be processed
        """
        LOGGER.info('Starting looper')
        while True:
            if utils.redis_get('camera_status'):
                self._process_frames
            else:


    def start_stream(self):

        avg = None
        motionCounter = 0

        for f in self.camera.capture_continuous(self.raw_capture, format="bgr",
                                                use_video_port=True):
            # grab the raw NumPy array representing the image and initialize
            # the timestamp and the occupied status to false
            frame = f.array
            timestamp = datetime.now()
            occupied = False

            # resize the frame, convert it to grayscale, and blur it
            frame = imutils.resize(frame, width=self.frame_width)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # if the average frame is None, initialize it
            if avg is None:
                LOGGER.info("Starting background model...")
                avg = gray.copy().astype("float")
                self.raw_capture.truncate(0)
                continue

            # accumulate the weighted average between the current frame and
            # previous frames, then compute the difference between the current
            # frame and running average
            cv2.accumulateWeighted(gray, avg, 0.1)
            frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

            # threshold the delta image, dilate the thresholded image to fill
            # in holes, then find contours on thresholded image
            thresh = cv2.threshold(frameDelta, self.delta_thresh, 255,
                cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if imutils.is_cv2() else cnts[1]

            # loop over the contours
            for c in cnts:
                # if the contour is too small, ignore it
                if cv2.contourArea(c) < self.min_area:
                    continue

                # compute the bounding box for the contour, draw it on the
                # frame, and update the text
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 2)
                occupied = True

            # draw the text and timestamp on the frame
            ts = timestamp.strftime("%Y-%m-%d-%H:%M:%S")
            text = ('Occupied' if occupied else 'Unoccupied')
            cv2.putText(frame, "Room Status: {}".format(text), (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(frame, ts, (10, frame.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

            if occupied:
                LOGGER.debug('Room is occupied!')
                # check to see if enough time has passed between uploads
                elapsed = (timestamp - lastOccUploaded).seconds
                if  elapsed >= self.occ_min_upload_seconds:
                    motionCounter += 1

                    # check to see if the number of frames with consistent
                    # motion is high enough
                    if motionCounter >= self.min_motion_frames:
                        # update the last uploaded timestamp and reset the
                        # motion counter
                        lastOccUploaded = timestamp
                        motionCounter = 0

                        utils.slack_post('<PiCam> {0} : Room is occupied'.format(ts))
                        if self.save_images:
                            fpath = os.path.join(IMG_DIR, text + '_' + ts + '.jpg')
                            LOGGER.info('Saving occupied image to %s' % fpath)
                            cv2.imwrite(fpath, frame)
                            LOGGER.info('Uploading to slack')
                            utils.slack_upload(fpath, title=fpath)
            else:
                motionCounter = 0
                elapsed = (timestamp - lastUnoccUploaded).seconds
                if  elapsed >= self.unocc_min_upload_seconds:
                    lastUnoccUploaded = timestamp
                    if self.save_images:
                        fpath = os.path.join(IMG_DIR, text + '_' + ts + '.jpg')
                        LOGGER.info('Saving unoccupied image to %s' % fpath)
                        cv2.imwrite(fpath, frame)

            # clear the stream in preparation for the next frame
            self.raw_capture.truncate(0)

if __name__ == '__main__':
    picam = PiCam()
    picam.start_stream()
