
## Resources

1) [Open CV Installation](https://www.pyimagesearch.com/2016/04/18/install-guide-raspberry-pi-3-raspbian-jessie-opencv-3/)

2) [General camera usage](https://www.pyimagesearch.com/2015/03/30/accessing-the-raspberry-pi-camera-with-opencv-and-python/)

3) [Intro to Motion Detection](https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/)
- Note - uses webcam instead of picam
- see [here](https://www.pyimagesearch.com/2016/01/04/unifying-picamera-and-cv2-videocapture-into-a-single-class-with-opencv/) to switch between the two

4) [Motion detection system](https://www.pyimagesearch.com/2015/06/01/home-surveillance-and-motion-detection-with-the-raspberry-pi-python-and-opencv/)
-  Uses picam!


## TODO

Look into increasing FPS with [threading](https://www.pyimagesearch.com/2015/12/28/increasing-raspberry-pi-fps-with-python-and-opencv/)


## Slack


In the alerts channel, general message looks like:

```python
[{'team': 'XXXXXX', 'channel': 'XXXXX', 'source_team': 'XXXXXX', 'ts': '1510520180.000086', 'user': 'XXXXX', 'type': 'message', 'text': 'good afternooon. this is a test.'}]

```


```python
[{'channel': 'XXXXX', 'team': 'XXXXXX', 'user': 'XXXXXX', 'text': '<@U2CQKA1GU> im talking to you :robot_face:', 'type': 'message', 'source_team': 'XXXXXX', 'ts': '1510520298.000009'}]

[{'channel': 'XXXXX', 'launchUri': 'slack://channel?id=XXXXX&message=1510520298000009&team=XXXXXX', 'title': "Ian's Rpi", 'ssbFilename': 'knock_brush.mp3', 'msg': '1510520298.000009', 'subtitle': '#alerts', 'is_shared': False, 'type': 'desktop_notification', 'content': 'ian-whitestone: @iansrpi im talking to you :robot_face:', 'event_ts': '1510520298.000036', 'imageUri': None, 'avatarImage': 'https://secure.gravatar.com/avatar/dc8f7cbc903f01d20f06ec921b5aa9eb.jpg?s=192&d=https%3A%2F%2Fa.slack-edge.com%2F7fa9%2Fimg%2Favatars%2Fava_0016-192.png'}]

```
