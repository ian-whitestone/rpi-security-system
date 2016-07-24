# -*- coding: utf-8 -*-
from gpiozero import MotionSensor
import datetime
import time

#time.sleep(120)

print ' \n \n \n \n \n \n \n    RUNNING \n \n \n \n \n \n \n'

pir = MotionSensor(4)

while True:
    if pir.motion_detected:
        print '%s : MOTION DETECTED' % datetime.datetime.now()
        

