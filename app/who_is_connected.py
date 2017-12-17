"""
See what devices are connected to the wifi network.
"""
import requests
import time
import os
from utils import read_yaml

currDir = os.path.dirname(__file__)
CONF = read_yaml(os.path.join(currDir, 'private.yml'))

s = requests.session()
r = s.get('http://192.168.0.1/login.html')

user = CONF['user']
pws = CONF['pws']

data = {'user': user, 'pws': pws}
headers = {
    'Connection': 'keep-alive',
    'Accept': '*/*',
    'Origin': 'http://192.168.0.1',
    'User-Agent': 'Mozilla/5.0 ',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Referer': 'http://192.168.0.1/login.html',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'Cookie': 'LANG_COOKIE=en_US; modelname=; cur_modelname=CGN3AMF'
}
r = s.post('http://192.168.0.1/goform/login', data, headers=headers)
user_str = r.headers['Set-Cookie']
user_id = user_str.split(';')[0].split('userid=')[1]


new_cookie = (
    "LANG_COOKIE=en_US; modelname=CGN3AMF; cur_modelname=CGN3AMF; "
    "userName={0}; password={1}; userid={2};").format(user, pws, user_id)
headers['Cookie'] = new_cookie

url = 'http://192.168.0.1//data/getConnectInfo.asp?_={0}'.format(
                                                        int(time.time())*1000)
r = s.get(url, headers=headers)
response = r.json()

print ([r for r in response if r['hostName'] == 'Ians-iPhone-4'])
print ([r for r in response if r['hostName'] == 'Sarahs-iPhone'])
devices = [device['ipAddr'] for device in response]

if '192.168.0.11' in devices:
    print ('Ian is in da house')

if '192.168.0.12' in devices:
    print ('Sarah is in da house')
