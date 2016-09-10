# -*- coding: utf-8 -*-
from gpiozero import MotionSensor
import datetime
import time
import subprocess
import twilio_text as tw
import os
import poplib
from email import parser
from geopy.distance import vincenty
from pyicloud import PyiCloudService
import csv



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


def search(mode):
    dir_path=os.path.dirname(os.path.realpath(__file__))
    pir = MotionSensor(4)

    i=0
    motion_count=0
    nomotion_count=0
    motion_data=[]
    timeout = time.time() + 60*5   # 5 minutes from now
    while True:
        if pir.motion_detected:
            motion_data.append((time.time(),1))
            nomotion_count=0 ##reset
            if motion_count==0: ##first time motion is detected
                curr_time=(datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I%M%p%d%m%Y")
                motion_detected(curr_time,dir_path)
                motion_count+=1
                time.sleep(1)
            else:
                motion_count+=1
        else:
            motion_data.append((time.time(),0))
            nomotion_count+=1
            print nomotion_count
	    if motion_count>0 and nomotion_count>20: #motion was previously sensed and has been gone for 10 seconds..
                motion_count=0
                intruder_gone(curr_time,dir_path)
        if time.time()>timeout:
            status=get_emails()
            if status==mode: #if
                timeout=time.time()+60*5 ##reset timeout and continue looping
            elif status in ['off','shutdown']:
                write_to_csv(motion_data)
                break
        time.sleep(0.5)
    return

def write_to_csv(data):
    with open('./data/'+str(time.time())+'.csv','w') as out:
        csv_out=csv.writer(out)
        csv_out.writerow(['time','motion'])
        for row in data:
            csv_out.writerow(row)
    return

def main():
    prev_status='on' #default on
    while True:
        status=get_emails()
        ##3 statuses: on,off,reg. on/off overide reg. reg enables based on location
        if status is not None and status!=prev_status:
            prev_status=status
        if prev_status=='on':
            search(prev_status)
        elif prev_status=='shutdown':
            break
        time.sleep(60) ##600 normally

    return

def get_emails():
    dir_path=os.path.dirname(os.path.realpath(__file__))
    f=open(dir_path.split('DoorSensor')[0]+'/mail_auth.txt','rb+')
    mail_auth=f.read().split()

    pop_conn = poplib.POP3_SSL('pop.gmail.com')
    pop_conn.user('recent:'+mail_auth[0])
    pop_conn.pass_(mail_auth[1])

    #Get messages from server:
    messages = [pop_conn.retr(i) for i in range(1, len(pop_conn.list()[1]) + 1)]
    # Concat message pieces:
    messages = ["\n".join(mssg[1]) for mssg in messages]
    #Parse message into an email object:
    messages = [parser.Parser().parsestr(mssg) for mssg in messages]

    for message in messages:
        print message['subject']
        # print message.keys()

    statuses=[message['subject'] for message in messages if message['subject'] in ['on','off','shutdown']] ##change to regex for things like oN or ON etc.

    if len(statuses)>0:
        pop_conn.quit()
        return statuses[-1]

    pop_conn.quit()
    return None

def location():
    dir_path=os.path.dirname(os.path.realpath(__file__))
    f=open(dir_path.split('DoorSensor')[0]+'/loc.txt','rb+')
    loc=f.read().split()

    # api = PyiCloudService('jappleseed@apple.com', 'password')
    coords=api.devices['RPcOAtJ84SNlCtdMZYmED+kA6NxEv03Qh5afc0M0X16Ygbfn9OtQsOHYVNSUzmWV'].location()
    lat=coords['latitude']
    lon=coords['longitude']
    me = (round(lat,7), round(lon,7))
    home=(float(loc[0]),float(loc[1]))
    print(vincenty(home, me).meters)

    return

main()

##TO ADD
##1) only turn on/off light if its a certain time of the day
##2) schedule the system with pcron
##3) set up dropbox uploader
##4) try requiing multiple motion detection events in order to trigger text?? (i.e. 5 trips in 30 seconds??)
##5) use phone location to see disable/enable alarm
##6) hardcoded enable/disable for overriding location...
##7) turn this whole thing into a class

##pip install pyicloud
##pip install geopy
