# -*- coding: utf-8 -*-
from gpiozero import MotionSensor
import datetime
import time
import subprocess
import os
import utils

def get_status(bot):
    user_messages,bot_messages=utils.get_messages(bot,'status')
    return user_messages[0]['message']

def main():
    timeout=utils.ConfigSectionMap('timeout') #timeout['loop'] is in minutes
    timeout=int(timeout['loop'])*60
    pir = MotionSensor(4)
    bot=utils.create_bot()

    curr_status=get_status(bot)

    if curr_status=='shutdown':
        utils.post_message(bot,'status','process shutdown')
        return
    else:
        curr_time=(datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I:%M%p on %B %d, %Y")
        utils.post_message(bot,'status','process initiated with status: %s @ %s' % (curr_status,curr_time))

    while True:
        status=get_status(bot)

        ##4 statuses: on,off,reg,shutdown. on/off overide reg. reg enables based on location
        if status!=curr_status: #detect status changes
            prev_status=curr_status
            curr_status=status
            if curr_status=='shutdown':
                utils.post_message(bot,'status','process shutdown')
                break
            else:
                utils.post_message(bot,'status','system has been switched from '+prev_status+ ' to '+curr_status)
            continue

        if curr_status=='on':
            search(curr_status,pir,bot)
            continue

        time.sleep(timeout)#wait X min..then check for new statuses
    return


def search(mode,pir,bot):
    dir_path=os.path.dirname(os.path.realpath(__file__))
    timeout=utils.ConfigSectionMap('timeout') #timeout['loop'] is in minutes
    nomotion_timeout=2*int(timeout['nomotion'])
    timeout=int(timeout['loop'])*60

    motion_count=0
    nomotion_count=0
    motion_data=[]
    timeout = time.time() + timeout   # X minutes from now
    while True:
        if pir.motion_detected:
            motion_data.append((str((datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I%M%p%d%m%Y")),time.time(),1))
            nomotion_count=0 ##reset
            if motion_count==0: ##first time motion is detected
                curr_time=(datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I%M%p%d%m%Y")
                motion_detected(curr_time,bot)
                motion_count+=1
            else:
                motion_count+=1
        else:
            motion_data.append((str((datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I%M%p%d%m%Y")),time.time(),0))
            nomotion_count+=1

	    if motion_count>0 and nomotion_count>nomotion_timeout: #motion was previously sensed and has been gone for X seconds..
                motion_count=0
                # intruder_gone(curr_time,bot)

        if time.time()>timeout: ##check for status changes
            status=get_status(bot)
            if status==mode: #if status has not changed
                timeout=time.time()+timeout ##reset timeout and continue looping
            elif status in ['off','shutdown']:
                utils.write_to_csv(motion_data)
                break
        time.sleep(0.5)
    return


def motion_detected(curr_time,bot):
    dir_path=os.path.dirname(os.path.realpath(__file__))
    print '%s : MOTION DETECTED' % datetime.datetime.now()
    #turn on living room light
    #subprocess.check_output([dir_path+'/codesend','4478259 -p 0'])
    ##send text
    utils.post_message(bot,'alerts','intruder detected @ '+(datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I:%M%p on %B %d, %Y"))
    ###start recording (max 1 hour...), kill once motion has stopped.
    # subprocess.Popen("raspivid -fps 30 -hf -t 360000 -w 640 -h 480 -o " + curr_time + ".h264", shell=True)
    return

def intruder_gone(curr_time,bot):
    dir_path=os.path.dirname(os.path.realpath(__file__))
    ##kill video
    # subprocess.call(["pkill raspivid"], shell=True)
    ##conver file
    # subprocess.Popen("MP4Box -fps 30 -add " + curr_time + ".h264 " + curr_time + ".mp4", shell=True)
     #turn off living room light
 #   subprocess.check_output([dir_path+'/codesend','4478268 -p 0'])
    #send text including dropbox/googledrive link??
 #   tw.send_text('intruder footage @ '+'dummy_link','1')
    return


print "\n Now running on: \n"
print (datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I%M%p%d%m%Y")
main()


##TO ADD
##1) only turn on/off light if its a certain time of the day
##2) set up dropbox uploader & integrate dropbox with slack
##3) try requiing multiple motion detection events in order to trigger text?? (i.e. 5 trips in 30 seconds??)
##5) use phone location to see disable/enable alarm
##7) turn this whole thing into a class
##9) build in something for dropped internet connections...(if you ever see the error message)
##10) add a special email to start up system (ie start python script)...need a bash script running to check emails say every 10 min?
##11) be able to ping system for current status (i.e. is it running?)
