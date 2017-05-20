Starts an AWS console from the shell based on cross account roles.
This script is an updated and cleaner version of the one from AWS:
https://aws.amazon.com/blogs/security/how-to-enable-cross-account-access-to-the-aws-management-console/
and this `botocore` version:
https://gist.githubusercontent.com/garnaat/10682964/raw/ef1caa152c006e33b54c0be8226f31ba35db331e/gistfile1.py

It uses an `awsaccounts` JSON file with the format:

```
{
    "thirdpartyaccount": {
        "account": "981036328202",
        "role": "ThirdParty",
        "external-id": "123456789"
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
* Direct account access using `awscli` profiles

All with or without MFA (while enabling MFA is highly recommanded).

You may give a path to a preferred path using the `--awsaccounts=` parameter.
If the role uses a MFA device, specify it with the `--mfa` parameter and the
`mfa` parameter must be associated with the target in the `awsaccounts` file,
its value is the MFA device serial number.

```
Usage:
  kriskross.py <target> [--awsaccounts=<file> --mfa=<token>]
```
