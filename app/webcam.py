import time


import numpy as np
import imutils
import cv2


from model import MotionModel


model = MotionModel()

cap = cv2.VideoCapture(0)

time.sleep(5)



def compare_frame(frame, avg):
    """Compare the latest frame to the background image

    1) Take the difference between the background average and the latest frame
    2) Threshold it
    3) Dilute it
    4) Find contours and return metadata about them (area and coordinates)

    Args:
        frame (numpy.ndarray): Blurred, grayscale frame
        avg (numpy.ndarray): Running average of the images

    Returns:
        tuple: (List of metadata for delta areas, delta frame)
    """


    frame_delta = cv2.absdiff(frame, cv2.convertScaleAbs(avg))

    # threshold the delta image, dilate the thresholded image to fill
    # in holes, then find contours on thresholded image
    thresh = cv2.threshold(frame_delta, 5, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)
    contours = contours[1]

    contours_meta = []

    # loop over the contours
    for contour in contours:
        meta = {}
        meta['coords'] = cv2.boundingRect(contour)
        meta['size'] = cv2.contourArea(contour)
        contours_meta.append(meta)
    return contours_meta, thresh


def make_grid(avg, frame, dilated, contour_check, person_prob):
    """Make a grid to show all the different images
    """
    avg_rgb = cv2.cvtColor(cv2.convertScaleAbs(avg), cv2.COLOR_GRAY2RGB)
    cv2.putText(avg_rgb, 'Background Avg', (0, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    dilated_rgb = cv2.cvtColor(dilated, cv2.COLOR_GRAY2RGB)
    cv2.putText(dilated_rgb, 'Dilated & Thresholded Difference', (0, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)


    if contour_check:
        text = "Motion detected!"
    else:
        text = "Difference from background image is too small."
    with_classification = np.zeros((frame.shape[0], frame.shape[1], 3), np.uint8)
    cv2.putText(with_classification, text, (0, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    grid_top = np.concatenate((frame, avg_rgb), axis=1)
    grid_bottom = np.concatenate((dilated_rgb, with_classification), axis=1)
    grid = np.concatenate((grid_top, grid_bottom), axis=0)
    return grid

avg = None

while(True):
    ret, frame = cap.read()

    frame = imutils.resize(frame, width=500)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_blur = cv2.GaussianBlur(gray, (21, 21), 0)

    if avg is None:
        print("Starting background model...")
        avg = gray_blur.copy().astype("float")
        continue

    # toggle alpha to how quickly the background average is updated
    # higher alpha = quicker updates to the background image
    cv2.accumulateWeighted(gray_blur, avg, 0.075)

    # difference between blurred frame and background avg
    delta = cv2.absdiff(gray_blur, cv2.convertScaleAbs(avg))

    # thresholded difference
    thresholded = cv2.threshold(delta, 5, 255, cv2.THRESH_BINARY)[1]

    # dilated difference (close the gaps)
    dilated = cv2.dilate(thresholded.copy(), None, iterations=2)

    image, contours, hierarchy = cv2.findContours(
        dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    contours_meta, _ = compare_frame(gray_blur, avg)
    contour_check = model.check_contours(contours_meta)
    person_prob = 0

    # Only run the model if there is a significant difference between the 
    # current frame and background frame
    if contour_check:
        person_prob = model.get_person_prob(frame)

    grid = make_grid(avg, frame, dilated, contour_check, person_prob)

    cv2.imshow('all', grid)


    k = cv2.waitKey(1) & 0xff
    if k == ord('q'):
        break


cap.release()
cv2.destroyAllWindows()