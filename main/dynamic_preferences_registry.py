# Preferences using django-dynamic-preferences

from dynamic_preferences import types
from dynamic_preferences.preferences import Section
from dynamic_preferences.registries import global_preferences_registry

general = Section('general')
template = Section('template')
webhook = Section('webhook')
google = Section('google')

###############################################################################
# General section

@global_preferences_registry.register
class CertNotice(types.BooleanPreference):
    section = general
    name = 'cert_notice'
    verbose_name = 'Enable sending cert expiration notices'
    default = False

@global_preferences_registry.register
class TitleHeader(types.StringPreference):
    section = general
    name = 'title_heading'
    default = 'BAMRU.net'

@global_preferences_registry.register
class WikiUrl(types.StringPreference):
    section = general
    name = 'wiki_url'
    default = 'https://wiki.bamru.net/mediawiki/index.php?title=Special:UserLogin&returnto=Main+Page'

###############################################################################
# Template section

@global_preferences_registry.register
class TitleHeader(types.LongStringPreference):
    section = template
    name = 'index'
    default = ''

###############################################################################
# Webhook section

@global_preferences_registry.register
class WebhookCalloutCreated(types.StringPreference):
    section = webhook
    name = 'callout_created'
    verbose_name = 'Webhook triggered on new callout'
    default = ''

###############################################################################
# Google section

@global_preferences_registry.register
class GoogleCredentials(types.LongStringPreference):
    section = google
    name = 'credentials'
    verbose_name = 'JSON credentials for service account'
    default = ''

@global_preferences_registry.register
class GoogleUser(types.StringPreference):
    section = google
    name = 'user'
    verbose_name = 'Delegated user on GSuite domain'
    default = ''

@global_preferences_registry.register
class DoGroup(types.StringPreference):
    section = google
    name = 'do_group'
    verbose_name = 'Google group to hold DO/AHCs'
    default = ''

@global_preferences_registry.register
class CalendarIdPublic(types.StringPreference):
    section = google
    name = 'calendar_id_public'
    verbose_name = 'Google calendar ID - public'
    default = ''

@global_preferences_registry.register
class CalendarIdPrivate(types.StringPreference):
    section = google
    name = 'calendar_id_private'
    verbose_name = 'Google calendar ID - private'
    default = ''

@global_preferences_registry.register
class FirebaseCredentials(types.LongStringPreference):
    section = google
    name = 'firebase_credentials'
    verbose_name = 'JSON credentials for firebase account'
    default = ''
