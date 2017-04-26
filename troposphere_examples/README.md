* `ec2instance.py`: deploys `n` _EC2_ instances
* `asg.py`: a very simple _AutoScaling Group_ template

Usage:

* Generate `cf-foo.json`:

```sh
$ python ec2instance.py 3 > cf-ec2instances.json
```

* Write the parameters file:

```json
[
	{
		"ParameterKey": "InstanceType",
		"ParameterValue": "t2.micro",
		"UsePreviousValue": false
	},
	{
		"ParameterKey": "AmiId",
		"ParameterValue": "ami-00000000",
		"UsePreviousValue": false
	},
	{
		"ParameterKey": "KeyName",
		"ParameterValue": "mykey-eu-central-1",
		"UsePreviousValue": false
	},
	{
		"ParameterKey": "SecurityGroup",
		"ParameterValue": "sg-00000000,sg-11111111",
		"UsePreviousValue": false
	},
	{
		"ParameterKey": "SubnetA",
		"ParameterValue": "subnet-00000000",
		"UsePreviousValue": false
	},
	{
		"ParameterKey": "InstanceName",
		"ParameterValue": "my_test_instance_",
		"UsePreviousValue": false
	}
]
```

Deploy the stack on `CloudFormation`

```sh
$ aws cloudformation create-stack --stack-name mystack --parameters file://cf-ec2instances.params --template-body file://cf-ec2instances.json
```
