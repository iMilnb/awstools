#!/usr/bin/env python
#-*- coding: utf-8 -*-


'''Simple boto3 based EC2 and RDS manipulation tool

To create an EC2 instance, create a ``yaml`` file with the following format:

   .. code-block:: yaml

      frankfurt:
      - subnet-aza:
        - type: t2.micro
          customer: foo
          name: foo-www-1
          image: image-name-glob*
          key: mypemkey
          ipaddr: 10.1.1.2
          sg: [ssh-icmp-reply, http-https]
          userdata:
          - foo.sh
          - bar.sh
        - type ...
      - subnet-azb
        - type ...
      ireland:
      - subnet-aza ...

.. note::

    optional region parameter

    .. code-block:: yaml

       vpc: vpc-name-tag

    optional instance parameters

    .. code-block:: yaml

       data: 10 (default: none)
       srcdstchk: True|False (defaults to False)
       pubip: True|False (defaults to False)
       elb:
         scheme: internal|internet-facing
         elb_proto: tcp|udp
         elb_port: 123
         instance_proto: tcp|udp
         instance_port: 123
         sg: [ssh-hq]

.. note::

    * name should be of the form customer-service-number
    * AZ must exist and have the form: title-az[ab]
    * if no proto / ports are given to ``elb``, it will assume TCP/80

To create an RDS instance, create a ``yaml`` file with the following format:

   .. code-block:: yaml

      frankfurt:
      - foo-rds-subnetgroup:
        - type: db.t1.micro
          customer: foo
          name: foo-rds
          data: 8
          dbengine: MySQL
          dbversion: 5.6.22
          dbroot: root
          subnets: {aza: 10.1.2.0/24, azb: 10.1.3.0/24}
          sg: [mysql]
      - bar-rds-subnetgroup:
        - type ...
      ireland:
      - baz-rds-subnetgroup ...

.. note::

    if the Security Group does not exist yet, you can declare it this way:

    .. code-block:: yaml

       sg: 
       - name: MySQL_from_client_infra-test
         tag: mysql-from-infra-test
         cidr: [10.0.1.0/24, 192.168.1.0/24]
         port: 3306
         proto: tcp

    optional instance parameters

    .. code-block:: yaml

       multiaz: true | false
       maintenance: Tue:04:00-Tue:04:30
       retention: 7 (in days)
       backup: Tue:02:00-Tue:02:30
       autoupgrade: false (defaults to true)
       iops: 2000
       charset: utf8
       storage: standard | gp2 | io1
'''

import os
import sys
import yaml
import time
import string
import random
from subprocess import call
from prettytable import from_csv

sys.path.append(os.getcwd())

import mods.awsprice as ap
from mods.session import Aws
# custom module you'd want to import
try:
    import mods.external as ext
    ext_available = True
except ImportError:
    ext_available = False

if len(sys.argv) < 2:
    print "usage: {0} <function> [arguments]".format(sys.argv[0])
    sys.exit(1)

profile = os.environ.get('EC2REGION')

if profile is None:
    print "Please add a profile or set the EC2REGION environment variable."
    sys.exit(1)

ec2 = Aws(profile, 'ec2')

print "> working on profile: {0}".format(profile)

# by default, work on the 1st VPC
vpc = [v for v in ec2.resource.vpcs.all()][0]

def ls():
    '''List instances running in current region
    '''
    for i in ec2.getall('instances'):
        if i.tags is None:
            print("/!\ {0} has no tag name [{1}]".format(i.id, i.state['Name']))
            continue

        t = ec2.tags2dict(i.tags)
        tid = i.id

        if ext_available is True:
            idtag = ext.custom_idtag
            tid = i.id if not idtag in t else t[idtag]

        print "{0} {1} ({2}) - [{3}]".format(
            tid, t['Name'], i.instance_type, i.state['Name']
        )

def getyaml(fn, yf):
    '''Read infrastructure ``yaml`` description

    :param str fn: Calling function name
    :param str yf: Path to ``yaml`` file
    '''
    if len(sys.argv) < 3:
        print("usage: {0} {1} <path/to/description.yaml>"
            .format(sys.argv[0], fn))
        sys.exit(1)

    try:
        with open(yf, 'r') as f:
            y = yaml.load(f.read())
    except IOError:
        print "{0} not found.".format(yf)
        sys.exit(1)

    return y

def wait4tag(res, tag, val):
    '''Waits for resource to be available before tagging its name

    :param str res: Resource name
    :param str tag: Tag key to be given
    :param str val: Tag value to be given
    '''
    rise = False
    while rise is False:
        try:
            ec2.create_tag(res.id, tag, val)
            rise = True
        except:
            e = sys.exc_info()[1]
            print('waiting for resource to rise, {0}'.format(e))
            time.sleep(1)

def subnet_check(ec2, subname, instance):
    '''Checks subnet existence for a given instance IP address and create it
    if not available

    :param ec2: EC2 resource
    :param str subnet: subnet name
    :param dict instance: Instance informations
    '''
    myaz = subname[-1]

    if ec2.get_obj_from_nametag('subnets', subname):
        print('{0} already available, continuing'.format(subname))
        return

    if ext_available is True:
        niname = ext.natinstancename(instance)
    else:
        niname = 'nat-instance'  # warning, this is an example

    natinstance = [
            i for i in ec2.resource.instances.filter(
                Filters = [{'Name': 'tag:Name', 'Values': [niname]}]
            )
    ]

    vpcid = vpc.id

    if not natinstance:
        print('NO NAT instance for customer {0}'.format(instance['customer']))
        reply = raw_input('attach this network to an Internet gw? [y/N] ')
        if reply[0] != 'y':
            sys.exit(1)
        gwid = [i for i in vpc.internet_gateways.all()][0].id
        nat = False
    else:
        gwid = natinstance[0].id
        nat = True

    zone = None

    azs = ec2.client.describe_availability_zones()
    for raz in azs['AvailabilityZones']:
        # us-east-1[a] == az[a]
        if raz['ZoneName'][-1] == myaz:
            zone = raz['ZoneName']
            break

    if zone is None:
        print('{0} does not match any AZ, aborting'.format(myaz))
        sys.exit(1)

    # EC2 instance
    if 'ipaddr' in instance:
        cidr = '{0}.0/24'.format('.'.join(instance['ipaddr'].split('.')[0:3]))
    # RDS instance
    else:
        cidr = instance['subnets']['az{0}'.format(myaz)]

    # create the subnet
    rs = ec2.resource.create_subnet(
        DryRun = False,
        VpcId = vpcid,
        CidrBlock = cidr,
        AvailabilityZone = zone
    )
    wait4tag(rs, 'Name', subname)
    print('created subnet {0}'.format(rs.id))

    # create a route table
    if instance['type'].startswith('db.'):
        rtname = '{0}-rdsRT'.format(instance['customer'])
    else:
        rtname = '{0}-ec2RT'.format(instance['customer'])

    rt = ec2.get_obj_from_nametag('route_tables', rtname)
    if rt:
        rt_exists = True
        print('{0} already exists, continuing'.format(rtname))
    else:
        rt_exists = False

    # create route table if non existent
    if rt_exists is False:
        rt = ec2.resource.create_route_table(
            DryRun = False,
            VpcId = vpcid
        )

        wait4tag(rt, 'Name', rtname)
        print('created route table {0}'.format(rt.id))

    # associate route table and subnet
    rta = rt.associate_with_subnet(
        DryRun = False,
        SubnetId = rs.id
    )
    print('associated route table {0} with {1}'.format(rt.id, rta.id))
    # create the default route
    kwargs = {'DryRun': False, 'DestinationCidrBlock': '0.0.0.0/0',}
    if nat is True:
        kwargs['InstanceId'] = gwid
    else:
        # subnet has a default route to IGW, we must propagate routes from VGW
        kwargs['GatewayId'] = gwid
        vgw = ec2.client.describe_vpn_gateways()
        for v in vgw['VpnGateways']:
            if v['VpcAttachments']:
                vgwid = v['VpnGatewayId']
                break
        print('attaching route table {0} to vgw {1}'.format(rt.id, vgwid))
        ec2.client.enable_vgw_route_propagation(
            RouteTableId = rt.id,
            GatewayId = vgwid
        )

    rc = rt.create_route(**kwargs)

def _mkdefval(data, kw, default):
    return default if not kw in data else data[kw]

def elb_register(ec2, allaz, curaz, instance):
    '''Register an instance to an ELB, creating the latter if it does not exist

    :param dict allaz: Every AZ present in the region, from the YAML file
    :param str curaz: Current AZ, where the current instance is being created
    :param dict instance: Instance being processed
    '''
    elb = Aws(ec2.profile, 'elb')

    elbs = elb.client.describe_load_balancers()

    lbname = 'elb-{0}'.format(instance['name'][:-2])
    elb_exists = False
    for lb in elbs['LoadBalancerDescriptions']:
        if lb['LoadBalancerName'] == lbname:
           elb_exists = True

    i = instance['elb']

    if elb_exists is False:
        # first check for subnets existence
        subnet_ids = []
        curnet = curaz[:-4]  # current network name without az
        for availz in allaz:
            yaz = availz.keys()[0]
            if curnet in yaz:
                # take 1st IP address from that subnet / AZ
                ipaddr = availz[yaz][0]['ipaddr']
                # and check for subnet existence
                subnet_check(ec2, yaz, instance)
                # and add it to subnet_ids
                subnet_ids.append(ec2.get_id_from_nametag('subnets', yaz))

        sgs = []
        for sglist in instance['elb']['sg']:
            sgs.append(ec2.get_id_from_nametag(
                'security_groups', sglist
            ))

        print('creating ELB {0}'.format(lbname))
        elb.client.create_load_balancer(
            LoadBalancerName = lbname,
            Listeners = [{
                'Protocol': _mkdefval(i, 'elb_proto', 'tcp'),
                'LoadBalancerPort': _mkdefval(i, 'elb_port', 80),
                'InstanceProtocol': _mkdefval(i, 'instance_proto', 'tcp'),
                'InstancePort': _mkdefval(i, 'instance_port', 80)
            }],
            Subnets = subnet_ids,
            SecurityGroups = sgs,
            Scheme = instance['elb']['scheme'],
            Tags = ec2.mktags({'Name': lbname})
        )

    print('registering {0} to ELB {1}'.format(instance['awsid'], lbname))
    elb.client.register_instances_with_load_balancer(
        LoadBalancerName = lbname,
        Instances = [{
            'InstanceId': instance['awsid']
        }]
    )

chars = ''.join([string.letters, string.digits])

def create_rds(ec2, subname, instance):
    '''Create RDS instance described in the ``yaml`` file passed in parameter
    '''

    rds = Aws(ec2.profile, 'rds')

    pwd = ''.join((random.choice(chars)) for x in range(20))

    groupname = ''.join(subname.split('-'))
    subnames = []
    for s in instance['subnets']:
        azname = '{0}-{1}'.format(subname, s)
        subnames.append(azname)
        subnet_check(ec2, azname, instance)

    subnetids = [
        ec2.get_id_from_nametag('subnets', s) for s in subnames
    ]

    descsubgr = rds.client.describe_db_subnet_groups()

    subgr_exists = False
    for subgr in descsubgr['DBSubnetGroups']:
        if subgr['DBSubnetGroupName'] == groupname:
            print("DBSubnetGroupName {0} exists, continuing".format(groupname))
            subgr_exists = True
            break

    if subgr_exists is False:
        rds.client.create_db_subnet_group(
            DBSubnetGroupName = groupname,
            DBSubnetGroupDescription = '{0} subnet group for {1}'.format(
                subname, instance['customer']
            ),
            SubnetIds = subnetids,
            Tags = ec2.mktags({'name': '{0}SubnetGroup'.format(subname)})
        )

    sg = []
    for rule in instance['sg']:
        sg.append(ec2.mksg(vpc, rule).id)

    kwargs = {
        'DBInstanceIdentifier': instance['name'],
        'AllocatedStorage': instance['data'],
        'DBInstanceClass': instance['type'],
        'Engine': instance['dbengine'],
        'MasterUsername': instance['dbroot'],
        'MasterUserPassword': pwd,
        'VpcSecurityGroupIds': sg,
        'DBSubnetGroupName': groupname,
        'EngineVersion': instance['dbversion']
    }
    opts = {
        'maintenance': 'PreferredMaintenanceWindow',
        'retention': 'BackupRetentionPeriod',
        'backup': 'PreferredBackupWindow',
        'multiaz': 'MultiAZ',
        'autoupgrade': 'AutoMinorVersionUpgrade',
        'iops': 'Iops',
        'charset': 'CharacterSetName',
        'storage': 'StorageType'
    }
    for k in opts:
        if k in instance:
            kwargs[opts[k]] = instance[k]
    kwargs['Tags'] = ec2.mktags({'name': instance['name']})

    rc = rds.client.create_db_instance(**kwargs)
    print('creating instance {0}'.format(instance['name']))

# Parse YAML and create EC2 instances

def create():
    '''Create instance(s) described in the ``yaml`` file passed in parameter
    '''
    yf = sys.argv[2]
    y = getyaml(create.__name__, yf)

    for reg in y: # loop through profiles
        ec2 = Aws(reg, 'ec2')
        ec2r = ec2.resource
        for azlst in y[reg]: # loop through AZ list
            if 'vpc' in azlst:
                vpc = ec2.get_obj_from_nametag('vpcs', azlst['vpc'])
                print('> selected {0}'.format(vpc.id))
                continue
            for az in azlst: # loop through AZ
                for instance in azlst[az]:
                    if 'awsid' in instance:
                        reply = raw_input(
                            '{0} exists as {1}, continue? [y/N] '.format(
                                instance['name'], instance['awsid']
                            )
                        )
                        if reply[0] != 'y':
                            continue

                    # check for RDS instance
                    if instance['type'].startswith('db.'):
                        create_rds(ec2, az, instance)
                        continue

                    # check AZ / subnet existence, create it if absent
                    subnet_check(ec2, az, instance)

                    if 'debian' in instance['image']:
                        image = ec2.get_debian_ami(instance['image'])
                    else:
                        image = ec2.getami(instance['image'])
                    sg = []
                    for sglist in instance['sg']:
                        sg.append(ec2.get_id_from_nametag(
                            'security_groups', sglist
                        ))
                    subnet = ec2.get_id_from_nametag('subnets', az)

                    if 'data' in instance:
                        blockdevmap = [
                            {
                                'DeviceName': '/dev/xvdb',
                                'Ebs': {
                                    'VolumeSize': instance['data'],
                                    'DeleteOnTermination': True,
                                }
                            }
                        ]
                    else:
                        blockdevmap = []

                    netint = []
                    if 'pubip' in instance and instance['pubip'] is True:
                        pubip = True
                    else:
                        pubip = False

                    # Here, 'name' is the tag Name

                    # netblock for a NAT-type instance
                    netblock = '{0}.0.0/16'.format(
                        '.'.join(instance['ipaddr'].split('.')[:2])
                    )
                    print("creating instance {0}".format(instance['name']))
                    rc = ec2r.create_instances(
                        ImageId = image,
                        MinCount = 1,
                        MaxCount = 1,
                        KeyName = instance['key'],
                        InstanceType = instance['type'],
                        BlockDeviceMappings = blockdevmap,
                        NetworkInterfaces = [{
                            'DeviceIndex': 0,
                            'Groups': sg,
                            'SubnetId': subnet,
                            'PrivateIpAddress': instance['ipaddr'],
                            'DeleteOnTermination': True,
                            'AssociatePublicIpAddress': pubip
                        }],
                        UserData = ec2.mkuserdata(
                            b64 = False,
                            userdata = instance['userdata'],
                            name = instance['name'],
                            netblock = netblock
                        )
                    )

                    iid = rc[0].id

                    instance['awsid'] = iid
                    tags = ['name', 'customer']
                    # add custom fields
                    if ext_available is True:
                        newtags = ext.addfields(reg, instance)
                        if newtags:
                            tags.extend(newtags)
                    # give the instance a tag name
                    # we are supposed to be able to pass many tags to
                    # create_tags but a traceback occurs as of boto3 0.0.21
                    for tag in tags:
                        print(
                            "tagging instance id {0} {1} to {2}".format(
                                iid, tag, instance[tag]
                            )
                        )
                        wait4tag(ec2r.Instance(iid), tag, instance[tag])

                    with open(sys.argv[2], 'w') as f:
                        yaml.dump(y, f, default_flow_style=False)

                    # Mostly for NAT instances
                    if 'srcdstchk' in instance:
                        r = ec2r.Instance(iid).modify_attribute(
                            SourceDestCheck  = {
                                'Value': instance['srcdstchk']
                            }
                        )

                    # optionally do something with instance informations
                    # like inserting it to your own information system
                    if ext_available is True:
                        ext.instance_actions(ec2, reg, az, instance)

                    # create ELB if needed
                    if 'elb' in instance:
                        elb_register(ec2, y[reg], az, instance)

                    # create additionnal block devices if needed
                    if not blockdevmap:
                        continue

                    devlst = []
                    print("waiting for block devices to rise")
                    while not devlst:
                        devlst = ec2r.Instance(iid).block_device_mappings
                        time.sleep(1)

                    for dev in devlst:
                        dname = dev['DeviceName'][5:]
                        print(
                            "tagging volume {0} to {1}_{2}".format(
                                dev['Ebs']['VolumeId'],
                                dname,
                                instance['name']
                            )
                        )
                        tags = {
                            'Name': '{0}_{1}'.format(
                                dname, instance['name']
                            ),
                            'Customer': instance['customer']
                        }
                        ec2.client.create_tags(
                            Resources = [dev['Ebs']['VolumeId']],
                            Tags = ec2.mktags(tags)
                        )

    # final actions if needed
    if ext_available is True:
        ext.final_actions()

def rm():
    '''Destroys an AWS instance
    '''
    if len(sys.argv) < 3:
        print("usage: {0} rm <aws instance ids ...>")
        sys.exit(1)

    reply = raw_input("REALLY DESTROY {0}? [y/N] ".format(
                ','.join(sys.argv[2:]))
            )
    if reply[0] != 'y':
        print("aborting.")
        sys.exit(0)

    # RDS instance
    if not sys.argv[2].startswith('i-'):
        dbid = sys.argv[2]
        rds = Aws(ec2.profile, 'rds')
        try:
            rds.client.delete_db_instance(
                DBInstanceIdentifier = dbid, SkipFinalSnapshot = True
            )
            print('deleting {0}'.format(dbid))
            sys.exit(0)
        except:
            e = sys.exc_info()[1]
            print('error while deleting {0}: {1}'.format(dbid, e))
            sys.exit(1)

    # pre-delete external actions
    if ext_available is True:
        ext.rm_actions(ec2, sys.argv[2:])

    try:
        ec2.resource.instances.filter(InstanceIds=sys.argv[2:]).terminate()
    except:
        print('error while terminating {0}'.format(sys.argv[2:]))
        sys.exit(1)

def _update_price(total, price):
    return {
        'ondemand': round(total['ondemand'] + float(price['ondemand']), 5),
        'noup': round(total['noup'] + float(price['yrTerm1']['noup']), 5),
        '1yearpartup': round(total['1yearpartup'] + \
            float(price['yrTerm1']['partial']), 5),
        '1yearfullup': round(total['1yearfullup'] + \
            float(price['yrTerm1']['full']), 5),
        '3yearpartup': round(total['3yearpartup'] + \
            float(price['yrTerm3']['partial']), 5),
        '3yearfullup': round(total['3yearfullup'] + \
            float(price['yrTerm3']['full']), 5)
    }

def _print_total_price(price):
    titles = [
        {'ondemand': 'on demand'},
        {'noup': '1 y no up'},
        {'1yearpartup': '1 y part up'},
        {'1yearfullup': '1 y full up'},
        {'3yearpartup': '3 y part up'},
        {'3yearfullup': '3 y full up'}
    ]
    duration = {'hrly': 1, 'mthly': 24 * 30.5, 'yrly': 24 * 30.5 * 12}


    prices = []
    for t in titles:
        prices.append(float(price[t.keys()[0]]))

    with open('prices.csv', 'w') as f:
        f.write('durat,{0}\n'.format(
            ','.join([x.values()[0] for x in titles]))
        )
        for d in sorted(duration, key=duration.get):
            f.write('{0},{1}\n'.format(
                d, ','.join([str(p * duration[d]) for p in prices])
            ))

    with open('prices.csv', 'r') as f:
        print(from_csv(f))


zero_price = {
    'ondemand': 0.0,
    'noup': 0.0,
    '1yearpartup': 0.0,
    '1yearfullup': 0.0,
    '3yearpartup' : 0.0,
    '3yearfullup': 0.0
}

def lsyaml():
    '''Lists instances types used in the descriptive ``yaml`` file
    '''
    t = {}
    fulllist = ap.get_all_instances(
        ec2.region, 'ec2', 'ri-v2/linux-unix-shared'
    )
    total_price = zero_price
    for f in sys.argv[2:]:
        y = getyaml(lsyaml.__name__, f)

        for reg in y: # loop through profiles
            for azlst in y[reg]: # loop through AZ list
                for az in azlst: # loop through AZ
                    for instance in azlst[az]:
                        saz = az.split('-')[-1]
                        if not saz in t:
                            t[saz] = {instance['type']:  0}
    
                        if instance['type'] in t[saz]:
                            t[saz][instance['type']] += 1
                        else:
                            t[saz][instance['type']] = 1

                        prices = ap.instance_price(fulllist, instance['type'])
                        total_price = _update_price(total_price, prices)

    print(yaml.dump(t, default_flow_style=False))

    _print_total_price(total_price)

def lsec2():
    '''List instances types used in EC2
    '''
    if len(sys.argv) < 3:
        print(
            'usage: {0} {1} \'name filter\''.format(
                sys.argv[0], lsec2.__name__
            )
        )
        sys.exit(1)

    t = {}
    total_price = zero_price
    fulllist = ap.get_all_instances(
        ec2.region, 'ec2', 'ri-v2/linux-unix-shared'
    )
    for i in ec2.resource.instances.filter(
        Filters=[{'Name': 'tag:Name', 'Values': [sys.argv[2]]}]
    ):
        az = i.placement['AvailabilityZone'].split('-')[-1]
        if not az in t:
            t[az] = {i.instance_type: 0}

        if i.instance_type in t[az]:
            t[az][i.instance_type] += 1
        else:
            t[az][i.instance_type] = 1

        prices = ap.instance_price(fulllist, i.instance_type)
        total_price = _update_price(total_price, prices)

    print(yaml.dump(t, default_flow_style=False))

    _print_total_price(total_price)


if __name__ == '__main__':
    getattr(sys.modules[__name__], sys.argv[1])()
