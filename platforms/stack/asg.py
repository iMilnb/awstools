from troposphere import Template, Ref, Split, Parameter, Tags
from troposphere.autoscaling import LaunchConfiguration, AutoScalingGroup, Tag

t = Template()

params = {
    'AmiId': 'Baked AMI Id',
    'InstanceName': 'Name tag of the instance',
    'IamInstanceProfile': 'IAM Instance profile',
    'SecurityGroups': 'Security Groups' ,
    'KeyName': 'SSH Key Name' ,
    'InstanceType': 'Instance Type',
    'EnvType': 'test',
    'ScaleCapacity': 'Number of api servers to run',
    'Subnets': 'ASG Subnets'
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
    SecurityGroups = Split(',', Ref(SecurityGroups)),
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
    VPCZoneIdentifier=Split(',', Ref(Subnets)),
))


print(t.to_json())
