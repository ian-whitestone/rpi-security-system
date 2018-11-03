cd /home/pi/rpi-security-system
nohup gunicorn -c gunicorn.conf run_flask &
nohup python3 app/who_is_home.py >> app/logs/who_is_home.log 2>&1 &
nohup python3 app/security_system.py >> app/logs/security_system.log &
nohup python3 app/s3_upload.py >> app/logs/s3_upload.log &
nohup glances -w -p 52962 --disable-plugin docker --password &