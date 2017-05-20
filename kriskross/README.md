Starts an AWS console from the shell based on cross account roles.
This script is an updated and cleaner version of the one from AWS:
https://aws.amazon.com/blogs/security/how-to-enable-cross-account-access-to-the-aws-management-console/
and this `botocore` version:
https://gist.githubusercontent.com/garnaat/10682964/raw/ef1caa152c006e33b54c0be8226f31ba35db331e/gistfile1.py  
It adds key features like _profile_ and [MFA][2] support.

It uses an `~/.awsaccounts` JSON file with the format:

```
{
    "thirdpartyaccount": {
        "account": "981036328202",
        "role": "ThirdParty",
        "external-id": "123456789"
    },
    "thirdpartyaccountwithMFA": {
        "account": "123036328892",
        "role": "ThirdParty",
        "external-id": "123456789"
        "mfa": "arn:aws:iam::225011332614:mfa/MySelf"
    },
    "childaccount": {
        "account": "287487895991",
        "role": "ChildAdmin",
    },
    "myownaccount": {
        "account": "636487856791",
        "role": "MFAAdmin",
        "mfa": "arn:aws:iam::225011332614:mfa/MySelf"
    },
    "myotheraccount": {
        "profile": "othercompany",
        "account": "123468236778",
        "role": "MFAAdmin",
        "mfa": "arn:aws:iam::678067632434:mfa/MySelf"
    }
}
```

There are many possible combinations:

* Direct, own account access, by creating a cross acount role with the local account id
* Child account, by enabling cross account access
* Third party account using an external id
* Direct account access using [awscli][1] profiles

All with or without MFA (while enabling MFA is highly recommanded).

You may give an alternative path and name for the account properties file using the
`--awsaccounts=` parameter.  
If the role uses a MFA device, specify it with the `--mfa` parameter along with a `mfa` key associated with the target in the `awsaccounts` file which value is the MFA device serial number.

```
Usage:
  kriskross.py <target> [--awsaccounts=<file> --mfa=<token>]
```

[1]: https://github.com/aws/aws-cli
[2]: https://aws.amazon.com/iam/details/mfa/