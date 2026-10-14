import pytest
from django.test import RequestFactory
from apps.core.views import config_pago
from django.conf import settings

@pytest.mark.django_db
def test_config_pago_valid_url(settings):
    """Debe devolver la URL y configurada=True cuando la URL empieza por https://"""
    settings.PAGO_CUENTA_URL = "https://checkout.nequi.wompi.co/l/abc123"
    settings.PAGO_CUENTA_NOMBRE = "Nequi Test"
    factory = RequestFactory()
    request = factory.get("/api/config/pago/")
    response = config_pago(request)
    assert response.status_code == 200
    data = response.json()
    assert data["configurada"] is True
    assert data["url"] == "https://checkout.nequi.wompi.co/l/abc123"
    assert data["nombre"] == "Nequi Test"

@pytest.mark.django_db
def test_config_pago_empty_url(settings):
    """Debe devolver configurada=False cuando la URL está vacía"""
    settings.PAGO_CUENTA_URL = ""
    settings.PAGO_CUENTA_NOMBRE = ""
    factory = RequestFactory()
    request = factory.get("/api/config/pago/")
    response = config_pago(request)
    assert response.status_code == 200
    data = response.json()
    assert data["configurada"] is False
    assert data["url"] == ""
    assert data["nombre"] == ""

@pytest.mark.django_db
def test_config_pago_invalid_url_without_https(settings):
    """Debe devolver configurada=False cuando la URL no empieza por https://"""
    settings.PAGO_CUENTA_URL = "http://checkout.nequi.wompi.co/l/abc123"
    settings.PAGO_CUENTA_NOMBRE = "Test"
    factory = RequestFactory()
    request = factory.get("/api/config/pago/")
    response = config_pago(request)
    assert response.status_code == 200
    data = response.json()
    assert data["configurada"] is False
    assert data["url"] == ""
    assert data["nombre"] == ""