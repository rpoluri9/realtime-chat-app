"""Isolated settings for the test suite.

- File-based SQLite test database (no Postgres needed)
- In-memory channel layer (no Redis needed)
- Fast password hashing
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/tmp/chatapp_test_db.sqlite3",
    }
}

CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

MEDIA_ROOT = "/tmp/chatapp_test_media"
