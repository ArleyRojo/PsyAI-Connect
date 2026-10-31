import json
from unittest.mock import patch

import pytest
from django.test import Client, RequestFactory

from apps.authentication.models import Register
from apps.core.views import notificacion_prueba
from apps.patients.models import PerfilPaciente


@pytest.fixture
def paciente(db):
    user = Register.objects.create_user(
        email="prueba-paciente@example.com",
        nombre="Paciente de prueba",
        password="StrongPass123!",
        rol="paciente",
    )
    PerfilPaciente.objects.create(
        idPaciente=user,
        numeroTelefonico="+573001234567",
        whatsappConsentimiento=True,
        canalNotificacion="whatsapp",
    )
    return user


def _request_with_session(path, data, user_id=None):
    request = RequestFactory().post(path, data=json.dumps(data), content_type="application/json")
    request.session = {"idUsuario": user_id} if user_id else {}
    return request


@pytest.mark.django_db
def test_prueba_requiere_sesion():
    response = notificacion_prueba(_request_with_session("/api/notificaciones/probar/", {}))
    assert response.status_code == 401


@pytest.mark.django_db
def test_whatsapp_debe_coincidir_con_numero_consentido(paciente):
    request = _request_with_session(
        "/api/notificaciones/probar/", {"canal": "whatsapp", "numero": "+573009999999"}, paciente.idUsuario
    )
    response = notificacion_prueba(request)
    assert response.status_code == 403


@pytest.mark.django_db
def test_whatsapp_envia_solo_al_numero_propio_consentido(paciente):
    request = _request_with_session(
        "/api/notificaciones/probar/", {"canal": "whatsapp", "numero": "3001234567"}, paciente.idUsuario
    )
    with patch("apps.core.notifier.enviar_prueba", return_value=(True, "enviado")) as send:
        response = notificacion_prueba(request)
    assert response.status_code == 200
    assert json.loads(response.content)["success"] is True
    send.assert_called_once_with("+573001234567")


@pytest.mark.django_db
def test_endpoint_requiere_csrf_en_cliente_real(paciente):
    client = Client(enforce_csrf_checks=True)
    session = client.session
    session["idUsuario"] = paciente.idUsuario
    session["rol"] = "paciente"
    session.save()
    response = client.post(
        "/api/notificaciones/probar/",
        data=json.dumps({"canal": "email"}),
        content_type="application/json",
    )
    assert response.status_code == 403
