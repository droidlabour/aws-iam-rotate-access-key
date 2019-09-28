# aws-iam-key-rotate
Rotate AWS IAM Access Key across `120` Days

# Workflow
1) At `90` days create a second access key.
2) Send the new key to the owner of the account. The owners email address will be in the Owner Tag for the IAM account. (The email will state that the Owner has `30` days to implement the new key.)
3) At `14` and `21` days from the initial email Lambda will review the IAM accounts to see if the new keys are being used and that the old keys are not.
If the new keys are not being used a follow-up email will be sent reminding the IAM account owner that they have `16` days and `9` days left to start using the new key.
4) At `30` days from the initial email the old keys will be set to inactive.
5) At `60` days from the initial email the inactive keys will be deleted.
