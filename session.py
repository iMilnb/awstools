
'''Helper functions in order to easily manipulate AWS objects with `boto3`_

.. module:: Aws
   :platform: UNIX
   :synopsis: Ease access to boto3 and wraps many useful functions

.. moduleauthor:: Emile 'iMil' Heitor <imil@NetBSD.org>

.. _boto3: http://boto3.readthedocs.org/en/latest/
'''

import boto3
import base64

class Aws:
    '''Aws class constructor

    :param str profile: Region profile, as defined in awscli configuration
    :param str t: Resource type, like ``ec2``, ``cloudformation``...

    :return: Access to resource, client and helpers
    '''
    def __init__(self, profile, t):
        '''Init method
        '''
        self.profile = profile
        if profile:
            self.session = boto3.Session(profile_name=profile)
            self.region = self.session._session.get_config_variable('region')
        if t:
            self.client = self.session.client(t)
            # some objects don't have resource (i.e. route53)
            try:
                self.resource = self.session.resource(t)
            except:
                pass

    def lsinstances(self, obj):
        '''Get all instances objects

        :param str obj: String form of resource type to get list from
        :return: All instances in object form
        '''
        return getattr(self.resource, obj).all()

    def mktags(self, taglst):
        '''Makes a Filter-friendly tag list

        :param dict taglst: A dict of key / value pairs

        :return: Filter-friendly tag list
        :rtype: dict
        '''
        tags = []
        for t in taglst:
            tags.append({'Key': t, 'Value': taglst[t]})
        return tags

    def tags2dict(self, tags):
        '''Converts a Filter tag list to a dict

        :param dict tags: A dict of Filter tag list

        :return: A simple key / value dict
        :rtype: dict
        '''
        ret = {}
        for t in tags:
            ret[t['Key']] = t['Value']
        return ret

    def get_id_from_nametag(self, res, tag):
        '''Returns a resource id matching a Name tag

        :param str obj: The resource to get the id from
        :param str tag: The Name tag

        :return: Resource id
        '''
        for o in getattr(self.resource, res).filter(
            Filters=[{'Name': 'tag:Name', 'Values': [tag]}]
        ):
            return o.id
    
        return None

    def mkuserdata(self, b64 = False, userdata = [], name = '', netblock = ''):
        '''Merge userdata files and possibly convert it to ``base64``

        :param boolean b64: Should we convert userdata to ``base64``
        :param list userdata: A list of userdata files
        :param str name: Name to be passed as an argument to userdata
        :param str netblock: Netblock (CIDR) argument for userdata

        :return: Merged userdata files, possibly in ``base64``
        :rtype: str
        '''
        sh = ''
        for u in userdata:
            with open('userdata/{0}'.format(u), 'r') as f:
                sh = sh + f.read()
        sh = sh.format(self.profile, name.lower(), netblock)
        if b64 is False:
            return sh
        else:
            return base64.b64encode(sh)

    def gettagval(self, res, tag):
        '''Returns a tag value for a given resource

        :param str res: The resource to get the tag from
        :param str tag: Tag's name

        :return: Tag value
        :rtype: str
        '''
        for t in res.tags:
            if t['Key'].lower() == tag.lower():
                return t['Value']
        return 'none'

    def create_tag(self, rid, k, v):
        '''Creates a tag entry for a given resource

        :param rid: Resource id
        :k: Tag key, will be titled (upper case first letter)
        :v: Tag value
        '''
        self.resource.create_tags(
            Resources = [rid],
            Tags = self.mktags({
                k.title(): v
            })
        )

    def lsinstnames(self):
        '''Returns a dict of instances ids and Name tag

        :return: Dict of ``key`` = ``id`` / ``value`` = ``Name tag``
        '''
        instances = self.resource.instances.all()
        instname = {}
        for i in instances:
            instname[i.id] = self.gettagval(i, 'Name')

        return instname

    def dmesg(self, name):
        '''Returns console output for a given instance ``id`` or Name tag

        :param str name: Instance ``id`` or Name tag

        :return: Console output
        :rtype: str
        '''
        instances = self.lsinstnames()
        for i in instances:
            if name in i or name in instances[i]:
                return self.client.get_console_output(InstanceId=i)['Output']

    def getamis(self, glob):
        '''Returns all AMI ids and creation date ordered by the latter

        :param str glob: An AMI name ``glob``

        :return: Ordered list of AMI ids
        :rtype: list
        '''
        imgs = {}
        for i in self.resource.images.filter(
            Filters = [{'Name': 'name', 'Values': [glob]}]
        ):
            imgs[i.id] = i.creation_date
        return sorted(imgs, key = imgs.get)

    def getami(self, glob):
        '''Returns the latest AMI matching ``glob``

        :param str glob: An AMI name ``glob``

        :return: Latest AMI matching the ``glob``
        :rtype: str
        '''
        return self.getamis(glob)[-1]

    def getinst(self, iid):
        '''Returns an instance resource

        :param str iid: Instance id

        :return: Instance resource
        '''
        return self.resource.Instance(iid)

    def getall(self, res):
        '''Return all occurences for a resource

        :param str res: Resource name

        :return: List of all resources
        :rtype: list
        '''
        return [i for i in getattr(self.resource, res).all()]

    def change_nsrecord(self, action, dnsrecord):
        '''Create a DNS record

        :param str action: One of ``CREATE``, ``DELETE`` or ``UPSERT``
        :param dict dnsrecord: A dict describing the DNS record to change

        .. code-block:: python

           dnsrecord = {
               'zone': 'foo.com',  # domain name
               'rectype': 'A'|'NS'|'CNAME'|'MX'|'PTR'|'SRV'|'SPF'|'AAAA',
               'name': 'myhost',  # host part only
               'target': 'targetId'|'www.bar.com'|'10.0.0.1',
               'ttl': 300,  # do not add TTL for an alias target
               'healthcheck': True,  # optional, alias target only
               'dnsname': 'foo-1.region.amazonaws.com'  # alias target only
           }

        .. note::

           For a ``targetId`` record, ``dnsname`` is the external DNS name AWS
           creates for the ELB, S3 bucket, CloudFront distribution or another
           route 53 resource on the same hosted zone.
           Also note that an ``AliasTarget`` must not have a ``TTL`` specified.

        Usage:

        .. code-block:: python

           obj.change_nsrecord('CREATE', dnsrecord)

        Documentation:

        * http://docs.aws.amazon.com/Route53/latest/APIReference/CreateAliasRRSAPI.html
        * http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/quickref-route53.html
        * http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-choosing-alias-non-alias.html

        '''

        hzones = self.client.list_hosted_zones_by_name(
            DNSName = dnsrecord['zone']
        )
        zoneid = hzones['HostedZones'][0]['Id']

        dnsname = '{0}.{1}.'.format(dnsrecord['name'], dnsrecord['zone'])

        change = {
            'Action': action,
            'ResourceRecordSet': {
                'Name': dnsname,
                'Type': dnsrecord['rectype'],
            }
        }

        if 'dnsname' in dnsrecord:  # Alias target
            if not 'healthcheck' in dnsrecord:
                hc = False
            else:
                hc = dnsrecord['healthcheck']
            change['ResourceRecordSet']['AliasTarget'] = {
                'HostedZoneId': dnsrecord['target'],
                'DNSName': dnsrecord['dnsname'],
                'EvaluateTargetHealth': hc
            }
            change['ResourceRecordSet']['SetIdentifier'] = '{0}_{1}_{2}'.format(
                self.region, dnsrecord['name'], dnsrecord['zone']
            )
            change['ResourceRecordSet']['Region'] = self.region
        else:
            change['ResourceRecordSet']['TTL'] = dnsrecord['ttl']
            change['ResourceRecordSet']['ResourceRecords'] = [
                {'Value': dnsrecord['target']}
            ]

        cb = {
            'Comment': '{0} / {1} / {2}'.format(
                action, dnsrecord['name'], dnsrecord['zone']
            ),
            'Changes': [change]
        }

        self.client.change_resource_record_sets(
            HostedZoneId = zoneid,
            ChangeBatch = cb
        )
