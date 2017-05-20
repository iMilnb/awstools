#!/usr/bin/env python
"""
Starts an AWS console from the shell based on cross account roles.
This script is an updated and cleaner version of the one from AWS:
https://aws.amazon.com/blogs/security/how-to-enable-cross-account-access-to-the-aws-management-console/
and this `botocore` version:
https://gist.githubusercontent.com/garnaat/10682964/raw/ef1caa152c006e33b54c0be8226f31ba35db331e/gistfile1.py

It uses an `awsaccounts` JSON file with the format:

    {
        "thirdpartyaccount": {
            "account": "981036328202",
            "role": "ThirdParty",
            "external-id": "123456789"
        },
        "childaccount": {
            "account": "287487895991",
            "role": "ChildAdmin",
        }
    }

You may give a path to a preferred path.

The first parameter specifies the `target` from the JSON file.
"""

import sys
import boto3
import json
import uuid
import requests
import webbrowser

def usage():
    print("usage: {0} <target> [aws accounts file]".format(sys.argv[0]))
    sys.exit(2)

if len(sys.argv) < 2:
    usage()

signin_url = 'https://signin.aws.amazon.com/federation'
console_url = 'https://console.aws.amazon.com/'

if len(sys.argv) > 2:
    awsaccounts = sys.argv[2]
else:
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


