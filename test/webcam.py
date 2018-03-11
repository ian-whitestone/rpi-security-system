import imutils
import numpy as np
import cv2
import time

cap = cv2.VideoCapture(0)

time.sleep(1)

# fgbg = cv2.createBackgroundSubtractorMOG()
# fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=False, history=100)



avg = None

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
    cv2.imwrite('double.jpg', double)

    # cv2.imshow('frame', frame)
    # cv2.imshow('gray', gray)
    # cv2.imshow('frame', double)
    k = cv2.waitKey(1) & 0xff
    if k == ord('q'):
        break


cap.release()
cv2.destroyAllWindows()