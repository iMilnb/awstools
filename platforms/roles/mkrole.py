# -*- coding: utf-8 -*-
"""This piece of code aims at simplifying IAM Roles creation
"""

import boto3
import sys

def usage():
    print(
        '{0} <role name> <trust policy JSON file> <policy document JSON>'
        .format(sys.argv[0])
    )
    sys.exit(2)


if len(sys.argv) < 4:
    usage()

name = sys.argv[1]
trust_policy_json = sys.argv[2]
policy_document_json = sys.argv[3]

# load the chosen trust policy and policy document
for json_file in ['trust_policy_json', 'policy_document_json']:
    with open(vars()[json_file], 'r') as f:
        vars()[json_file[:-5]] = f.read()

# connect to IAM
c = boto3.client('iam')

# create the instance profile
instance_profile = '{0}_instance_profile'.format(name)
r = c.create_instance_profile(
    InstanceProfileName = instance_profile
)

# create the role, associated with the trust policy, here assume EC2 role
role = '{0}_role'.format(name)
r = c.create_role(
    RoleName = role,
    AssumeRolePolicyDocument = trust_policy
)

# associate role and instance profile
r = c.add_role_to_instance_profile(
    InstanceProfileName = instance_profile,
    RoleName = role
)

# attach policy to role
r = c.put_role_policy(
    RoleName = role,
    PolicyName = '{0}_policy'.format(name),
    PolicyDocument = policy_document
)

print(
    'Role {0} created with Instance Profile {1}'
    .format(role, instance_profile)
)
