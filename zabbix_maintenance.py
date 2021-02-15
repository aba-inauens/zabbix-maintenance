#!/usr/bin/python

from datetime import datetime, timedelta
import json
import platform
import socket
import sys
import time
import urllib2
import yaml
import os.path

if platform.system() == "Windows":
    win_path = 'C:\ProgramData\zabbix\zabbix_maintenance.yml'
    if os.path.isfile(win_path) == True:
        configfile = win_path
    else:
        configfile = '.\zabbix_maintenance.yml'
else:
    linux_path = '/etc/zabbix/zabbix_maintenance.yml'
    if os.path.isfile(linux_path) == True:
        configfile = linux_path
    else:
        configfile = './zabbix_maintenance.yml'

with open(configfile, 'r') as ymlfile:
    config = yaml.load(ymlfile, yaml.SafeLoader)

user = config['user']
password = config['password']
server = config['server']
api = "https://" + server + "/api_jsonrpc.php"

def get_token():
    data = {'jsonrpc': '2.0', 'method': 'user.login', 'params': {'user': user, 'password': password},
            'id': '0'}
    req = urllib2.Request(api)
    data_json = json.dumps(data)
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib2.urlopen(req, data_json)
    except urllib2.HTTPError as ue:
        print("Error: " + str(ue))
        sys.exit(1)
    else:
        body = json.loads(response.read())
        if not body['result']:
            print("can't get authtoken")
            sys.exit(1)
        else:
            return body['result']


def get_host_id(check=False):
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "host.get", "params": {"output": "extend", "filter":
           {"host": [hostname]}}, "auth": token, "id": 0}
    req = urllib2.Request(api)
    data_json = json.dumps(data)
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib2.urlopen(req, data_json)
    except urllib2.HTTPError as ue:
        print("Error: " + str(ue))
    else:
        body = json.loads(response.read())
        if not body['result']:
            if check:
                return False
            else:
                print("Host " + hostname + " not found on " + server)
                sys.exit(1)
        else:
            return body['result'][0]['hostid']


def get_maintenance_id():
    global maintenance
    hostid = get_host_id()
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "maintenance.get", "params": {"output": "extend", "selectGroups": "extend",
                                                                      "selectTimeperiods": "extend", "hostids": hostid},
            "auth": token, "id": 0}
    req = urllib2.Request(api)
    data_json = json.dumps(data)
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib2.urlopen(req, data_json)
    except urllib2.HTTPError as ue:
        print("Error: " + str(ue))
    else:
        body = json.loads(response.read())
        if not body['result']:
            print("No maintenance for host: " + hostname)
        else:
            maintenance = body
            return int(body['result'][0]['maintenanceid'])


def del_maintenance(mid):
    print("Found maintenance for host: " + hostname + " maintenance id: " + str(mid))
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "maintenance.delete", "params": [mid], "auth": token, "id": 1}
    req = urllib2.Request(api)
    data_json = json.dumps(data)
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib2.urlopen(req, data_json)
    except urllib2.HTTPError as ue:
        print("Error: " + str(ue))
        sys.exit(1)
    else:
        print("Removed existing maintenance")


def start_maintenance():
    maintids = get_maintenance_id()
    maint = isinstance(maintids, int)
    global maintenance
    if maint is True:
        if until < int(maintenance['result'][0]['active_till']):
            del_maintenance(maintids)
            hostid = get_host_id()
            token = get_token()
            data = {"jsonrpc": "2.0", "method": "maintenance.create", "params":
                {"name": "maintenance_" + hostname, "active_since": int(maintenance['result'][0]['active_since']), "active_till": int(maintenance['result'][0]['active_till']), "hostids": [hostid], "timeperiods":
                [{"timeperiod_type": 0, "period": period},{"timeperiod_type": 0, "period": int(maintenance['result'][0]['timeperiods'][0]['period'])}]}, "auth": token, "id": 1}
            req = urllib2.Request(api)
            data_json = json.dumps(data)
            req.add_header('content-type', 'application/json-rpc')
            try:
                response = urllib2.urlopen(req, data_json)
            except urllib2.HTTPError as ue:
                print("Error: " + str(ue))
                sys.exit(1)
            else:
                print("Added a " + str(period / int('3600')) + " hours period on host: " + hostname)
                sys.exit(0)
        del_maintenance(maintids)
        hostid = get_host_id()
        token = get_token()
        data = {"jsonrpc": "2.0", "method": "maintenance.create", "params":
            {"name": "maintenance_" + hostname, "active_since": int(maintenance['result'][0]['active_since']), "active_till": until, "hostids": [hostid], "timeperiods":
            [{"timeperiod_type": 0, "period": period},{"timeperiod_type": 0, "period": int(maintenance['result'][0]['timeperiods'][0]['period'])}]}, "auth": token, "id": 1}
        req = urllib2.Request(api)
        data_json = json.dumps(data)
        req.add_header('content-type', 'application/json-rpc')
        try:
            response = urllib2.urlopen(req, data_json)
        except urllib2.HTTPError as ue:
            print("Error: " + str(ue))
            sys.exit(1)
        else:
            print("Added a " + str(period / int('3600')) + " hours period on host: " + hostname + " and extended active till date")
            sys.exit(0)
    hostid = get_host_id()
    token = get_token()
    data = {"jsonrpc": "2.0", "method": "maintenance.create", "params":
        {"name": "maintenance_" + hostname, "active_since": now, "active_till": until, "hostids": [hostid], "timeperiods":
        [{"timeperiod_type": 0, "period": period}]}, "auth": token, "id": 1}
    req = urllib2.Request(api)
    data_json = json.dumps(data)
    req.add_header('content-type', 'application/json-rpc')
    try:
        response = urllib2.urlopen(req, data_json)
    except urllib2.HTTPError as ue:
        print("Error: " + str(ue))
        sys.exit(1)
    else:
        print("Added a " + str(period / int('3600')) + " hours maintenance on host: " + hostname)
        sys.exit(0)


def check_host_id():
    if get_host_id(True):
        print("Host " + hostname + " found on " + server)
        sys.exit(0)
    else:
        print("Host " + hostname + " not found on " + server)
        sys.exit(1)


if 'hostname' in config:
    hostname = config['hostname']
else:
    hostname = socket.getfqdn()

if sys.argv[3:]:
    hostname = sys.argv[3]

period = int('3600')
if sys.argv[2:]:
    period = int(sys.argv[2]) * int('3600')

now = int(time.time())
x = datetime.now() + timedelta(seconds=int(period))
float = str(time.mktime(x.timetuple()))
until = int(float.split('.')[0])

if len(sys.argv) > 1:
    if sys.argv[1] == "start":
        start_maintenance()
    elif sys.argv[1] == "stop":
        maintids = get_maintenance_id()
        maint = isinstance(maintids, int)
        if maint is True:
            del_maintenance(maintids)
    elif sys.argv[1] == "check":
        check_host_id()
    else:
        print("Error: did not receive action argument start, stop or check")
        sys.exit(1)
else:
    print(sys.argv[0] + " <start|stop|check> [hours] [fqdn]")
    sys.exit(1)
