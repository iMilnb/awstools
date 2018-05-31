### Disposable and usable testing environment

The goal of this [Terraform][1] definition is to create an on-demand, disposable working environment within minutes in _AWS EC2_. I tried to make it as generic as possible so anyone could easily adapt it to its needs.

It setups a single instance whose parameters are recorded in the `variables.tf` file.

Once fired up, the instance is provisionned using [Ansible][2].  
I used my [own Ansible "essentials" playbook available here on GitHub][3] but you can obviously use yours simply by modifying the `playbook` and `extra_vars` variables in the `variables.tf` file.

Inspired from:

* https://alex.dzyoba.com/blog/terraform-ansible/
* https://github.com/dzeban/c10k/tree/master/infrastructure
* https://github.com/terraform-community-modules/tf_aws_ec2_instance

[1]: https://terraform.io
[2]: https://ansible.com
[3]: https://github.com/iMilnb/playbooks/tree/master/single
