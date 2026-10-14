# apps/core/tests/test_whatsapp.py
import os
import hmac
import hashlib
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.conf import settings
from apps.core.whatsapp import get_whatsapp_provider, TwilioProvider, DummyProvider
from apps.core.notifier import notificar_paciente, enviar_prueba
from apps.core.webhooks import WhatsAppWebhook
from apps.patients.models import PerfilPaciente
from apps.authentication.models import Register
from django.utils import timezone


class WhatsAppProviderTests(TestCase):
    @override_settings(WHATSAPP_ENABLED=False)
    def test_dummy_provider_when_disabled(self):
        provider = get_whatsapp_provider()
        self.assertIsInstance(provider, DummyProvider)
        self.assertTrue(provider.simulado)
        sid = provider.enviar_whatsapp("+573001234567", texto="hola")
        self.assertEqual(sid, "DUMMY_SID")

    @override_settings(WHATSAPP_ENABLED=True, TWILIO_SID="", TWILIO_TOKEN="", TWILIO_WHATSAPP_FROM="")
    def test_twilio_provider_missing_creds_raises(self):
        with self.assertRaises(RuntimeError):
            get_whatsapp_provider()

    @override_settings(WHATSAPP_ENABLED=True, TWILIO_SID="SID", TWILIO_TOKEN="TOKEN", TWILIO_WHATSAPP_FROM="whatsapp:+14155238886")
    @patch("apps.core.whatsapp.Client")
    def test_twilio_provider_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.sid = "SM123"
        mock_client.messages.create.return_value = mock_msg
        mock_client_class.return_value = mock_client

        provider = TwilioProvider()
        self.assertFalse(provider.simulado)
        sid = provider.enviar_whatsapp("+573001234567", texto="test")
        self.assertEqual(sid, "SM123")
        mock_client.messages.create.assert_called_once()

    @override_settings(WHATSAPP_ENABLED=True, TWILIO_SID="SID", TWILIO_TOKEN="TOKEN", TWILIO_WHATSAPP_FROM="whatsapp:+14155238886")
    @patch("apps.core.whatsapp.Client")
    def test_twilio_provider_exception(self, mock_client_class):
        from twilio.base.exceptions import TwilioRestException
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = TwilioRestException(400, "url", "msg", "code")
        mock_client_class.return_value = mock_client

        provider = TwilioProvider()
        with self.assertRaises(TwilioRestException):
            provider.enviar_whatsapp("+573001234567", texto="test")


class NotifierTests(TestCase):
    @override_settings(WHATSAPP_ENABLED=False, DEFAULT_FROM_EMAIL="test@example.com")
    @patch("apps.core.notifier.send_mail")
    @patch("apps.core.notifier.PatientService")
    def test_notificar_paciente_email_only(self, mock_service, mock_send):
        paciente = MagicMock()
        paciente.email = "a@b.com"
        paciente.nombre = "Juan"
        paciente.idUsuario = 1
        mock_service.return_value.get_preferences.return_value = ({"preferencias": {"canalNotificacion": "email"}}, None)

        ok = notificar_paciente(paciente, "Titulo", "Mensaje", "recordatorio_cita")
        self.assertTrue(ok)
        mock_send.assert_called_once()

    @override_settings(WHATSAPP_ENABLED=True, TWILIO_SID="SID", TWILIO_TOKEN="TOKEN", TWILIO_WHATSAPP_FROM="whatsapp:+14155238886")
    @patch("apps.core.notifier.PatientService")
    @patch("apps.core.notifier.get_whatsapp_provider")
    def test_notificar_paciente_whatsapp_fail_marks_false(self, mock_get_provider, mock_service):
        paciente = MagicMock()
        paciente.email = "a@b.com"
        paciente.nombre = "Juan"
        paciente.idUsuario = 1
        mock_service.return_value.get_preferences.return_value = ({"preferencias": {
            "canalNotificacion": "whatsapp",
            "whatsappConsentimiento": True,
            "numeroTelefonico": "+573001234567",
            "recibirRecordatorioCita": True,
        }}, None)

        mock_provider = MagicMock()
        mock_provider.simulado = False
        mock_provider.enviar_whatsapp.side_effect = Exception("Twilio error")
        mock_get_provider.return_value = mock_provider

        ok = notificar_paciente(paciente, "Titulo", "Mensaje", "recordatorio_cita")
        self.assertFalse(ok)


class WebhookSignatureTests(TestCase):
    def _make_signature(self, token, url, params):
        data = url + ''.join(f'{k}{v}' for k, v in sorted(params.items()))
        return hmac.new(token.encode(), data.encode(), hashlib.sha1).hexdigest()

    @override_settings(TWILIO_TOKEN="SECRET", TWILIO_WEBHOOK_URL="https://example.com/api/whatsapp/webhook/")
    def test_valid_signature(self):
        params = {"From": "whatsapp:+573001234567", "Body": "STOP"}
        sig = self._make_signature("SECRET", "https://example.com/api/whatsapp/webhook/", params)
        request = MagicMock()
        request.headers = {"X-Twilio-Signature": sig}
        request.POST = params
        request.META = {"REMOTE_ADDR": "1.2.3.4"}
        view = WhatsAppWebhook()
        self.assertTrue(view._verify_signature(sig, "https://example.com/api/whatsapp/webhook/", params))

    @override_settings(TWILIO_TOKEN="SECRET", TWILIO_WEBHOOK_URL="https://example.com/api/whatsapp/webhook/")
    def test_invalid_signature(self):
        request = MagicMock()
        request.headers = {"X-Twilio-Signature": "badsig"}
        request.POST = {"From": "whatsapp:+573001234567", "Body": "STOP"}
        view = WhatsAppWebhook()
        self.assertFalse(view._verify_signature("badsig", "https://example.com/api/whatsapp/webhook/", request.POST))