provider "aws" {
  region = "${var.aws_region}"
  profile = "${var.aws_profile}"
}

data "aws_ami" "ami_type" {
  most_recent = true

  filter {
    name   = "name"
    values = ["${var.ami_filter}"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["${var.ami_owner}"]
}

resource "aws_security_group" "ssh_sg" {
  name = "inbound SSH"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags {
    Name = "allow_ssh"
  }
}

resource "aws_instance" "ec2_instance" {
  ami                         = "${data.aws_ami.ami_type.id}"
  instance_type               = "${var.instance_type}"
  subnet_id                   = "${var.subnet_id}"
  vpc_security_group_ids      = ["${aws_security_group.ssh_sg.id}"]
  key_name                    = "${var.keypair}"
  associate_public_ip_address = "${var.associate_public_ip}"
  count                       = 1

  tags {
    created_by = "terraform"
    Name = "${var.instance_name}"
  }

  provisioner "remote-exec" {
    inline = ["sudo apt-get -y install python"]

    connection {
      type        = "ssh"
      user        = "${var.ec2admin_user}"
      private_key = "${file(var.ssh_private_key)}"
    }
  }

  provisioner "local-exec" {
    command = "ansible-playbook -u ${var.ec2admin_user} -i '${self.public_ip},' --private-key ${var.ssh_private_key} -T 300 ${var.playbook} --extra-vars ${var.extra_vars}"
  }
}

resource "aws_route53_record" "instance" {
  zone_id = "${var.zone_id}"
  name    = "${var.fqdn}"
  type    = "A"
  ttl     = "300"
  records = ["${aws_instance.ec2_instance.public_ip}"]
}
