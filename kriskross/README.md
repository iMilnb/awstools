Starts an AWS console from the shell based on cross account roles.
This script is an updated and cleaner version of the one from AWS:
https://aws.amazon.com/blogs/security/how-to-enable-cross-account-access-to-the-aws-management-console/
and this `botocore` version:
https://gist.githubusercontent.com/garnaat/10682964/raw/ef1caa152c006e33b54c0be8226f31ba35db331e/gistfile1.py

It uses an `awsaccounts` _JSON_ file with the format:

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
    }
}
```

You may give a path to a preferred path.

The first parameter specifies the `target` from the _JSON_ file.
