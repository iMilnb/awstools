#!/usr/bin/env python

'''Price retrieval module for EC2 and RDS AWS resources

This module uses the HTML code within AWS website, which will most probably
change from time to time, dont blindly rely on this module before checking it
is still functionnal.

AWS website has ``<script>`` sections containing ``JavaScript`` which declares
a ``model`` variable. This variable points to an URL whose content is JS
readable ``JSON`` listing instances types, attributes and prices.

This module uses those ``JSON`` dicts to build ``python`` dicts, it can be used
as a replacement of http://ec2instances.info/instances.json
'''

import requests
import re
import sys
import demjson
from bs4 import BeautifulSoup

def get_awshtml(resource):
    '''Retrieve JS from AWS website for a given resource (``ec2`` or ``rds``)

    :param str resource: Resource to query, ``ec2`` or ``rds``

    :return text:
    :rtype: str
    '''
    return BeautifulSoup(requests.get(
        'http://aws.amazon.com/{0}/pricing/'.format(resource)
    ).text)

def get_models(resource):
    '''Retrieve available models

    :param str resource: Resource to query, ``ec2`` or ``rds``

    :return urllist: List of available models urls
    :rtype: list
    '''

    s = get_awshtml(resource)
    urllist = []
    for m in s.find_all('script'):
        r = re.search('model:[^\']*\'([^\']+)', m.text)
        if r and r.group(1):
            urllist.append('http:{0}'.format(r.group(1)))

    return urllist

def get_regions(resource, rtype):
    '''Returns price a price list dict by regions

    :param str resource: Resource to query, ``ec2`` or ``rds``
    :param str rtype: Resource type (``linux-od``, ``rhel-od`` ...)

    :return: Price list with region as key
    :rtype: dict
    '''

    models = get_models(resource)

    for url in models:
        if rtype not in url:
            continue

        js = requests.get(url)

        # as of 31/05/2015, format is
        # callback({vers=0.01,config{:{...}});
        jregex = re.search('[^\(]+\(\{[^{]+(.+)\}\);$', js.text)
        if jregex:
            # demjson is less picky than json, keys are not "enclosed"
            pricelist = demjson.decode(jregex.group(1))
            return [ r for r in pricelist['regions']]

    return {}

def get_all_instances(resource = None, rtype = None, region = None):
    '''Returns an array of resource type on region

    :param str resource: Resource to query, ``ec2`` or ``rds``
    :param str rtype: Resource type (``linux-od``, ``rhel-od`` ...)
    :param str region: Region to lookup (``us-west-1`` ...)

    :return prices: Dict containing instances properties and prices per hour
    :rtype: dict

    .. note::

       as of 31/05/2015, format is
       model: '//a0.awsstatic.com/pricing/1/ec2/linux-od.min.js'
    '''

    pricelist = get_regions(resource, rtype)
    for reg in pricelist:
        if reg['region'] == region:
            return reg

    return None

def get_instance_attrs(fulllist, itype):
    '''Returns instance price and caracteristics for a given region

    :param str fulllist: Full instance list caracteristics from
    ``get_all_instances``
    :param str itype: Instance type

    :return: Dict of instance caracteristics
    :rtype: dict
    '''

    for itypes in fulllist['instanceTypes']:
        for i in itypes['sizes']:
            if i['size'] == itype:
                return i

def get_rtype(resource):
    '''List resource types

    :param str resource: Resource to query, ``ec2`` or ``rds``

    :return: List of resource types
    :rtype: list
    '''

    models = get_models(resource)

    typelist = []
    for url in models:
        rtype = re.search('.*/{0}/(.+)\.min\.js'.format(resource), url)
        if rtype and rtype.group(1):
            typelist.append(rtype.group(1))

    return typelist

# Example usage of this module: awsprice.py ec2 linux-od eu-west-1

if __name__ == '__main__':
    try:
        all_instances = get_all_instances(sys.argv[1], sys.argv[2], sys.argv[3])
        print(get_instance_attrs(all_instances, 't2.micro'))
    except IndexError:
        print('usage: {0} <resource> <type> <region>'.format(sys.argv[0]))
