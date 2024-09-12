import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.messaging import AndroidConfig, Aps, ApsAlert, APNSConfig, Message, Notification, WebpushConfig
from fcm_django.models import FCMDevice
from django.conf import settings
from dynamic_preferences.registries import global_preferences_registry
import json
import requests

import logging
logger = logging.getLogger(__name__)

EXPO_PUSH_ROOT = 'https://exp.host/--/api/v2/push/'
EXPO_SEND = EXPO_PUSH_ROOT + 'send'
EXPO_ID_PREFIX = 'ExponentPushToken'

def generate_push_message_firebase(
        title, body, data=None, channel=None, critical=False):
    data['title'] = title
    data['body'] = body
    if channel:
        data['channel'] = channel
    if critical:
        data['critical'] = '1'
    for k in data:
        data[k] = str(data[k])

    # apns
    alert = messaging.ApsAlert(title = title, body = body)
    aps = messaging.Aps(
        alert = alert,
        badge = 1,
        content_available = True,
        mutable_content = True,
    )
    payload = messaging.APNSPayload(aps)
    logger.info('{}, {}, {}'.format(title, body, data))
    m=Message(
        # notification = messaging.Notification(title=title, body=body),
        data = data,
        android = messaging.AndroidConfig(priority="high"),
        apns = messaging.APNSConfig(headers={"apns-priority": "10"}, payload=payload),
        webpush = messaging.WebpushConfig(headers={"Urgency": "high"}),
    )
    return m

def send_push_message_devices_firebase(devices, message):
    response = devices.send_message(message)
    logger.info(response)
    logger.info('{} success, {} failure'.format(
        response.response.success_count, response.response.failure_count))
    ids = []
    for r in response.response.responses:
        if r.success:
            ids.append(r.message_id)
        else:
            logger.error(r.exception)
    logger.info(ids)
    return response


def send_push_message_firebase(title, body, data=None,
                               member_ids=None, channel=None, critical=False):
    m = generate_push_message_firebase(title, body, data, channel, critical)
    devices = FCMDevice.objects.exclude(
        registration_id__startswith=EXPO_ID_PREFIX)
    if member_ids is not None:
        devices = devices.filter(user_id__in=member_ids)
    send_push_message_devices_firebase(devices, m)

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
                message['sound'] = {
                    'critical': True,
                    'name': 'default',
                    'volume': 1,
                }
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

def load_firebase():
    if firebase_admin._apps:
        logger.info('firebase already loaded')
        return True
    global_preferences = global_preferences_registry.manager()
    service_account_json = global_preferences['google__firebase_credentials']
    if not service_account_json:
        logger.info('no firebase credentials available')
        return False
    try:
        service_account_info = json.loads(service_account_json)
    except json.decoder.JSONDecodeError as e:
        logger.info("Google credentials json parse error: " + str(e))
        return False
    creds = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(creds)
    logger.info('firebase loaded')
    return True


def send_push_message(title, body, data=None,
                      member_ids=None, channel=None, critical=False):
    if body is None:
        body = ''
    if data is None:
        data = {'title': title, 'body': body}
    if len(body) > 120:
        body = body[:119] + '…'
    logger.info('Sending push message: {}: "{}" filtered to {}'.format(title, body, sorted(member_ids)))

    sent = False
    if load_firebase():
        send_push_message_firebase(title, body, data, member_ids, channel, critical)
        sent = True
    if settings.EXPO_APP:
        send_push_message_expo(title, body, data, member_ids, channel, critical)
        sent = True
    if not sent:
        logger.info('Skipping push message for "{}"'.format(title))
