from firebase_admin.messaging import AndroidConfig, APNSConfig, Message, Notification, WebpushConfig
from fcm_django.models import FCMDevice
from django.conf import settings


def send_push_message(title, body, data=None, member_ids=None):
    if not settings.FIREBASE_APP:
        print('Skipping push message for "{}"'.format(title))
        return
    if data is None:
        data = {'title': title, 'body': body}
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
