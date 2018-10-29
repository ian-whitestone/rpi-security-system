"""
See what devices are connected to the wifi network.
"""
import time
import os
import logging

import requests

import utils
import config

config.init_logging()

LOGGER = logging.getLogger('who_is_home')
CURR_DIR = os.path.dirname(__file__)
CONF = config.load_private_config()

ROUTER = CONF['router']
USERNAME = ROUTER['user']
PWD = ROUTER['pws']
LOGIN_DATA = {'user': USERNAME, 'pws': PWD}
LOGIN_GET = ROUTER['login_get']
LOGIN_POST = ROUTER['login_post']
GET_CONNECTED_URL = ROUTER['get_connected_url']
BASE_HEADERS = ROUTER['headers']
BASE_COOKIE = ROUTER['base_cookie']
KNOWN_HOSTS = ["Ian's iPhone", 'iPhone']

def get_connected_humans():
    session = requests.session()
    response = session.get(LOGIN_GET)

    headers = BASE_HEADERS.copy()
    response = session.post(LOGIN_POST, LOGIN_DATA, headers=headers)
    user_str = response.headers['Set-Cookie']
    user_id = user_str.split(';')[0].split('userid=')[1]

    new_cookie = BASE_COOKIE.format(USERNAME, PWD, user_id)
    headers['Cookie'] = new_cookie

    url = GET_CONNECTED_URL.format(int(time.time())*1000)
    response = session.get(url, headers=headers)
    devices = response.json()

    device_names = [d['hostName'] for d in devices]
    connected_humans = list(set(KNOWN_HOSTS).intersection(device_names))
    return connected_humans


def loop():
    while True:
        if utils.redis_get('auto_detect_status'):

            try:
                connected_humans = get_connected_humans()        
            except:
                LOGGER.exception("message")
                LOGGER.warning('Error while fetching connected_humans')
                time.sleep(5)
                continue

            if connected_humans:
                LOGGER.info('%s are connected. Turning off camera', 
                            connected_humans)
                utils.redis_set('home', True)
                utils.redis_set('camera_status', False)
                time.sleep(60*5)
            else:
                LOGGER.info('No humans are connected.')
                utils.redis_set('home', False)
                utils.redis_set('camera_status', True)
                # newly connected devices take ~ 30 seconds to show up
                time.sleep(30)

        else:
            time.sleep(60)

if __name__ == '__main__':
    loop()
