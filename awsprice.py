#!/usr/bin/env python

'''Price and attributes retrieval module for EC2 and RDS AWS resources

This module uses the HTML code within AWS website, which will most probably
change from time to time, dont blindly rely on this module before checking it
is still functionnal.

AWS website has ``<script>`` sections containing ``JavaScript`` which declares
a ``model`` variable. This variable points to an URL whose content is JS
readable ``JSON`` listing instances types, attributes and prices.

This module uses those ``JSON`` dicts to build ``python`` dicts.

.. note::

   As of 06/2015, the resources you might be interested in will probably be:

     - \*-od: on-demand attributes and on-demand price only
     - ri-v2/\*: prices by reserved instance options

   All resource types can be retrieved with the ``get_restype`` function

Typical usage:

   .. code-block:: python
   
      fulllist = ap.get_all_instances(
          'us-west-1', 'ec2', 'ri-v2/linux-unix-shared'
      )
      ap.instance_price(fulllist, 'm3.xlarge')

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

def get_regions(resource, restype):
    '''Returns attributes or price list dict by regions

    :param str resource: Resource to query, ``ec2`` or ``rds``
    :param str restype: Resource type (``linux-od``, ``rhel-od`` ...)

    :return: Price list with region as key
    :rtype: dict
    '''

    models = get_models(resource)

    for url in models:
        if restype not in url:
            continue

        js = requests.get(url)

        # as of 31/05/2015, format is
        # od: callback({vers=0.01,config{:{...}});
        # reserved: callback({config{:{...}},vers:0.01});
        jregex = re.search('.+config:(\{(.+)\})(\}\);|,vers:0\.0.+)', js.text)
        if jregex:
            s = re.sub(r'([a-zA-Z0-9_-]+):', r'"\1":', jregex.group(1))
            pricelist = json.loads(s)
            return [r for r in pricelist['regions']]

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

    :param str fulllist: Full instance list from ``get_all_instances``
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

    :param str fulllist: Full instance list from ``get_all_instances``
    :param str itype: Instance type

    :return: Dict of given instance type price
    :rtype: dict
    '''

    inst_type = {}
    for inst_type in fulllist['instanceTypes']:
        if inst_type['type'] == itype:
            return inst_type['terms']

def get_insttypes(fulllist):

    inst_types = []
    for inst_type in fulllist['instanceTypes']:
        inst_types.append(inst_type['type'])

    return inst_types

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

    :param str fulllist: Full instance list from ``get_all_instances``
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

def prices2csv(fulllist):
    '''An example function that converts all instances prices to a CSV file

    :param str fulllist: Full instance by regions list from ``get_regions``

    .. note::

       If may want to modify the ``head`` and ``tmprow`` variables to suit your
       needs.
    '''

    typelist = []
    for region in fulllist:
        for itype in region['instanceTypes']:
            if not itype['type'] in typelist:
                typelist.append(itype['type'])

    def getusd(term, option, duration):
        # fulllist[x]['instanceTypes'][y]['terms'][z]['purchaseOptions']
        for opt in term['purchaseOptions']:
            if opt['purchaseOption'] == option:
                for vc in opt['valueColumns']:
                    if vc['name'] == duration:
                        return vc['prices']['USD']

    regions = []
    csvarr = []
    for itype in typelist:
        row = {'type': itype}
        # fulllist[x]
        for region in fulllist:
            curreg = region['region']
            regions.append(curreg)
            row[curreg] = {}
            row[curreg]['avail'] = False
            # fulllist[x]['instanceTypes']
            for family in region['instanceTypes']:
                if family['type'] == itype:
                    row[curreg]['avail'] = True
                    # fulllist[x]['instanceTypes'][y]
                    for term in family['terms']:
                        row[curreg][term['term']] = {}
                        for otype in [
                            'noUpfront', 'partialUpfront', 'allUpfront'
                        ]:
                            row[curreg][term['term']][otype] = {}
                            for d in [
                                'upfront', 'monthlyStar'
                            ]:
                                row[curreg][term['term']][otype][d] = getusd(
                                    term, otype, d
                                )

        csvarr.append(row)

    head = ''
    for region in regions:
        head = ','.join([
            head, '{0},1y no up,1y part up,monthly,3y part up,monthly'
        ]).format(region)

    f = open('allprices.csv', 'w')

    f.write('{0}\n'.format(head))

    # parse in instance order
    for itype in typelist:
        row = itype
        # then parse in region order
        for region in regions:
            for inst in csvarr:
                if inst['type'] == itype:
                    if inst[region]['avail'] is False:
                        tmprow = 'N,,,,,'
                    else:
                        ireg = inst[region]
                        tmprow = 'Y,{0},{1},{2},{3},{4}'.format(
                            ireg['yrTerm1']['noUpfront']['monthlyStar'],
                            ireg['yrTerm1']['partialUpfront']['upfront'],
                            ireg['yrTerm1']['partialUpfront']['monthlyStar'],
                            ireg['yrTerm3']['partialUpfront']['upfront'],
                            ireg['yrTerm3']['partialUpfront']['monthlyStar']

                        )
                    row = ','.join([row, tmprow])
        f.write('{0}\n'.format(row))

    f.close()


# Example usage

if __name__ == '__main__':
    try:
        all_instances = get_all_instances(sys.argv[1], sys.argv[2], sys.argv[3])
        print(get_instance_attrs(all_instances, 't2.micro'))
        print(instance_price(all_instances, 'm4.xlarge'))
    except IndexError:
        print('usage: {0} <region> <resource> <type>'.format(sys.argv[0]))
