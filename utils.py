import configparser
import os
import poplib
from email import parser
from geopy.distance import vincenty
from pyicloud import PyiCloudService
from twilio.rest import TwilioRestClient
import csv
import slacker
from slacker import Slacker
import datetime
import time
import glob

def ConfigSectionMap(section):
    Config = configparser.ConfigParser()
    dir_path=os.path.dirname(os.path.realpath(__file__))
    config_path=dir_path.split('DoorSensor')[0]+'/config.ini'
    Config.read(config_path)

    config_ops = {}
    options = Config.options(section)
    for option in options:
        try:
            config_ops[option] = Config.get(section, option)
            if config_ops[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            config_ops[option] = None
    return config_ops

def write_to_csv(data):
    dir_path=os.path.dirname(os.path.realpath(__file__))
    with open(dir_path+'/data/'+str((datetime.datetime.now()-datetime.timedelta(hours=4)).strftime("%I%M%p%d%m%Y"))+'.csv','w') as out:
        csv_out=csv.writer(out)
        csv_out.writerow(['time','time_stamp','motion'])
        for row in data:
            csv_out.writerow(row)
    return

def create_bot():
    config_ops=ConfigSectionMap("slack")
    bot=Slacker(config_ops['token'])
    return bot

def upload_vid(bot,channel="#videos"):
    main_dir=os.getcwd()
    allFiles = glob.glob(main_dir+ "/camera" + "/*.mp4")
    for filename in allFiles:
        response=bot.files.upload(filename,channels=channel)
        if response.body['ok']:
            os.remove(filename) ##delete after updating
            os.remove(filename.split(".mp4")[0]+".h264") ##delete h264 version
        else:
            print ("video not uploaded due to: %s") % response.body['error']
    return

def post_message(bot,channel,message):
    bot.chat.post_message(channel, message,username='iansrpi',icon_emoji=':robot_face:')
    return

def get_messages(bot,channel): #channel ops: general or status
    config_ops=ConfigSectionMap("slack")

    #get channels codes
    channels_response=bot.channels.list()
    channel_dict={chan['name']:chan['id'] for chan in channels_response.body['channels']}
    #get channel id
    channel_id=channel_dict[channel]

    response=bot.channels.history(channel_id)
    messages=response.body['messages']

    bot_messages=[]
    user_messages=[]
    for message in messages:
        if 'user' in message.keys() and 'subtype' not in message.keys() and message['type']=='message':
            if message['user']==config_ops['user']:
                user_messages.append({'message':message['text'],'time':message['ts']})
        elif 'subtype' in message.keys() and 'bot_id' in message.keys() and message['type']=='message':
            if message['bot_id']==config_ops['bot'] and message['subtype']=='bot_message':
                bot_messages.append({'message':message['text'],'time':message['ts']})
    return user_messages,bot_messages

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
    f=open(dir_path.split('DoorSensor')[0]+'/sky.txt','rb+')
    sky=f.read().split()

    api = PyiCloudService(sky[0], sky[1])
    coords=api.devices[sky[2]].location()
    lat=coords['latitude']
    lon=coords['longitude']
    me = (round(lat,7), round(lon,7))
    home=(float(loc[0]),float(loc[1]))
    print(vincenty(home, me).meters)

    return

def send_text(message,media):
    account_sid=contents[0]
    auth_token=contents[1]
    client = TwilioRestClient(account_sid, auth_token)
    # this is the URL to an image file we're going to send in the MMS
    media = "http://www.mattmakai.com/source/static/img/work/fsp-logo.png"

    client.messages.create(to="+14387932891", from_="+14387932891",
                              body=message)#, media_url=media)
    return
