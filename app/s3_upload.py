import time
import os

from app import utils

CURR_DIR = os.path.dirname(__file__)
IMG_DIR = os.path.join(CURR_DIR, 'imgs')
CONF = utils.CONF
BUCKET = CONF['bucket']
S3_IMG_PREFIX = 'images'

def loop():
    """Loop through the images directory, upload images to S3, delete after
    uploading
    """

    images = utils.search_path(IMG_DIR, filetypes=['.jpg'])
    for img in images:
        key = S3_IMG_PREFIX + img.split(IMG_DIR)[-1]
        utils.upload_to_s3(BUCKET, img, key)
        os.remove(img)
    utils.clean_dir(IMG_DIR, exclude=['.gitignore'])
    time.sleep(60*5)


if __name__ == '__main__':
    loop()
