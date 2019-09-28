import os
import logging
from datetime import datetime

import boto3

log = logging.getLogger()
log.setLevel(logging.INFO)


def notify(body, subject):
    client = boto3.client('sns')
    r = client.publish(
        TopicArn=os.getenv('SNS_TOPIC_ARN'),
        Message=body,
        Subject=subject
    )
    log.info('SNS notified with MessageId %s', r['MessageId'])


def key_age(key_created_date):
    tz_info = key_created_date.tzinfo
    age = datetime.now(tz_info) - key_created_date
    log.info('key age %s', age)

    key_age_str = str(age)
    if 'days' not in key_age_str:
        return 0

    return int(key_age_str.split(',')[0].split(' ')[0])


def is_access_key_ever_used(client, access_key):
    x = client.get_access_key_last_used(AccessKeyId=access_key)
    if 'LastUsedDate' in x['AccessKeyLastUsed'].keys():
        log.info('Access key %s has been used', access_key)
        return True
    else:
        log.info('Access key %s has never been used', access_key)
        return False


def get_owner_email(client, username):
    meta = client.list_user_tags(UserName=username)['Tags']
    for i in meta:
        if i['Key'] == 'Owner':
            log.info('Email for user %s is %s', username, i['Value'])
            return i['Value']


def lambda_handler(event, context):
    log.info('RotateAccessKey: starting...')
    EXPIRE_OLD_ACCESS_KEY_AFTER = 30
    DELETE_OLD_ACCESS_KEY_AFTER = 60
    CREATE_NEW_ACCESS_KEY_AFTER = 90
    NEW_ACCESS_KEY_NOTIFY_WINDOW = [14, 21]
    client = boto3.client('iam')

    data = client.list_users()
    log.info(data)

    for user in data['Users']:
        username = user['UserName']
        log.info('username %s', username)
        email = get_owner_email(client, username)
        if not email:
            logging.info('Skipping: Email not found for user %s', username)
            continue

        access_keys = client.list_access_keys(UserName=username)['AccessKeyMetadata']
        if len(access_keys) == 1 and key_age(access_keys[0]['CreateDate']) == CREATE_NEW_ACCESS_KEY_AFTER:
            log.info('Creating a new access key')
            x = client.create_access_key(UserName=username)['AccessKey']
            access_key, secret_access_key = x['AccessKeyId'], x['SecretAccessKey']
            body = 'Access Key: ' + access_key + '\n' + 'Secret Key: ' + secret_access_key + '\n'
            subject = 'New access keys created for user ' + username
            notify(body, subject)
        elif len(access_keys) == 2:
            log.info('Screening existing access keys for user %s', username)
            younger_access_key = access_keys[0]
            younger_access_key_age = key_age(younger_access_key['CreateDate'])

            if not is_access_key_ever_used(client, younger_access_key['AccessKeyId']):
                if younger_access_key_age in NEW_ACCESS_KEY_NOTIFY_WINDOW:
                    old_key_expire_timeout = EXPIRE_OLD_ACCESS_KEY_AFTER - younger_access_key_age
                    logging.info('User %s has %s days to use this new key %s', username, old_key_expire_timeout, younger_access_key['AccessKeyId'])
                    body = 'You have ' + str(old_key_expire_timeout) + ' days to use the new access keys.'
                    subject = 'Please use the new access keys for ' + username
                    notify(body, subject)

            if younger_access_key_age == EXPIRE_OLD_ACCESS_KEY_AFTER:
                logging.info('Deactivating old key %s for user %s', access_keys[1]['AccessKeyId'], username)
                client.update_access_key(
                    UserName=username,
                    AccessKeyId=access_keys[1]['AccessKeyId'],
                    Status='Inactive'
                )
            elif younger_access_key_age == DELETE_OLD_ACCESS_KEY_AFTER:
                logging.info('Deleting old key %s for user %s', access_keys[1]['AccessKeyId'], username)
                client.delete_access_key(
                    UserName=username,
                    AccessKeyId=access_keys[1]['AccessKeyId']
                )

    log.info('Completed')
    return 0


# if __name__ == "__main__":
#    event = 1
#    context = 1
#    lambda_handler(event, context)
