"""
Run the background processes for the home security system

1) Detect who is home
2) Upload images to S3
"""
import threading
import time
from app import who_is_home
from app import s3_upload

def my_func():
    while True:
        print ('hello')
        time.sleep(5)

home_thread = threading.Thread(target=who_is_home.loop, args=())
home_thread.daemon = True
home_thread.start()

s3_thread = threading.Thread(target=s3_upload.loop, args=())
s3_thread.daemon = True
s3_thread.start()

while True:
    time.sleep(10000)