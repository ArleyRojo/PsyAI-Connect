# apps/patients/tests/test_cita_factura_notificaciones.py
from unittest.mock import patch, MagicMock

import pytest
from django.core import mail
from django.test import override_settings

from apps.authentication.models import Register
from apps.patients.models import PerfilPaciente


def _make_patient(email="p@test.com", nombre="Paciente", **perfil_kwargs):
    user = Register.objects.create_user(
        email=email, password="x", rol="paciente", nombre=nombre,
    )
    defaults = dict(
        canalNotificacion="email",
        whatsappConsentimiento=False,
        numeroTelefonico=None,
        recibirRecordatorioCita=True,
        recibirConfirmacion=True,
        recibirMensajePro=True,
    )
    defaults.update(perfil_kwargs)
    PerfilPaciente.objects.create(idPaciente=user, **defaults)
    return user


@pytest.mark.django_db
def test_cita_paciente_canal_email_ruta_por_notificar_paciente():
    user = _make_patient(canalNotificacion="email")
    with patch("apps.scheduling.services.notificar_paciente") as mock_notify:
        from apps.scheduling.services import AppointmentMailService
        AppointmentMailService.send_cita_notificacion(
            recipient_email=user.email,
            titulo="Nueva cita",
            mensaje="Tienes una cita",
            fecha="2027-06-15",
            hora="10:00",
            recipient_user_id=user.idUsuario,
        )
    mock_notify.assert_called_once()
    _, args, kwargs = mock_notify.mock_calls[0]
    assert args[0] == user  # paciente
    assert kwargs["plantilla_email"] == "emails/cita_notificacion.html"
    assert "params_email" in kwargs
    # No correo directo: se respeta el canal vía notificar_paciente
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_cita_paciente_canal_whatsapp_no_envia_correo_directo():
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    with patch("apps.scheduling.services.notificar_paciente") as mock_notify:
        from apps.scheduling.services import AppointmentMailService
        AppointmentMailService.send_cita_notificacion(
            recipient_email=user.email,
            titulo="Nueva cita",
            mensaje="Tienes una cita",
            recipient_user_id=user.idUsuario,
        )
    mock_notify.assert_called_once()
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_cita_paciente_canal_ninguno_no_envia():
    user = _make_patient(canalNotificacion="ninguno")
    with patch("apps.scheduling.services.notificar_paciente") as mock_notify:
        from apps.scheduling.services import AppointmentMailService
        mock_notify.return_value = False
        AppointmentMailService.send_cita_notificacion(
            recipient_email=user.email,
            titulo="Nueva cita",
            mensaje="Tienes una cita",
            recipient_user_id=user.idUsuario,
        )
    mock_notify.assert_called_once()
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_cita_profesional_sin_recipient_user_id_no_ruta_por_notificar_paciente():
    # El profesional no es paciente: no debe pasar por notificar_paciente.
    user = _make_patient()
    with patch("apps.scheduling.services.notificar_paciente") as mock_notify:
        from apps.scheduling.services import AppointmentMailService
        AppointmentMailService.send_cita_notificacion(
            recipient_email="prof@test.com",
            titulo="Nueva solicitud",
            mensaje="Un paciente solicitó cita",
        )
    mock_notify.assert_not_called()


@pytest.mark.django_db
def test_factura_paciente_canal_email_ruta_por_notificar_paciente():
    user = _make_patient(canalNotificacion="email")
    with patch("apps.billing.services.notificar_paciente") as mock_notify:
        from apps.billing.services import InvoiceMailService
        InvoiceMailService.send_factura_notificacion(
            recipient_email=user.email,
            titulo="Pago registrado",
            mensaje="Pago recibido",
            id_factura=10,
            nombre_paciente=user.nombre,
            monto=100000,
            paciente_user=user,
        )
    mock_notify.assert_called_once()
    _, args, kwargs = mock_notify.mock_calls[0]
    assert args[0] == user
    assert args[3] == "factura"  # tipo
    assert kwargs["plantilla_email"] == "emails/factura_notificacion.html"
    assert "params_email" in kwargs
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_factura_paciente_canal_whatsapp_no_envia_correo_directo():
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    with patch("apps.billing.services.notificar_paciente") as mock_notify:
        from apps.billing.services import InvoiceMailService
        InvoiceMailService.send_factura_notificacion(
            recipient_email=user.email,
            titulo="Pago registrado",
            mensaje="Pago recibido",
            id_factura=10,
            nombre_paciente=user.nombre,
            monto=100000,
            paciente_user=user,
        )
    mock_notify.assert_called_once()
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_factura_paciente_canal_ninguno_no_envia():
    user = _make_patient(canalNotificacion="ninguno")
    with patch("apps.billing.services.notificar_paciente") as mock_notify:
        from apps.billing.services import InvoiceMailService
        mock_notify.return_value = False
        InvoiceMailService.send_factura_notificacion(
            recipient_email=user.email,
            titulo="Pago registrado",
            mensaje="Pago recibido",
            id_factura=10,
            nombre_paciente=user.nombre,
            monto=100000,
            paciente_user=user,
        )
    mock_notify.assert_called_once()
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_factura_sin_paciente_user_no_ruta_por_notificar_paciente():
    # Destinatario sin vinculación a paciente (ej. profesional en anulación):
    # correo directo, sin notificar_paciente.
    user = _make_patient()
    with patch("apps.billing.services.notificar_paciente") as mock_notify:
        from apps.billing.services import InvoiceMailService
        InvoiceMailService.send_factura_notificacion(
            recipient_email="prof@test.com",
            titulo="Factura anulada",
            mensaje="Anulada",
            id_factura=10,
        )
    mock_notify.assert_not_called()


# ───────── Nuevo: Twilio nunca recibe una ruta .html como content_sid ─────────

@patch("apps.core.notifier.get_whatsapp_provider")
@pytest.mark.django_db
def test_cita_canal_whatsapp_twilio_recibe_sid_no_html(mock_get_provider):
    """Cita con canal whatsapp: a Twilio no le llega una ruta .html como content_sid."""
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    provider = MagicMock()
    provider.simulado = False
    provider.enviar_whatsapp.return_value = "SID_X"
    mock_get_provider.return_value = provider

    with patch("apps.core.notifier.send_mail"):
        from apps.core.notifier import notificar_paciente
        notificar_paciente(
            user, "Nueva cita", "Tienes una cita", "cita_general",
            plantilla_email="emails/cita_notificacion.html",
            params_email={"titulo": "Nueva cita"},
        )

    provider.enviar_whatsapp.assert_called_once()
    call_kwargs = provider.enviar_whatsapp.call_args.kwargs
    content_sid = call_kwargs.get("plantilla")
    # Nunca debe llegar una ruta .html como content_sid (texto libre o SID real).
    assert not (isinstance(content_sid, str) and content_sid.endswith(".html"))


@patch("apps.core.notifier.get_whatsapp_provider")
@pytest.mark.django_db
def test_ambos_canal_whatsapp_twilio_recibe_sid_no_html(mock_get_provider):
    """Canal ambos con whatsapp: a Twilio no le llega una ruta .html como content_sid."""
    user = _make_patient(
        canalNotificacion="ambos",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    provider = MagicMock()
    provider.simulado = False
    provider.enviar_whatsapp.return_value = "SID_Y"
    mock_get_provider.return_value = provider

    with patch("apps.core.notifier.send_mail"):
        from apps.core.notifier import notificar_paciente
        notificar_paciente(
            user, "T", "M", "factura",
            plantilla_email="emails/factura_notificacion.html",
            params_email={"id_factura": 5},
        )

    provider.enviar_whatsapp.assert_called_once()
    call_kwargs = provider.enviar_whatsapp.call_args.kwargs
    content_sid = call_kwargs.get("plantilla")
    # Nunca debe llegar una ruta .html como content_sid (texto libre o SID real).
    assert not (isinstance(content_sid, str) and content_sid.endswith(".html"))


@patch("apps.core.notifier.get_whatsapp_provider")
@pytest.mark.django_db
@override_settings(TWILIO_TPL_FACTURA="FAKE_SID_FACTURA")
def test_factura_con_sid_configurado_se_pasa_a_twilio(mock_get_provider):
    """Cuando existe TWILIO_TPL_FACTURA, se pasa como plantilla a Twilio (no es .html)."""
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    provider = MagicMock()
    provider.simulado = False
    provider.enviar_whatsapp.return_value = "SID_FACT"
    mock_get_provider.return_value = provider

    with patch("apps.core.notifier.send_mail"):
        from apps.core.notifier import notificar_paciente
        notificar_paciente(user, "Factura", "Pago pendiente", "factura")

    provider.enviar_whatsapp.assert_called_once()
    call_kwargs = provider.enviar_whatsapp.call_args.kwargs
    assert call_kwargs.get("plantilla") == "FAKE_SID_FACTURA"


@patch("apps.core.notifier.get_whatsapp_provider")
@pytest.mark.django_db
def test_cita_canal_whatsapp_pasa_params_email_no_params_whatsapp(mock_get_provider):
    """El contexto HTML (params_email) no se envía como content_variables de Twilio."""
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    provider = MagicMock()
    provider.simulado = False
    provider.enviar_whatsapp.return_value = "SID_Z"
    mock_get_provider.return_value = provider

    with patch("apps.core.notifier.send_mail"):
        from apps.core.notifier import notificar_paciente
        notificar_paciente(
            user, "T", "M", "factura",
            plantilla_email="emails/factura_notificacion.html",
            params_email={"id_factura": 5, "monto_total": "100.000"},
        )

    provider.enviar_whatsapp.assert_called_once()
    call_kwargs = provider.enviar_whatsapp.call_args.kwargs
    # params_whatsapp no fue provisto -> None (texto libre, sin variables de plantilla)
    assert call_kwargs.get("params") is None


# ───────── Nuevo: tipo factura sin SID -> texto libre con warning ─────────

@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.logger")
@pytest.mark.django_db
@override_settings(TWILIO_TPL_FACTURA="")
def test_factura_sin_sid_envia_texto_libre_y_loggea_warning(mock_logger, mock_get_provider):
    """Factura sin SID de Twilio: usa texto libre y registra advertencia."""
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    provider = MagicMock()
    provider.simulado = False
    provider.enviar_whatsapp.return_value = "SID_FREE"
    mock_get_provider.return_value = provider

    with patch("apps.core.notifier.send_mail"):
        from apps.core.notifier import notificar_paciente
        notificar_paciente(user, "Factura", "Pago pendiente", "factura")

    provider.enviar_whatsapp.assert_called_once()
    call_kwargs = provider.enviar_whatsapp.call_args.kwargs
    assert call_kwargs.get("plantilla") is None  # texto libre (body)
    assert call_kwargs.get("texto") == "Pago pendiente"
    # Se registró el warning de plantilla ausente
    assert mock_logger.warning.called
    warning_msg = mock_logger.warning.call_args[0][0]
    assert "plantilla" in warning_msg.lower() or "24 h" in warning_msg


# ───────── Nuevo: canal ninguno no envía correo ni whatsapp (citas y facturas) ─

@patch("apps.core.notifier.get_whatsapp_provider")
@pytest.mark.django_db
def test_canal_ninguno_no_envia_correo_ni_whatsapp_cita(mock_get_provider):
    user = _make_patient(canalNotificacion="ninguno")
    with patch("apps.core.notifier.send_mail") as mock_send:
        from apps.core.notifier import notificar_paciente
        ok = notificar_paciente(user, "Cita", "Tienes cita", "cita_general")
    assert ok is False
    mock_send.assert_not_called()
    mock_get_provider.assert_not_called()


@patch("apps.core.notifier.get_whatsapp_provider")
@pytest.mark.django_db
def test_canal_ninguno_no_envia_correo_ni_whatsapp_factura(mock_get_provider):
    user = _make_patient(canalNotificacion="ninguno")
    with patch("apps.core.notifier.send_mail") as mock_send:
        from apps.core.notifier import notificar_paciente
        ok = notificar_paciente(user, "Factura", "Pago pendiente", "factura")
    assert ok is False
    mock_send.assert_not_called()
    mock_get_provider.assert_not_called()


# ───────── Nuevo: respaldo por correo al faltar consentimiento/teléfono (whatsapp) ─

@patch("apps.core.notifier.get_whatsapp_provider")
@pytest.mark.django_db
@override_settings(WHATSAPP_FALLBACK_TO_EMAIL=True)
def test_whatsapp_sin_consentimiento_fallback_true_envia_correo(mock_get_provider):
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=False,
        numeroTelefonico="+573001234567",
    )
    with patch("apps.core.notifier.send_mail") as mock_send:
        from apps.core.notifier import notificar_paciente
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is True
    mock_send.assert_called_once()
    mock_get_provider.assert_not_called()


@patch("apps.core.notifier.get_whatsapp_provider")
@pytest.mark.django_db
@override_settings(WHATSAPP_FALLBACK_TO_EMAIL=False)
def test_whatsapp_sin_consentimiento_fallback_false_no_envia(mock_get_provider):
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=False,
        numeroTelefonico="+573001234567",
    )
    with patch("apps.core.notifier.send_mail") as mock_send:
        from apps.core.notifier import notificar_paciente
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is False
    mock_send.assert_not_called()
    mock_get_provider.assert_not_called()


@patch("apps.core.notifier.get_whatsapp_provider")
@pytest.mark.django_db
@override_settings(WHATSAPP_FALLBACK_TO_EMAIL=True)
def test_whatsapp_sin_telefono_fallback_true_envia_correo(mock_get_provider):
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico=None,
    )
    with patch("apps.core.notifier.send_mail") as mock_send:
        from apps.core.notifier import notificar_paciente
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is True
    mock_send.assert_called_once()
    mock_get_provider.assert_not_called()
