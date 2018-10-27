import imutils
import numpy as np
import cv2
import time
from datetime import datetime
import threading

cap = cv2.VideoCapture(0)

time.sleep(1)

# fgbg = cv2.createBackgroundSubtractorMOG()
# fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=False, history=100)



avg = None
frames = []

while(1):
    ret, frame = cap.read()

    frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if avg is None:
        print("Starting background model...")
        avg = gray.copy().astype("float")
        continue

    cv2.accumulateWeighted(gray, avg, 0.1)

    # fgmask = fgbg.apply(frame)
    double = np.concatenate((gray, avg), axis=0)

    # cv2.imshow('frame', frame)
    # cv2.imshow('gray', gray)
    cv2.imshow('frame', double)
    k = cv2.waitKey(1) & 0xff
    if k == ord('q'):
        break

    frames.append((datetime.now(), cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)))
    if len(frames) > 300:
        break
        frames.pop(0)

start = (datetime.now())

def write_frames():
    write_time = 0
    for frame in frames:
        write_start = datetime.now()
        cv2.imwrite('test/imgs/{}.jpg'.format(frame[0].strftime('%Y-%m-%d_%H:%M:%S.%f'))
                    , frame[1])
        write_end = datetime.now()
        write_time += (write_end - write_start).total_seconds()
    print ('Total write time: %s. %s' % (write_time, write_end.strftime('%M:%S.%f')))

th = threading.Thread(target=write_frames)
th.start()
end = (datetime.now())

print ('Total time: %s. %s' % ((end - start).total_seconds(), end.strftime('%M:%S.%f')))
cap.release()
cv2.destroyAllWindows()