# we import the Twilio client from the dependency we just installed
from twilio.rest import TwilioRestClient
import os


dir_path=os.path.dirname(os.path.realpath(__file__))
f=open(dir_path.split('DoorSensor')[0]+'/twilio_auth.txt','rb+')
contents=f.read().split()

# the following line needs your Twilio Account SID and Auth Token
account_sid=contents[0]
auth_token=contents[1]
client = TwilioRestClient(account_sid, auth_token)

# this is the URL to an image file we're going to send in the MMS
media = "http://www.mattmakai.com/source/static/img/work/fsp-logo.png"

def send_text(message,media):
    client.messages.create(to="+15879985603", from_="+14387932891", 
                              body=message)#, media_url=media)
    return

#send_text('hello world','str')

##use git python to push images to git repo
###https://github.com/gitpython-developers/GitPython
