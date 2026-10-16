from datetime import timedelta
from django.conf import settings

SESSION_DURATION = timedelta(days=2)
DEFAULT_LANGUAGE = "en"
OPENAI_MODEL = settings.OPENAI_MODEL
MAX_HISTORY = 7
MAX_BOOKS = 3
