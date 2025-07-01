from rest_framework.renderers import JSONRenderer
import requests

from main.models import Webhook

import logging
logger = logging.getLogger(__name__)

def trigger_webhook_url(url, data):
    session = requests.Session()
    session.headers.update({
        'accept': 'application/json',
        'accept-encoding': 'gzip, deflate',
        'content-type': 'application/json',
    })
    json_data = JSONRenderer().render(data)
    response = session.post(url, data=json_data)
    message = '{} -> {}: {}'.format(url, response.status_code, response.text)
    if response.ok:
        logger.info(message)
    else:
        logger.error(message)

def trigger_webhook(name, data):
    for webhook in Webhook.objects.filter(hook=name):
        try:
            trigger_webhook_url(webhook.url, data)
        except Exception as e:
            logger.error(str(e))
