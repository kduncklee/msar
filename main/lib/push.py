from firebase_admin.messaging import AndroidConfig, APNSConfig, Message, Notification, WebpushConfig
from fcm_django.models import FCMDevice
from django.conf import settings
import json
import requests

import logging
logger = logging.getLogger(__name__)

EXPO_PUSH_ROOT = 'https://exp.host/--/api/v2/push/'
EXPO_SEND = EXPO_PUSH_ROOT + 'send'
EXPO_ID_PREFIX = 'ExponentPushToken'

def send_push_message_firebase(title, body, data=None, member_ids=None):
    m=Message(
        notification = Notification(
            title=title, body=body,
            #image="url"
        ),
        data = data,
        android = AndroidConfig(priority="high"),
        apns = APNSConfig(headers={"apns-priority": "10"}),
        webpush = WebpushConfig(headers={"Urgency": "high"}),
    )
    devices = FCMDevice.objects.all()
    if member_ids is not None:
        devices = devices.filter(user_id__in=member_ids)
    devices.send_message(m)

def send_push_message_expo(title, body, data=None,
                           member_ids=None, channel=None, critical=False):
    expo_devices = FCMDevice.objects.filter(
        registration_id__startswith=EXPO_ID_PREFIX,
        active=True)
    if member_ids is not None:
        expo_devices = expo_devices.filter(user_id__in=member_ids)
    if not expo_devices:
        logger.info('No Expo devices found')
        return
    session = requests.Session()
    session.headers.update({
        'accept': 'application/json',
        'accept-encoding': 'gzip, deflate',
        'content-type': 'application/json',
    })
    critical_choices = [False]
    if critical:
        critical_choices.append(True)
    # Andoid and iOS may use different projects, so send separately.
    for device_type in ['ios', 'android']:
        for critical_choice in critical_choices:
            devices = expo_devices.filter(type=device_type)
            if critical:
                # The device_id field is now used to store if that device
                # wants to receive a notification on the critical channel.
                # Null indicates to send using normal methods.
                if critical_choice:
                    devices = devices.filter(device_id__isnull=False)
                else:
                    devices = devices.filter(device_id__isnull=True)
            if not devices:
                continue
            message = {
                'to': [d.registration_id for d in devices],
                'title': title,
                'body': body,
                'data': data,
                'priority': 'high',
            }
            if channel is not None:  # for Android
                if critical_choice:
                    message['channelId'] = channel + '-alarm'
                else:
                    message['channelId'] = channel
            if critical_choice:  # for iOS
                message['sound'] = {'critical':True}
            logger.info('{}, {}: {}'.format(device_type, critical, message['to']))
            response = session.post(EXPO_SEND, data=json.dumps(message))
            logger.info('{}: {}'. format(response, response.json()))
            if not response.ok:
                logger.error('Push error: ' + str(response.json()))
                # Try to send seperately
                for to in message['to']:
                    m = message.copy()
                    m['to'] = to
                    r = session.post(EXPO_SEND, data=json.dumps(m))
                    logger.info('{}, {}: {}'. format(to, r, r.json()))
                    if not r.ok:
                        logger.error('Single push error: ' + str(r.json()))

def send_push_message(title, body, data=None,
                      member_ids=None, channel=None, critical=False):
    if data is None:
        data = {'title': title, 'body': body}
    if len(body) > 120:
        body = body[:119] + '…'
    logger.info('Sending push message: {}: "{}" filtered to {}'.format(title, body, sorted(member_ids)))
    if settings.FIREBASE_APP:
        send_push_message_firebase(title, body, data, member_ids)
    elif settings.EXPO_APP:
        send_push_message_expo(title, body, data, member_ids, channel, critical)
    else:
        logger.info('Skipping push message for "{}"'.format(title))
