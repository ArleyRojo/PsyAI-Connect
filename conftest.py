import pytest
from rest_framework.test import APIRequestFactory


class SessionRequestFactory(APIRequestFactory):
    def generic(self, *args, **kwargs):
        from django.contrib.sessions.backends.db import SessionStore

        request = super().generic(*args, **kwargs)
        request.session = SessionStore()
        return request


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Match the documented test setup; repository/view tests may use SQLite."""
    pass


# ── Reusable fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def rf():
    return SessionRequestFactory()


@pytest.fixture
def db_user(django_user_model):
    """Create a plain patient user in the test DB."""
    return django_user_model.objects.create_user(
        email="patient@test.com",
        nombre="Test Patient",
        password="TestPass123",
        rol="paciente",
    )



