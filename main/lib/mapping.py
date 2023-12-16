from django.conf import settings
import requests

GEOCODE_URL = 'https://maps.googleapis.com/maps/api/geocode/json'

def geocode(address, extra=None):
    session = requests.Session()
    url = '{}?key={}&address={}'.format(
        GEOCODE_URL, settings.GOOGLE_MAPS_API_KEY, address)
    if extra:
        url += '&' + extra
    response = session.get(url)
    if not response.ok:
        return None
    json = response.json()
    if ((results := json.get('results')) and
        (geometry := results[0].get('geometry')) and
        (location := geometry.get('location'))
        ):
        return (location.get('lat'), location.get('lng'))
    return None
