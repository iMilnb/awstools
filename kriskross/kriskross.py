#!/usr/bin/env python
"""
Starts an AWS console from the shell based on cross account roles.

See `README.md` for more details.

Usage:
  kriskross.py <target> [--awsaccounts=<file> --mfa=<token>]

"""

import sys
import boto3
import json
import uuid
import requests
import webbrowser
from docopt import docopt

args = docopt(__doc__, version = 'kriskross 0.2')

target = args.get('<target>')
awsaccounts = args.get('--awsaccounts')
mfatoken = args.get('--mfa')

signin_url = 'https://signin.aws.amazon.com/federation'
console_url = 'https://console.aws.amazon.com/'

if awsaccounts == None:
    awsaccounts = 'awsaccounts'

prefs = json.load(open(awsaccounts))
target = sys.argv[1]

# prepare assume role parameters
params = {}
params['RoleArn'] = 'arn:aws:iam::{0}:role/{1}'.format(
    prefs[target]['account'], prefs[target]['role']
)
# random hexadecimal
params['RoleSessionName'] = uuid.uuid4().hex
# ExternalId for 3rd party accounts
if 'external-id' in prefs[target]:
    params['ExternalId'] = prefs[target]['external-id']
# MFA token
if mfatoken != None and 'mfa' in prefs[target]:
    params['SerialNumber'] = prefs[target]['mfa']
    params['TokenCode'] = mfatoken

p = {}
if 'profile' in prefs[target]:
    p['profile_name'] = prefs[target]['profile']

s = boto3.Session(**p)
sts = s.client('sts')

creds = sts.assume_role(**params)

json_creds = json.dumps(
    {
        'sessionId': creds['Credentials']['AccessKeyId'],
        'sessionKey': creds['Credentials']['SecretAccessKey'],
        'sessionToken': creds['Credentials']['SessionToken']
    }
)

params = {'Action': 'getSigninToken', 'Session': json_creds}


r = requests.get(signin_url, params = params)

params = {
    'Action': 'login',
    'Issuer': '',
    'Destination': console_url,
    'SigninToken': json.loads(r.text)['SigninToken'],
}

if 'external-id' in prefs[target]:
    params['ExternalId'] = prefs[target]['external-id']

uri = '{0}?{1}'.format(signin_url, requests.compat.urlencode(params))

webbrowser.open(uri)


