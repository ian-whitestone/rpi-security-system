"""Model used to classify an image as having been triggered by motion 
"""
import logging
import os

import numpy as np
import cv2

import utils
import config

LOGGER = logging.getLogger(__name__)
CONF = config.load_config()

config.init_logging()

class MotionModel():

    def __init__(self):
        """Initialize the MotionModel class
        """
        self.min_area = CONF['min_area']
        self.model = self.load_model()
        self.person_class = 15 # index of the person class of the pre-trained model

    def load_model(self):
        proto_path = os.path.join(
            config.MODEL_DIR, 'MobileNetSSD_deploy.prototxt.txt')
        model_path = os.path.join(
            config.MODEL_DIR, 'MobileNetSSD_deploy.caffemodel')
        net = cv2.dnn.readNetFromCaffe(proto_path, model_path)
        return net

    def get_person_prob(self, image):
        """Get the probability of a person being present in an image
        
        Args:
            image (numpy.ndarray): Image to classify
        
        Returns:
            float: Probability between 0 and 1 of a person being present
        """
        resized = cv2.resize(image, (300, 300))
        blob = cv2.dnn.blobFromImage(resized, 0.007843, (300, 300), 127.5)
        self.model.setInput(blob)
        detections = self.model.forward()
        probs = [
            detections[0, 0, i, 2] if int(detections[0, 0, i, 1]) == 15 else 0 
            for i in np.arange(0, detections.shape[2])
        ]
        person_prob = max(probs)
        return person_prob

    def check_contours(self, contours):
        contour_check = False
        for contour in contours:
            if contour['size'] > self.min_area:
                contour_check = True
        return contour_check

    def classify(self, frame, contours, pir):
        """Classify whether the system should flag motion being detected

        Args:
            frame (numpy.ndarray): Image to classify
            contours (list): List of contours meta
            pir (list): List of PIR motion sensor values

        Returns:
            bool: Motion classification
        """

        classification = False
        
        contour_check = self.check_contours(contours)
        # person_prob = self.get_person_prob(frame)

        # Decide classification strictly on contour_check
        if contour_check:
            classification = True

        return classification
