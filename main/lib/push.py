from firebase_admin.messaging import AndroidConfig, APNSConfig, Message, Notification, WebpushConfig
from fcm_django.models import FCMDevice
from django.conf import settings
import json
import requests

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

def send_push_message_expo(title, body, data=None, member_ids=None):
    devices = FCMDevice.objects.filter(registration_id__startswith=EXPO_ID_PREFIX)
    if member_ids is not None:
        devices = devices.filter(user_id__in=member_ids)
    if not devices:
        print('No Expo devices found')
        return
    message = {
        'to': [d.registration_id for d in devices],
        'title': title,
        'body': body,
        'data': data,
        'priority': 'high',
    }
    session = requests.Session()
    session.headers.update({
        'accept': 'application/json',
        'accept-encoding': 'gzip, deflate',
        'content-type': 'application/json',
    })
    response = session.post(EXPO_SEND, data=json.dumps(message))
    print(response)
    print(response.json())

def send_push_message(title, body, data=None, member_ids=None):
    if data is None:
        data = {'title': title, 'body': body}
    if len(body) > 120:
        body = body[:119] + '…'
    print('Sending push message: {}: "{}" filtered to {}'.format(title, body, member_ids))
    if settings.FIREBASE_APP:
        send_push_message_firebase(title, body, data, member_ids)
    elif settings.EXPO_APP:
        send_push_message_expo(title, body, data, member_ids)
    else:
        print('Skipping push message for "{}"'.format(title))
