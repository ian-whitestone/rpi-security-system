# -*- coding: utf-8 -*-
from gpiozero import MotionSensor
import datetime
import time
import subprocess


import os
from picamera import PiCamera


camera=PiCamera()
camera.resolution=(1920,1080)
camera.exposure_mode = 'sports'
camera.framerate=60
##camera.rotation=180
camera.brightness=50

##time.sleep(1)
##camera.start_preview()
####try:
####    camera.start_recording('./camera/video1.h264')
####    camera.wait_recording(5)
##time.sleep(5)
####    camera.stop_recording()
####except:
####    pass
##camera.stop_preview()
####

time.sleep(2)
for i in range(1,9):
    camera.capture('./camera/image%s_%s.jpg'%(1,i))
    time.sleep(0.5)


##camera.start_preview()
##camera.exposure_mode = 'sports'
##time.sleep(5)
##camera.capture('/home/pi/Desktop/beach.jpg')
##camera.stop_preview()

