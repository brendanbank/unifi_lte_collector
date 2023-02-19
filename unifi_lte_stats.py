#!/usr/bin/env python3
'''
unifi_lte_stats.py -- Exporter for unifi U-LTE-Pro devices 

unifi_lte_stats.py is a data exporter for Prometheus

@author:     Brendan Bank

@copyright:  2023 Brendan Bank. All rights reserved.

@license:    BSDv3

@contact:    brendan.bank ... gmail.com
@deffield    updated: Updated
'''

'''
Copyright 2023 Brendan Bank

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

__all__ = []
__version__ = 0.2
__date__ = '2023-01-10'
__updated__ = '2023-01-20'


import requests 
import urllib3
import re
import time
import prometheus_client
from prometheus_client import Info, generate_latest, Gauge, start_http_server
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import os
from dotenv import load_dotenv
import pprint
import argparse


ENV = '.env'


import logging, sys
log = logging.getLogger(os.path.basename(__file__))

logging.basicConfig(format='%(name)s.%(funcName)s(%(lineno)s): %(message)s', stream=sys.stderr, level=logging.WARN)

""" get authentication credentials from .env file"""


TIMEOUT = 5
POLL_INTERVAL = 20
EXPORTER_PORT = os.environ.get('PORT', 9013)


def main():

    '''main function.'''

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by Brendan Bank on %s.
  Copyright 2023 Brendan Bank. All rights reserved.

  Licensed under the BSD-3-Clause
  https://opensource.org/licenses/BSD-3-Clause

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE''' % (program_shortdesc, str(__date__))

    """ Set variables """

    # Setup argument parser
    parser = argparse.ArgumentParser(description=program_license, formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False,
                         help="set verbosity [default: %(default)s]")
    
    parser.add_argument('-V', '--version', action='version', version=program_version_message)
    
    parser.add_argument('-d', '--debug', action='store_true', dest="debug", default=False,
                        help="set debug [default: %(default)s]")
    
    parser.add_argument('-E', '--exporter-port', type=int, dest="exporter_port", default=EXPORTER_PORT,
                        help="set TCP Port for the exporter server [default: %(default)s]")

    parser.add_argument('-i', '--interval', type=int, dest="interval", default=POLL_INTERVAL,
                        help="Poll interval [default: %(default)s] seconds")

    parser.add_argument('-e', '--environment', type=argparse.FileType('r'), dest="environment_file", default=ENV,
                        help="enviroment file to read from  [default: %(default)s] seconds")
    
    parser.add_argument('hostname', type=str, help='Hostname to poll')



    # Process arguments
    args = parser.parse_args()
    
    if (args.debug):
        log.setLevel(level=logging.DEBUG)
    elif (args.verbose):
        log.setLevel(level=logging.INFO)

    basedir = os.path.abspath(os.path.dirname(__file__))
    envpath = os.path.join(basedir, args.environment_file.name)
    
    load_dotenv(envpath)

    USERNAME = os.environ.get('USERNAME')
    PASSWORD = os.environ.get('PASSWORD')
    
    for i in ['USERNAME', 'PASSWORD']:
        if not os.environ.get(i):
            log.critical(f'{i} is not set ')
            exit(1)


    login_url = f"https://{args.hostname}/api/auth/login"
    Headers = {'Content-type': 'application/json'} 
    device_url = f"https://{args.hostname}/proxy/network/api/s/default/stat/device"

    """ Create a prometheus_client registry and http session"""
    
    registry = prometheus_client.CollectorRegistry()
    http_session = requests.Session()

    """ create prometheus_client items """
    lte_info = Info('unifi_lte', 'LTE info', registry=registry)

    stats = ['lte_rx_chan', 'lte_tx_chan', 'lte_rssi', 'lte_rsrq', 'lte_rsrp', 'total_tx_bytes', 'total_rx_bytes', 'lte_signal','lte_failover', 'uptime']
    
    lte_stats = {}
    
    for i in stats:
        lte_stats[i] = Gauge('unifi_' + i, i, labelnames=['id', 'name', 'model'], registry=registry)
    
    stats_text = ['lte_connected', 'lte_imei', 'lte_iccid', 'lte_radio', 'lte_ip', 'lte_networkoperator', 'lte_pdptype', \
                   'lte_rat', 'lte_signal', 'lte_mode', 'lte_band', 'lte_cell_id', 'lte_radio_mode', \
                   'model', 'name', 'ip', 'mac', 'version', 'license_state', '_id', 'serial',
                   'displayable_version','lte_state','lte_ext_ant', 'lte_connected', 'ip' ]
    
    lte_data = {}

    """ create prometheus server """
    
    drop_privileges()

    start_http_server(EXPORTER_PORT, registry=registry)
    
    cookie = None
                          
    pp = pprint.PrettyPrinter(indent=4)
    
    while True:
        
        """ try to fetch data, this fill fail on the first run """
        try:
            r_data = http_session.get(device_url, cookies=cookie, verify=False, timeout=TIMEOUT)
        except Exception as e:
            log.critical(f'could not connect to {device_url}: {e}')
            time.sleep(POLL_INTERVAL)
            log.debug(f'sleep {POLL_INTERVAL}')

            continue
        
        if (r_data.status_code != 200):
            """ try to authenticate """
            
            log.critical(f'Could not fetch {device_url}: http status code: {r_data.status_code}')
            data = {'username': USERNAME, 'password': PASSWORD }

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
                time.sleep(POLL_INTERVAL)
                log.debug(f'sleep {POLL_INTERVAL}')
                continue

            if (r.status_code == 200):
                log.info(f'login was successful on {login_url}')
                cookie = r.cookies
                
            else:
                log.critical(f'Could not fetch: http status code: {r.status_code}, sleep for 60 sec')
                time.sleep(60)
                log.debug(f'sleep 60')
            continue

        

        j_data = r_data.json()
        
        for data in j_data['data']:
            
            """Only pull data from ULTEPEU or ULTEUS device types"""
            
            if data['model'] == "ULTEPEU" or data['model'] == "ULTEUS":
                
                
                log.debug('ULTE found')
                log.debug(pp.pformat(data))

                
                
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

            elif  k == 'lte_failover':
                if lte_data['stats'][k]:
                    lte_stats[k].labels(lte_data['id'], lte_data['name'], lte_data['model']).set(1)
                else:
                    lte_stats[k].labels(lte_data['id'], lte_data['name'], lte_data['model']).set(0)
            else:            
                lte_stats[k].labels(lte_data['id'], lte_data['name'], lte_data['model']).set(lte_data['stats'][k])
                
            log.debug(f'set {k} to  {lte_data["stats"][k]}')
            
        log.debug(f'generate_latest')
        log.debug(generate_latest(registry=registry).decode("ascii"))
        log.debug(f'sleep {POLL_INTERVAL}')
        if 'lte_signal' in lte_data['stats'] and 'lte_rssi' in lte_data['stats']:
            log.info(f"Fetched data from {args.hostname} signal: '{lte_data['stats']['lte_signal']}' rssi: {lte_data['stats']['lte_rssi']} sleep: {POLL_INTERVAL}s")
            
        time.sleep (POLL_INTERVAL)
            
            
def drop_privileges(uid_name='nobody', gid_name='nogroup'):
    if os.getuid() != 0:
        # We're not root so, like, whatever dude
        return

    log.warning(f'Dropping privileges to user {uid_name} and group {gid_name}')
    
    # Get the uid/gid from the name
    try:
        running_uid = pwd.getpwnam(uid_name).pw_uid
    except Exception as e:
        log.critical(f'cannot find username {uid_name}: {e}')
        exit()

    try:
        running_gid = grp.getgrnam(gid_name).gr_gid
    except Exception as e:
        log.critical(f'cannot find groupname {gid_name}: {e}')
        exit()
 
    # Remove group privileges
    os.setgroups([])
 
    # Try setting the new uid/gid
    os.setgid(running_gid)
    os.setuid(running_uid)
 
    # Ensure a very conservative umask
    old_umask = os.umask(0o077)

if __name__ == "__main__":
    main() 

