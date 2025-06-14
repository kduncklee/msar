"""
WSGI config for bamru_net project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bamru_net.settings")

application = get_wsgi_application()
