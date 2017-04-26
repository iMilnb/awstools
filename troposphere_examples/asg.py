from troposphere import Template, Ref, Parameter, Tags
from troposphere.autoscaling import LaunchConfiguration, AutoScalingGroup, Tag

t = Template()

params = {
    'AmiId': 'Baked AMI Id',
    'InstanceName': 'Name tag of the instance',
    'SecurityGroup': 'Security Group' ,
    'KeyName': 'SSH Key Name' ,
    'InstanceType': 'Instance Type',
    'EnvType': 'test',
    'ScaleCapacity': 'Number of api servers to run',
    'SubnetA': 'ASG Subnet A'
}

for p in params.keys():
    vars()[p] = t.add_parameter(Parameter(
        p,
        Type = "String",
        Description = params[p]
    ))

LaunchConfig = t.add_resource(LaunchConfiguration(
    "LaunchConfiguration",
    ImageId = Ref(AmiId),
    SecurityGroups = [Ref(SecurityGroup)],
    KeyName = Ref(KeyName),
    InstanceType = Ref(InstanceType)
))

t.add_resource(AutoScalingGroup(
    "AutoscalingGroup",
    Tags=[
        Tag("Environment", Ref(EnvType), True),
        Tag("Name", Ref(InstanceName), True)
    ],
    DesiredCapacity = Ref(ScaleCapacity),
    LaunchConfigurationName=Ref(LaunchConfig),
    MinSize = Ref(ScaleCapacity),
    MaxSize = Ref(ScaleCapacity),
    VPCZoneIdentifier=[Ref(SubnetA)],
))


print(t.to_json())
