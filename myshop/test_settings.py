"""Credential-free isolated validation. Never loads the developer's .env."""
import os
from secrets import token_urlsafe

os.environ["BOOKSHOP_LOAD_DOTENV"] = "0"
os.environ["DJANGO_SECRET_KEY"] = token_urlsafe(48)
from .settings import *  # noqa: E402,F403

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = True
ALLOWED_HOSTS = ["testserver", "127.0.0.1", "localhost"]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / ".validation" / "demo.sqlite3",
    "TEST": {"NAME": ":memory:"},
}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "bookshop@example.test"
OPENAI_API_KEY = ""
STRIPE_SECRET_KEY = ""
STRIPE_PUBLISHABLE_KEY = ""
EXTERNAL_SERVICES_ENABLED = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_ROOT = BASE_DIR / ".validation" / "media"
STATIC_ROOT = BASE_DIR / ".validation" / "staticfiles"
CHAT_REQUESTS_PER_MINUTE = 10000
