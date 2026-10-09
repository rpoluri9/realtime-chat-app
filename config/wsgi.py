"""WSGI entry point (plain HTTP fallback; Daphne/ASGI is preferred)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
