from picamera.array import PiRGBArray
from picamera import PiCamera
import argparse
import warnings
from datetime import datetime
import imutils
import time
import cv2
import os

from .logger import create_logger
from .utils import read_yaml, slack_post, slack_upload

log_file = '/app/logs' + datetime.now().strftime("%Y-%m-%d-%H:%M")
log = create_logger(__name__, log_level='DEBUG', log_filename=log_file)


CONF = read_yaml('app/config.yml')
IMG_PATH = 'app/imgs'

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
		self.warmup_time = CONF["camera_warmup_time"]
		self.save_images = CONF['save_images']
		self._init_camera()

	def _init_camera():
		log.info('Initializing PiCamera')
		self.camera = PiCamera()
		self.camera.resolution = tuple(self.resolution)
		self.camera.framerate = self.fps

	def start_stream():
		self.rawCapture = PiRGBArray(camera, size=tuple(self.resolution))
		log.info('Warming up camera')
		time.sleep(self.warmup_time)

		for f in camera.capture_continuous(self.rawCapture, format="bgr",
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
				log.info("Starting background model...")
				avg = gray.copy().astype("float")
				self.rawCapture.truncate(0)
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
				log.info('Room is occupied!')
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

						slack_post('<PiCam> {0} : Room is occupied'.format(ts))
						if self.save_images:
							fpath = os.path.join(IMG_PATH, text + '_' + ts)
							log.info('Saving occupied image to %s' % fpath)
							cv2.imwrite(fpath, frame)
							log.info('Uploading to slack')
							slack_upload(fpath, title=fpath)
			else:
				motionCounter = 0
				elapsed = (timestamp - lastUnoccUploaded).seconds
				if  elapsed >= self.unocc_min_upload_seconds:
					lastUnoccUploaded = timestamp
					if self.save_images:
						fpath = os.path.join(IMG_PATH, text + '_' + ts)
						log.info('Saving unoccupied image to %s' % fpath)
						cv2.imwrite(fpath, frame)

			# clear the stream in preparation for the next frame
			self.rawCapture.truncate(0)

if __name__ == '__main__':
	picam = PiCam()
	picam.start_stream()
