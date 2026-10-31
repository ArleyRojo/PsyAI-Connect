# apps/patients/tests/test_notificaciones.py
import pytest
from django.test import override_settings
from django.core import mail
from apps.patients.models import PerfilPaciente
from apps.authentication.models import Register
from apps.core.notifier import notificar_paciente
from apps.core.webhooks import WhatsAppWebhook
from unittest.mock import patch, MagicMock

@pytest.mark.django_db
def test_guardar_preferencias_con_validacion():
    user = Register.objects.create_user(email="p@test.com", password="x", rol="paciente", nombre="Pac")
    from apps.patients.serializers import PerfilPacienteSerializer
    ser = PerfilPacienteSerializer(data={"canalNotificacion":"whatsapp"})
    assert not ser.is_valid()
    assert "numeroTelefonico" in ser.errors
    ser = PerfilPacienteSerializer(data={
        "canalNotificacion":"whatsapp",
        "numeroTelefonico":"+573001234567",
        "whatsappConsentimiento":True,
    })
    assert ser.is_valid()

@pytest.mark.django_db
def test_notificar_paciente_email():
    user = Register.objects.create_user(email="p@test.com", password="x", rol="paciente", nombre="Pac")
    PerfilPaciente.objects.create(idPaciente=user, canalNotificacion="email")
    notificar_paciente(user, "Titulo", "Cuerpo", "mensaje_profesional")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "[PsyAI] Titulo"

@pytest.mark.django_db
def test_notificar_paciente_whatsapp_fallback():
    user = Register.objects.create_user(email="p@test.com", password="x", rol="paciente", nombre="Pac")
    PerfilPaciente.objects.create(idPaciente=user,
        canalNotificacion="ambos",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567")
    mock_prov = MagicMock()
    mock_prov.enviar_whatsapp.return_value = "SID123"
    with patch('apps.core.notifier.get_whatsapp_provider', return_value=mock_prov), \
            patch('apps.core.notifier.send_mail'):
        notificar_paciente(user, "T", "M", "recordatorio_cita")
    mock_prov.enviar_whatsapp.assert_called_once()

@pytest.mark.django_db
@override_settings(TWILIO_TOKEN="test-token", TWILIO_WEBHOOK_URL="http://testserver/api/whatsapp/webhook/")
def test_webhook_stop_desactiva_consentimiento(client):
    user = Register.objects.create_user(email="p@test.com", password="x", rol="paciente", nombre="Pac")
    PerfilPaciente.objects.create(idPaciente=user,
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
        canalNotificacion="ambos")
    
    # Mock the signature verification
    with patch.object(WhatsAppWebhook, '_verify_signature', return_value=True):
        resp = client.post("/api/whatsapp/webhook/",
            {"From":"whatsapp:+573001234567","Body":"STOP"},
            HTTP_X_TWILIO_SIGNATURE="dummy")
        assert resp.status_code == 200
    
    perfil = PerfilPaciente.objects.get(idPaciente=user)
    assert perfil.whatsappConsentimiento is False
    assert perfil.canalNotificacion == "email"
