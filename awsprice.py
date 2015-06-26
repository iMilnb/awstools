#!/usr/bin/env python

'''Price retrieval module for EC2 and RDS AWS resources

This module uses the HTML code within AWS website, which will most probably
change from time to time, dont blindly rely on this module before checking it
is still functionnal.

AWS website has ``<script>`` sections containing ``JavaScript`` which declares
a ``model`` variable. This variable points to an URL whose content is JS
readable ``JSON`` listing instances types, attributes and prices.

This module uses those ``JSON`` dicts to build ``python`` dicts.
'''

import requests
import re
import sys
import json
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
        # od: callback({vers=0.01,config{:{...}});
        # reserved: callback({config{:{...}},vers:0.01});
        jregex = re.search('.+config:(\{(.+)\})(\}\);|,vers:0\.0.+)', js.text)
        if jregex:
            s = re.sub(r'([a-zA-Z0-9_-]+):', r'"\1":', jregex.group(1))
            pricelist = json.loads(s)
            return [ r for r in pricelist['regions']]

    return {}

def get_all_instances(region = None, resource = None, restype = None):
    '''Returns an array of resource type on region

    :param str region: Region to lookup (``us-west-1`` ...)
    :param str resource: Resource to query, ``ec2`` or ``rds``
    :param str restype: Resource type (``linux-od``, ``rhel-od`` ...)

    :return prices: Dict containing instances properties and prices per hour
    :rtype: dict

    .. note::

       as of 31/05/2015, format is
       model: '//a0.awsstatic.com/pricing/1/ec2/linux-od.min.js'
    '''

    pricelist = get_regions(resource, restype)
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

def get_instance_prices(fulllist, itype):
    '''Returns prices corresponding to a reserve instance type, as of 26/06/15,
    those are listed in the ``ri-v2/*`` rtypes.

    :param str fulllist: Full instance list caracteristics from
    ``get_all_instances``
    :param str itype: Instance type

    :return: Dict of given instance type price
    :rtype: dict
    '''

    inst_type = {}
    for inst_type in fulllist['instanceTypes']:
        if inst_type['type'] == itype:
            return inst_type['terms']
    

def get_restype(resource):
    '''List resource types

    :param str resource: Resource to query, ``ec2`` or ``rds``

    :return: List of resource types
    :rtype: list
    '''

    models = get_models(resource)

    typelist = []
    for url in models:
        restype = re.search('.*/{0}/(.+)\.min\.js'.format(resource), url)
        if restype and restype.group(1):
            typelist.append(restype.group(1))

    return typelist

def instance_price(fulllist, itype):
    '''An example function that gives prices for a given instance type

    :param str region: AWS region
    :param str resource: Pricing resource (``linux-od``...)
    :param str itype: Instance type (``t2.micro``, ``m3.large``...)

    :return: A simple hourly prices dict
    :rtype: dict
    '''
    prices = fulllist['instanceTypes']

    pricelist = {
        'ondemand': None,
        'yrTerm1': {},
        'yrTerm3': {}
    }
    for rtype in prices:  # resource type (t2.micro, m3.large...)
        if rtype['type'] == itype:
            pricelist['ondemand'] = \
                rtype['terms'][0]['onDemandHourly'][0]['prices']['USD']
            for term in rtype['terms']:  # terms (yrTerm1, yrTerm3)
                for option in term['purchaseOptions']:
                    for value in option['valueColumns']:
                        if option['purchaseOption'] == 'partialUpfront':
                            if value['name'] == 'effectiveHourly':
                                pricelist[term['term']]['partial'] = \
                                    value['prices']['USD']
                        if option['purchaseOption'] == 'allUpfront':
                            if value['name'] == 'effectiveHourly':
                                pricelist[term['term']]['full'] = \
                                    value['prices']['USD']
                        if (term['term'] == 'yrTerm1' and
                            option['purchaseOption'] == 'noUpfront' and
                            value['name'] == 'effectiveHourly'):
                                pricelist['yrTerm1']['noup'] = \
                                    value['prices']['USD']
    return pricelist


# Example usage

if __name__ == '__main__':
    try:
        all_instances = get_all_instances(sys.argv[1], sys.argv[2], sys.argv[3])
        print(get_instance_attrs(all_instances, 't2.micro'))
        print(instance_price(
            'eu-west-1', 'ri-v2/linux-unix-shared', 'm4.xlarge')
        )
    except IndexError:
        print('usage: {0} <resource> <type> <region>'.format(sys.argv[0]))
