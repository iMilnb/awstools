from troposphere import Base64, Join, Split
from troposphere import Parameter, Ref, Template, Tags
import troposphere.ec2 as ec2
import sys

params = {
    'AmiId': 'AMI Id',
    'InstanceName': 'Name tag of the instance',
    'SecurityGroup': 'Security Group' ,
    'KeyName': 'SSH Key Name' ,
    'InstanceType': 'Instance Type',
    'SubnetA': 'Subnet A',
}

t = Template()

for p in params.keys():
    vars()[p] = t.add_parameter(Parameter(
        p,
        Type = "String",
        Description = params[p]
    ))

for n in range(int(sys.argv[1])):
    if n == 0:
        name = 'master'
    else:
        name = 'slave_{0}'.format(n)
    t.add_resource(ec2.Instance(
        "Ec2Instance{0}".format(n),
        ImageId = Ref(AmiId),
        InstanceType = Ref(InstanceType),
        KeyName = Ref(KeyName),
        SecurityGroupIds = Split(',', Ref(SecurityGroup)),
        SubnetId = Ref(SubnetA),
        Tags = Tags(Name = Join('', [Ref(InstanceName), name])),
    ))

print(t.to_json())
