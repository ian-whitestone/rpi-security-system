
## Resources

1) [Open CV Installation](https://www.pyimagesearch.com/2016/04/18/install-guide-raspberry-pi-3-raspbian-jessie-opencv-3/)

2) [General camera usage](https://www.pyimagesearch.com/2015/03/30/accessing-the-raspberry-pi-camera-with-opencv-and-python/)

3) [Intro to Motion Detection](https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/)
- Note - uses webcam instead of picam
- see [here](https://www.pyimagesearch.com/2016/01/04/unifying-picamera-and-cv2-videocapture-into-a-single-class-with-opencv/) to switch between the two

4) [Motion detection system](https://www.pyimagesearch.com/2015/06/01/home-surveillance-and-motion-detection-with-the-raspberry-pi-python-and-opencv/)
-  Uses picam!

5) Video Streaming
http://www.instructables.com/id/Raspberry-Pi-Video-Streaming/
https://www.linux-projects.org/uv4l/installation/

`$ pkill uv4l`
`$ uv4l -nopreview --auto-video_nr --driver raspicam --encoding mjpeg --vflip yes --hflip yes --width 640 --height 480 --framerate 20 --server-option '--port=9090' --server-option '--max-queued-connections=30' --server-option '--max-streams=25' --server-option '--max-threads=29' --server-option '--user-password=11' --server-option '--admin-password=11'`


## TODO

* Look into increasing FPS with [threading](https://www.pyimagesearch.com/2015/12/28/increasing-raspberry-pi-fps-with-python-and-opencv/)

* on/off slash commands
* status slash command (return whether running or not)
* picam slack updates
--> initial picture when starting up
--> post & upload picture when motion detected

* picture slash command (return most recent image)


## Slack

1) Using the RTM API
In the alerts channel, general message looks like:

```python
[{'team': 'XXXXXX', 'channel': 'XXXXX', 'source_team': 'XXXXXX', 'ts': '1510520180.000086', 'user': 'XXXXX', 'type': 'message', 'text': 'good afternooon. this is a test.'}]

```


```python
[{'channel': 'XXXXX', 'team': 'XXXXXX', 'user': 'XXXXXX', 'text': '<@U2CQKA1GU> im talking to you :robot_face:', 'type': 'message', 'source_team': 'XXXXXX', 'ts': '1510520298.000009'}]

[{'channel': 'XXXXX', 'launchUri': 'slack://channel?id=XXXXX&message=1510520298000009&team=XXXXXX', 'title': "Ian's Rpi", 'ssbFilename': 'knock_brush.mp3', 'msg': '1510520298.000009', 'subtitle': '#alerts', 'is_shared': False, 'type': 'desktop_notification', 'content': 'ian-whitestone: @iansrpi im talking to you :robot_face:', 'event_ts': '1510520298.000036', 'imageUri': None, 'avatarImage': 'https://secure.gravatar.com/avatar/dc8f7cbc903f01d20f06ec921b5aa9eb.jpg?s=192&d=https%3A%2F%2Fa.slack-edge.com%2F7fa9%2Fimg%2Favatars%2Fava_0016-192.png'}]

```


## MongoDB

General Notes:
* Don't need to explicitly create databases or collections (i.e. tables). I.e. running the snippet below for the first time will automatically create the "test" database (if it doesn't already exist, otherwise it would just connect to it). Same thing applies for the "test_table" collection (Note - I'm still getting used to calling them collections..)

```python
mongo_url = "mongodb://localhost:27017"
client = MongoClient(mongo_url)
db = client.test

for x in range(1,10):
    doc = {'doc_id': x, 'image': None}
    db.test_table.insert_one(doc)
```

* Querying
```python
## return everything
cursor = db.test_table.find({})

for doc in cursor:
    print (doc)

## query by doc id
cursor = db.test_table.find({'doc_id':1})

for doc in cursor:
    print (doc)
``

* Storing Images with GridFS

```python
from pymongo import MongoClient
from gridfs import GridFS

mongo_url = "mongodb://localhost:27017"
client = MongoClient(mongo_url)

db =client.gridfs_example
fs = GridFS(db)

fpath = 'path/to/my/image'
id = fs.put(open(fpath, 'rb'), filename='ians_test_image', other=999)

# Get object by ID
obj = fs.get(id)

# Get object by other metadata
obj = fs.find_one({'filename':'ians_test_image'})

# read contents
contents = obj.read()
# Note: calling obj.read() a second time returns nothing for some reason..

# read other properties
filename = obj.filename
other = obj.other

# write the byte contents to an image file locally
with open('./myimage.tif', 'wb') as f:
    f.write(contents)

client.close()
```

## Setup Notes

### Slack
- Slack bot
- Slack-cleaner setup with required roles/permissions

### Router
- Port forwarding (take screenshot)
- DHCP lease times



## Wiring Notes

GPIO4 --> temp sensor

GPIO17 --> RF transmitter

Turn kitchen light on:
(cv) pi@raspberrypi:~/rpi-security-system/archive $ ./codesend 4478403 -p 0
Sending Code: 4478403. PIN: 0. Pulse Length: 189

Turn kitchen light off:
(cv) pi@raspberrypi:~/rpi-security-system/archive $ ./codesend 4478412 -p 0
Sending Code: 4478412. PIN: 0. Pulse Length: 189



Light sensor Notes
- GPIO27
- http://www.uugear.com/portfolio/using-light-sensor-module-with-raspberry-pi/
- *When the ambient light intensity is lower than the predefined threshold, the output signal is high. When the light intensity reaches or exceeds the threshold, the signal output is low.*
    + i.e. no light --> output is 1

```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.IN)
GPIO.input(27)
```


LED Setup

- 390 Ohm Resistor
    - Used this calculator: http://ledcalc.com/
    - supply: 5V, drop: 2-2.2V , current: 8mA (these were on the LEd package)
- Longer leg of LED is connected to power supply (GPIO)
- Shorter leg is connectedt to ground

```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)
# turn it on
GPIO.output(26, GPIO.HIGH)
# turn it off
GPIO.output(26, GPIO.LOW)
```

PIR Motion Sensor

```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.IN)
import time
while True:
    GPIO.input(21)
    time.sleep(0.1)
```

Checking CPU Throttling:

https://www.raspberrypi.org/forums/viewtopic.php?f=28&t=152549

```
pi@raspberrypi:~ $ vcgencmd get_throttled
throttled=0x50000
```
- I believe this outputs means: currently throttled due to low voltage since my temp is < 50 degC
- Ref: https://github.com/raspberrypi/firmware/issues/615
-