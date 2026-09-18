import pytest
from django.test import Client


# ── Reusable fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def anon_client():
    """Unauthenticated Django test client."""
    return Client()


@pytest.fixture
def db_user(django_user_model):
    """Create a plain patient user in the test DB."""
    return django_user_model.objects.create_user(
        email="patient@test.com",
        nombre="Test Patient",
        password="TestPass123",
        rol="paciente",
    )


@pytest.fixture
def db_professional(django_user_model):
    """Create a professional user in the test DB."""
    return django_user_model.objects.create_user(
        email="pro@test.com",
        nombre="Test Pro",
        password="TestPass123",
        rol="profesional",
    )


@pytest.fixture
def db_admin(django_user_model):
    """Create an admin user in the test DB."""
    return django_user_model.objects.create_user(
        email="admin@test.com",
        nombre="Test Admin",
        password="TestPass123",
        rol="admin",
    )
