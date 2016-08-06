# -*- coding: utf-8 -*-
from gpiozero import MotionSensor
import datetime
import time
import subprocess
import camera as cam
import twilio_text as tw

time.sleep(10)

#print (datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I:%M%p on %B %d, %Y")

#print ' \n \n \n \n \n \n \n    RUNNING \n \n \n \n \n \n \n'

pir = MotionSensor(4)

i=0
count=0
while True:
    if pir.motion_detected:
        if i>0 and count<=3:
            print '%s : MOTION DETECTED' % datetime.datetime.now()
            subprocess.check_output(['./codesend','4478259 -p 0']) #turn on living room light
            if count=0:
                tw.send_text('intruder detected @'+(datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I:%M%p on %B %d, %Y"),'1')
            cam.snap_x(3,count)
            count+=1
            time.sleep(5)
        else:
            i+=1
            time.sleep(3)


