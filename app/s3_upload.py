"""Periodically upload all the training data to S3
"""
import time
import logging
import os

import utils
import config

LOGGER = logging.getLogger('s3_upload')
CONF = config.load_config()
BUCKET = CONF['bucket']

config.init_logging()

def loop():
    """Loop through the training data directory, upload files to S3, 
    delete after uploading
    """
    while True:
        files = utils.search_path(config.TRAIN_DIR, filetypes=['.pkl', '.txt'])
        LOGGER.info('Uploading %s files', len(files))
        for file in files:
            key = os.path.basename(file)
            try:
                utils.upload_to_s3(BUCKET, file, key)
                os.remove(file)
            except:
                LOGGER.exception("message")
                LOGGER.error('Error while uploading file %s', file)
        time.sleep(60*5)

if __name__ == '__main__':
    loop()
