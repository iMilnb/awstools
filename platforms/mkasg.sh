#!/bin/sh

usage()
{
	echo "$0 -parc"
	echo "	-p run packer"
	echo "	-a execute all actions"
	echo "	-a create IAM roles"
	echo "	-a create CloudFormation stack"
	exit 2
}

flags=''

while [ $# -gt 0 ]; do
	case "$1" in
	-p) flags="${flags}p" ;;
	-a) flags="${flags}a" ;;
	-r) flags="${flags}r" ;;
	-c) flags="${flags}c" ;;
	*) usage ;;
	esac
	shift
done

. ./vars

case ${flags} in
# packer IAM
*a*|*p*)
	
	SGID=$(aws ec2 describe-security-groups --filters "Name=tag:Name, Values=${PKRSG}"| jq -r '.SecurityGroups[0].GroupId')
	SUBNETID=$(aws ec2 describe-subnets --filters "Name=tag:Name, Values=${PKRSUBNET}"|jq -r '.Subnets[0].SubnetId')
	
	cd packer && packer build \
		-var "username=${USER}" \
		-var "githubname=${GHUSER}" \
		-var "sgid=${SGID}" \
		-var "subnetid=${SUBNETID}" \
		-var "ami_basename=${AMI_BASENAME}" \
		basic.json
	;;
# role creation
*a*|*r*)
	cd roles
	# HOSTEDZONEID needs to be set in vars for RRset
	HOSTEDZONEID=$HOSTEDZONEID python mkrole.py \
		${ROLE} ${TRUST_POLICY} ${POLICY_DOCUMENT}
	;;
# CloudFormation stack creation
*a*|*c*)
	# get latest built AMI id
	AMIID=$(jq -r '.last_run_uuid as $uuid | .builds[] | select(.packer_run_uuid == $uuid) | .artifact_id' packer/manifest.json)
	INSTANCEPROFILE=$(aws iam list-instance-profiles-for-role --role-name "${ROLE}"|jq -r '.InstanceProfiles[].Arn')

	cd stack

	# generate JSON stack
	python asg.py > ${STACKNAME}.json
	# load stack parameters
	. ./params
	PARAMFILE="${STACKNAME}-parameters.json"
	echo "${PARAMS}" > "${PARAMFILE}"

	aws cloudformation create-stack --stack-name ${STACKNAME} --template-body file://${STACKNAME}.json --parameters file://${PARAMFILE}
	;;
*)
	usage
	;;
esac
