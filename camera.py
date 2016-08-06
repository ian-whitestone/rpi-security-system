from picamera import PiCamera
from time import sleep



def snap_x(x,count):
    camera=PiCamera()
    camera.rotation=180
    #camera.start_preview()
    for i in range(x):
        sleep(2)
        camera.capture('/home/pi/Documents/Python Projects/Door Sensor/image%s_%s.jpg'%(count,i))
    #camera.stop_preview()
    return


