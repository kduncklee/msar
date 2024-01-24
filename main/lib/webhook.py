from dynamic_preferences.registries import global_preferences_registry
from rest_framework.renderers import JSONRenderer
import json
import requests

import logging
logger = logging.getLogger(__name__)

def trigger_webhook(name, data):
    global_preferences = global_preferences_registry.manager()
    url = global_preferences['webhook__' + name]
    if not url:
        logger.info('Webhook {} not set, skipping'.format(name))
        return
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
