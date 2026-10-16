"""Opt-in PostgreSQL checks against a dedicated disposable database only."""
import os
from .test_settings import *  # noqa: F403

validation_name = os.getenv("VALIDATION_DB_NAME", "bookshop_validation")
if not validation_name.startswith("bookshop_validation"):
    raise ValueError("Validation database names must start with bookshop_validation")
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": validation_name,
    "USER": os.getenv("VALIDATION_DB_USER", "postgres"),
    "HOST": os.getenv("VALIDATION_DB_HOST", ""),
    "TEST": {"NAME": "test_" + validation_name},
}}
