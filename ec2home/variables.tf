variable "aws_region" {
  default = "eu-west-1"
}

variable "aws_profile" {
}

variable "instance_name" {
  default = "homesweethome"
}

variable "ami_filter" {
  default = "debian-stretch-hvm-x86_64-gp2-*"
}

variable "ami_owner" {
  default = "379101102735"
}

variable "instance_type" {
  default = "t2.nano"
}

variable "ec2admin_user" {
  default = "admin"
}

variable "associate_public_ip" {
  default = true
}

variable "subnet_id" {
  default = ""
}

variable "keypair" {
  default = "myownawskey_eu-west-1"
}

variable "ssh_private_key" {
  default = "~/aws/keys/myownawskey_eu-west-1.pem"
}

variable "zone_id" {
  default = "Y1KK3AR0KND02Z"
}

variable "fqdn" {
  default = "homesweethome.mydomain.com."
}

variable "playbook" {
  default = "playbooks/single/essentials.yml"
}

variable "extra_vars" {
  default = "'myuser=username myghuser=UberUserFoo' -e @playbooks/group_vars/debian -e @addons.yml -e new=yes"
}
