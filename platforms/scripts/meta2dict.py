# -*- coding: utf-8 -*-
"""Converts and return an AWS EC2 metadata in a dict format.

This module makes easier the task of finding and reading instances values
located in the http://169.254.169.254/ `virtual web server`_.

Its usage is trivial::

    import meta2dict

    ec2meta = meta2dict.load()

.. _virtual web server:
   http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html

"""

import json
import requests


def load(root='latest'):
    """Returns instance metadata in a dict format.

    Args:
        root (str): root directory.

    Return:
        dict: instance metadata.

    """
    metaurl = 'http://169.254.169.254/{0}'.format(root)
    # those 3 top subdirectories are not exposed with a final '/'
    metadict = {'dynamic': {}, 'meta-data': {}, 'user-data': {}}

    for subsect in metadict:
        _datacrawl('{0}/{1}/'.format(metaurl, subsect), metadict[subsect])

    return metadict


def _datacrawl(url, d):
    """Recursively populates a dict with metadata.

    Args:
        url (str): URL to parse
        d (dict): dict to populate data with

    """
    r = requests.get(url)
    if r.status_code == 404:
        return

    for l in r.text.split('\n'):
        if not l: # handle "instance-identity/\n" case
            continue
        newurl = '{0}{1}'.format(url, l)
        # a key is detected with a final '/'
        if l.endswith('/'):
            newkey = l.split('/')[-2]
            d[newkey] = {}
            _datacrawl(newurl, d[newkey])

        else:
            r = requests.get(newurl)
            if r.status_code != 404:
                try:
                    d[l] = json.loads(r.text)
                except ValueError:
                    d[l] = r.text
            else:
                d[l] = None



if __name__ == '__main__':
    # test the load function
    print(json.dumps(load()))
