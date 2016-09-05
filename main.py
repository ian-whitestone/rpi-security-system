# -*- coding: utf-8 -*-
from gpiozero import MotionSensor
import datetime
import time
import subprocess
import twilio_text as tw
import os


# from picamera import PiCamera
#
# camera=PiCamera()
# camera.resolution=(2592,1944)
# camera.rotation=180
#
# def snap_x(x,count):
#     #camera.start_preview()
#     for i in range(x):
#         time.sleep(2)
#         camera.capture('./camera/image%s_%s.jpg'%(count,i))
#     #camera.stop_preview()
#     camera=None
#     return


def motion_detected(curr_time,dir_path):
    print '%s : MOTION DETECTED' % datetime.datetime.now()
    #turn on living room light
#    subprocess.check_output([dir_path+'/codesend','4478259 -p 0'])
    #send text
#    tw.send_text('intruder detected @'+(datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I:%M%p on %B %d, %Y"),'1')
    ###start recording (max 1 hour...), kill once motion has stopped.
    # subprocess.Popen("raspivid -fps 30 -hf -t 360000 -w 640 -h 480 -o " + curr_time + ".h264", shell=True)
    return

def intruder_gone(curr_time,dir_path):
    ##kill video
    # subprocess.call(["pkill raspivid"], shell=True)
    ##conver file
    # subprocess.Popen("MP4Box -fps 30 -add " + curr_time + ".h264 " + curr_time + ".mp4", shell=True)
     #turn off living room light
 #   subprocess.check_output([dir_path+'/codesend','4478268 -p 0'])
    #send text including dropbox/googledrive link??
 #   tw.send_text('intruder footage @ '+'dummy_link','1')
    return


def main():
    dir_path=os.path.dirname(os.path.realpath(__file__))
    pir = MotionSensor(4)

    i=0
    motion_count=0
    nomotion_count=0

    while True:
        if pir.motion_detected:
            nomotion_count=0 ##reset
            if motion_count==0: ##first time motion is detected
                curr_time=(datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I%M%p%d%m%Y")
                motion_detected(curr_time,dir_path)
                motion_count+=1
                time.sleep(5)
            else:
                motion_count+=1
        else:
            nomotion_count+=1
            print nomotion_count
	    if motion_count>0 and nomotion_count>10: #motion was previously sensed and has been gone for 10 seconds..
                motion_count=0
                intruder_gone(curr_time,dir_path)
        time.sleep(1)
    return


main()









##

