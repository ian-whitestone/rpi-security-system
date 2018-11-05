# Setup

## Raspberry Pi Setup & OpenCV Installation
Checkout out my [rpi-setup](https://github.com/ian-whitestone/rpi-setup) repo for details on how I configured my raspberry pi.

In particular, look at the [camera](https://github.com/ian-whitestone/rpi-setup#camera-tings) section to see installation instructions for `OpenCV 3.4.3`, the raspberry pi camera, and Pimoroni's pantilthat.


## Python Dependencies

See `requirements.txt` for the python dependencies:

`pip install -r requirements.txt`

## Port Forwarding

You will need to open up some ports on your router in order to route slack requests, or requests for other pages webpages on your pi, to the local IP address of your pi. Every router will be different, but here is my setup:

<img src="imgs/port_forwarding.png">

This allows any devices on my local network to SSH into the raspberry pi. It also opens up two ports on my router, `8088` and `8080`, and forwards traffic to the corresponding ports running on my raspberry pi.

## Slack

Follow [Slack's great documentation](https://api.slack.com/slack-apps) for how to build an app.

Once built, manage/find your app at `https://api.slack.com/apps`.

I added a bunch of slash commands:

<img src="imgs/slash_commands.png">

Here's one example of a slash command setup:

<img src="imgs/slash_command_example.png">

I also added an interactive component to allow for image tagging. You just need to specify the request URL for this, i.e. `http://<your_ip_address>:8080/interactive`

## Redis

Followed instructions from this [blog post](http://mjavery.blogspot.com/2016/05/setting-up-redis-on-raspberry-pi.html).

**Note:**
this line: `sudo cp utils/redis_init_script /etc/init.d/redis_6379`
should be: `sudo cp utils/redis_init_script /etc/init.d/redis`

As pointed out by someone in the comments.

## Glances

**Config File**

`/home/pi/.config/glances/glances.conf`

```
[amp_Flask-App]
enable=true
regex=.*gunicorn.*
refresh=3
countmin=2
countmax=3

[amp_Security-System]
enable=true
regex=.*security_system.*
refresh=3
countmin=1
countmax=1

[amp_Who-Is-Home]
enable=true
regex=.*who_is_home.*
refresh=3
countmin=1
countmax=1

[amp_S3-Upload]
enable=true
regex=.*s3_upload.*
refresh=3
countmin=1
countmax=1

[amp_Redis]
enable=true
regex=.*redis-server.*
refresh=3
countmin=1
countmax=1

[amp_Raspi-Temperature]
enable=true
regex=.*
refresh=3
command=vcgencmd measure_temp
countmin=1
```

Here I have some specific processes/things I am monitoring:

- Flask app python process
- A few other python processes
- Redis Server
- Raspberry Pi Temperature (along with total number of running processes)

**Setting Up a Password**

```
>>> glances -w -p 52962 --disable-plugin docker --password
Define the Glances webserver password (glances username):
Password (confirm):
Do you want to save the password? [Yes/No]: yes
Glances Web User Interface started on http://0.0.0.0:52962/
```

**Running Glances Webserver**

`glances -w -p 52962 --disable-plugin docker --password`

Login with username `glances` and the password you set...

**Monitoring Glances Log File**

`tail -f /tmp/glances-pi.log`

**References**
- https://glances.readthedocs.io/en/stable/index.html
- https://www.maketecheasier.com/glances-monitor-system-ubuntu/

## Credentials

### Slack
`app/config/private.yml`

```yaml
ian_uid: XXXXX # id of the user I allow to make slack requests
alerts_channel: XXXX # channel ID (named alerts), where messages are posted to

rpi_cam_app:
  bot_token: xoxb-XXXXX-XXX # get this from https://api.slack.com/apps/<your_app_id>/oauth? 
  verification_token: XXXXXX # get this from app homepage: https://api.slack.com/apps/<your_app_id>
```

### AWS

I created an S3 bucket called `rpi-security-system`. I also created a new IAM user, with a limited set of permissions. I defined the user's permissions by attaching this policy to it:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "RestrictedS3Access",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::rpi-security-system",
                "arn:aws:s3:::rpi-security-system/*"
            ]
        }
    ]
}
```

If you have installed the `awscli` package, and retrieved your IAM user's credentials from the console, you can run the following:

```bash
>>> aws configure
AWS Access Key ID [None]: AKIAXXXX
AWS Secret Access Key [None]: XXXXXXXXXX
Default region name [None]:
Default output format [None]:
```

You can inspect the AWS config files to make sure everything looks okay:

```bash
cat ~/.aws/config
cat ~/.aws/credentials
```

You can test out access to the bucket by running the following:

```bash
>>> touch test.txt
>>>  s3://rpi-security-system/ --sse
upload: ./test.txt to s3://rpi-security-system/test.txt
```

**Note:** I have encryption required in my bucket policy, hence the `--sse`. This is not required.

```json
{
    "Version": "2012-10-17",
    "Id": "PutObjPolicy",
    "Statement": [
        {
            "Sid": "DenyIncorrectEncryptionHeader",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::rpi-security-system/*",
            "Condition": {
                "StringNotEquals": {
                    "s3:x-amz-server-side-encryption": "AES256"
                }
            }
        },
        {
            "Sid": "DenyUnEncryptedObjectUploads",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::rpi-security-system/*",
            "Condition": {
                "Null": {
                    "s3:x-amz-server-side-encryption": "true"
                }
            }
        }
    ]
}
```
