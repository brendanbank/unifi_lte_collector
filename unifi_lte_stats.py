#!/usr/bin/env python3

import requests 
import urllib3
import re
import time
import prometheus_client
from prometheus_client import Info, generate_latest, Gauge, start_http_server
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from os import environ, path
from dotenv import load_dotenv

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))

import logging, sys
log = logging.getLogger(path.basename(__file__))

logging.basicConfig(format='%(name)s.%(funcName)s(%(lineno)s): %(message)s', stream=sys.stderr, level=logging.INFO)

""" Set defaults """
PORT = environ.get('PORT', 9013)
FREQ = environ.get('FREQ', 30)

try:
    PORT = int(PORT)
    FREQ = int(FREQ)
except Exception as e:
    log.critical(f'could not set PORT to "{PORT}" or FREQ to "{FREQ}: {e}"')
    exit(1)

""" get authentication credentials from .env file"""

HOSTNAME = environ.get('HOSTNAME')
USERNAME = environ.get('USERNAME')
PASSWORD = environ.get('PASSWORD')

for i in ['USERNAME', 'PASSWORD', 'HOSTNAME']:
    if not environ.get(i):
        log.critical(f'{i} is not set ')
        exit(1)

TIMEOUT = 5


def main():
    
    """ Set variables """
    
    login_url = f"https://{HOSTNAME}/api/auth/login"
    username = USERNAME
    password = PASSWORD
    Headers = {'Content-type': 'application/json'} 
    device_url = f"https://{HOSTNAME}/proxy/network/api/s/default/stat/device"

    """ Create a prometheus_client registry and http session"""
    
    registry = prometheus_client.CollectorRegistry()
    http_session = requests.Session()

    """ create prometheus_client items """
    lte_info = Info('unifi_lte', 'LTE info', registry=registry)

    stats = ['lte_rx_chan', 'lte_tx_chan', 'lte_rssi', 'lte_rsrq', 'lte_rsrp', 'total_tx_bytes', 'total_rx_bytes', 'lte_signal']
    
    lte_stats = {}
    
    for i in stats:
        lte_stats[i] = Gauge('unifi_' + i, i, labelnames=['id', 'name', 'model'], registry=registry)
    
    stats_text = ['lte_connected', 'lte_imei', 'lte_iccid', 'lte_radio', 'lte_ip', 'lte_networkoperator', 'lte_pdptype', \
                   'lte_rat', 'lte_signal', 'lte_mode', 'lte_band', 'lte_cell_id', 'lte_radio_mode', \
                   'model', 'name', 'ip', 'mac', 'version', 'license_state', '_id' ]
    
    lte_data = {}

    """ create prometheus server """

    start_http_server(PORT, registry=registry)
    
    cookie = None
                          
    while True:
        
        """ try to fetch data, this fill fail on the first run """
        try:
            r_data = http_session.get(device_url, cookies=cookie, verify=False, timeout=TIMEOUT)
        except Exception as e:
            log.critical(f'could not connect to {device_url}: {e}')
            time.sleep(FREQ)
            continue
        
        if (r_data.status_code != 200):
            """ try to authenticate """
            
            log.critical(f'Could not fetch {device_url}: http status code: {r_data.status_code}')
            data = {'username': username, 'password': password }

            log.info(f'try to fetch cookie from: {login_url}')
            
            try:
                r = http_session.post(login_url,
                            json=data,
                            headers=Headers,
                            verify=False,
                            timeout=TIMEOUT
                            )
            except Exception as e:
                log.critical(f'could not connect to {login_url}: f{e}')
                time.sleep(FREQ)
                continue

            if (r.status_code == 200):
                log.info(f'login was successful on {login_url}')
                cookie = r.cookies
                
            else:
                log.critical(f'Could not fetch: http status code: {r.status_code}, sleep for 60 sec')
                time.sleep(60)
                
            continue

        log.info(f'Fetched data from {device_url}')

        j_data = r_data.json()
        
        for data in j_data['data']:
            
            """Only pull data from ULTEPEU or ULTEUS device types"""
            
            if data['model'] == "ULTEPEU" or data['model'] == "ULTEUS":
                lte_data['name'] = data['name']
                lte_data['model'] = data['model']
                lte_data['id'] = data['_id']
                lte_data['stats'] = {}
                for i in stats:
                    if not (i in data):
                        continue
                                        
                    lte_data['stats'][i] = data[i]

                lte_data['info'] = {}
                for i in stats_text:
                    if i in data:
                        lte_data['info'][i] = data[i]

        """Fill unifi_lte_info with details"""
        lte_info.info(lte_data['info'])
        log.debug(f'fill info with {lte_data["info"]}')
        
        """Fill unifi_* stats """
        for k in lte_stats.keys():
            if not (k in lte_data['stats']):
                log.info (f'element {k} not in data set')
                continue
            
            if k == 'lte_signal':
                signal = re.search(r'\d', lte_data['stats'][k])
                lte_stats[k].labels(lte_data['id'], lte_data['name'], lte_data['model']).set(signal.group())
                continue
            
            lte_stats[k].labels(lte_data['id'], lte_data['name'], lte_data['model']).set(lte_data['stats'][k])
            log.debug(f'set {k} to  {lte_data["stats"][k]}')
            
        log.debug(f'generate_latest')
        log.debug(generate_latest(registry=registry).decode("ascii"))
            
        time.sleep (FREQ)
            
            
            
if __name__ == "__main__":
    main() 

