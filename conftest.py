import pytest


@pytest.fixture(autouse=True)
def _use_sqlite_for_tests(settings):
    """Override MySQL with in-memory SQLite for all tests."""
    settings.DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
    settings.DEBUG = False
    settings.ALLOWED_HOSTS = ["*"]
