"""
See what devices are connected to the wifi network.
"""
import requests
import time
import os
import logging
from app import utils

LOGGER = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(__file__)
CONF = utils.read_yaml(os.path.join(CURR_DIR, 'private.yml'))
ROUTER = CONF['router']

USERNAME = ROUTER['user']
PWD = ROUTER['pws']
LOGIN_DATA = {'user': USERNAME, 'pws': PWD}
LOGIN_GET = ROUTER['login_get']
LOGIN_POST = ROUTER['login_post']
GET_CONNECTED_URL = ROUTER['get_connected_url']
BASE_HEADERS = ROUTER['headers']
BASE_COOKIE = ROUTER['base_cookie']
KNOWN_HOSTS = ['Ians-iPhone-2', 'Sarahs-iPhone']

def loop():
    while True:
        if utils.redis_get('auto_detect_status'):
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

            if connected_humans:
                LOGGER.info('{} are connected. Turning off camera'
                       .format(connected_humans))
                utils.redis_set('home', True)
                utils.redis_set('camera_status', False)
                utils.led(False)
                time.sleep(60*5)
            else:
                LOGGER.info('No humans are connected. ')
                utils.redis_set('home', False)
                utils.led(True)
                utils.redis_set('camera_status', True)
                # newly connected devices take 30 seconds to show up
                time.sleep(30)

        else:
            time.sleep(60)

if __name__ == '__main__':
    loop()
