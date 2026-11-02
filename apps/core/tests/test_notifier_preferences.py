# apps/core/tests/test_notifier_preferences.py
from unittest.mock import patch, MagicMock

import pytest
from django.core import mail
from django.test import override_settings

from apps.authentication.models import Register
from apps.core.notifier import notificar_paciente, notification_service
from apps.scheduling.models import Notificaciones


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
    from apps.patients.models import PerfilPaciente
    PerfilPaciente.objects.create(idPaciente=user, **defaults)
    return user


def _whatsapp_provider_mock(sid="SID_W", simulado=False):
    provider = MagicMock()
    provider.simulado = simulado
    provider.enviar_whatsapp.return_value = sid
    return provider


@pytest.mark.django_db
def test_canal_email_envia_correo_y_no_whatsapp():
    user = _make_patient(canalNotificacion="email")
    with patch("apps.core.notifier.send_mail") as mock_send, \
            patch("apps.core.notifier.get_whatsapp_provider") as mock_wp:
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is True
    mock_send.assert_called_once()
    mock_wp.assert_not_called()
    assert len(mail.outbox) == 0  # send_mail está mockeado


@pytest.mark.django_db
def test_canal_whatsapp_envia_whatsapp_y_no_correo():
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    prov = _whatsapp_provider_mock()
    with patch("apps.core.notifier.send_mail") as mock_send, \
            patch("apps.core.notifier.get_whatsapp_provider", return_value=prov):
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is True
    prov.enviar_whatsapp.assert_called_once()
    mock_send.assert_not_called()


@pytest.mark.django_db
def test_canal_ambos_envia_correo_y_whatsapp():
    user = _make_patient(
        canalNotificacion="ambos",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    prov = _whatsapp_provider_mock()
    with patch("apps.core.notifier.send_mail") as mock_send, \
            patch("apps.core.notifier.get_whatsapp_provider", return_value=prov):
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is True
    mock_send.assert_called_once()
    prov.enviar_whatsapp.assert_called_once()


@pytest.mark.django_db
def test_canal_ninguno_no_envia_nada():
    user = _make_patient(canalNotificacion="ninguno")
    with patch("apps.core.notifier.send_mail") as mock_send, \
            patch("apps.core.notifier.get_whatsapp_provider") as mock_wp:
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is False
    mock_send.assert_not_called()
    mock_wp.assert_not_called()
    intento = Notificaciones.objects.filter(idUsuario=user, canal="interno").first()
    assert intento is not None
    assert intento.estado == "guardado"


@pytest.mark.django_db
def test_canal_whatsapp_sin_consentimiento_respaldo_por_correo():
    # Canal whatsapp pero sin consentimiento: con fallback habilitado se reenvía por correo.
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=False,
        numeroTelefonico="+573001234567",
    )
    with patch("apps.core.notifier.send_mail") as mock_send, \
            patch("apps.core.notifier.get_whatsapp_provider") as mock_wp:
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is True
    mock_send.assert_called_once()
    mock_wp.assert_not_called()
    # Se registra el fallo de whatsapp y el envío de correo de respaldo
    intentos = list(
        Notificaciones.objects.filter(idUsuario=user).order_by("fecha")
    )
    canales = [i.canal for i in intentos]
    assert "whatsapp" in canales
    assert "email" in canales


@pytest.mark.django_db
@override_settings(WHATSAPP_FALLBACK_TO_EMAIL=False)
def test_canal_whatsapp_sin_consentimiento_sin_fallback_no_envia():
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=False,
        numeroTelefonico="+573001234567",
    )
    with patch("apps.core.notifier.send_mail") as mock_send, \
            patch("apps.core.notifier.get_whatsapp_provider") as mock_wp:
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is False
    mock_send.assert_not_called()
    mock_wp.assert_not_called()


@pytest.mark.django_db
def test_canal_whatsapp_sin_telefono_respaldo_por_correo():
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico=None,
    )
    with patch("apps.core.notifier.send_mail") as mock_send, \
            patch("apps.core.notifier.get_whatsapp_provider") as mock_wp:
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is True
    mock_send.assert_called_once()
    mock_wp.assert_not_called()


@pytest.mark.django_db
def test_tipo_factura_no_tiene_interruptor_y_respeta_canal():
    # 'factura' no tiene interruptor propio: con canal whatsapp y sin consentimiento
    # usa el respaldo por correo; con canal email envía correo.
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=False,
        numeroTelefonico="+573001234567",
    )
    with patch("apps.core.notifier.send_mail") as mock_send, \
            patch("apps.core.notifier.get_whatsapp_provider") as mock_wp:
        ok = notificar_paciente(user, "Factura", "Pago pendiente", "factura")
    assert ok is True
    mock_send.assert_called_once()
    mock_wp.assert_not_called()


@pytest.mark.django_db
def test_interruptor_recordatorio_desactivado_bloquea_recordatorio():
    user = _make_patient(
        canalNotificacion="email",
        recibirRecordatorioCita=False,
    )
    with patch("apps.core.notifier.send_mail") as mock_send:
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is False
    mock_send.assert_not_called()


@pytest.mark.django_db
def test_interruptor_confirmacion_desactivado_bloquea_confirmacion_y_cancelacion():
    user = _make_patient(
        canalNotificacion="email",
        recibirConfirmacion=False,
    )
    with patch("apps.core.notifier.send_mail") as mock_send:
        assert notificar_paciente(user, "T", "M", "confirmacion_cita") is False
        assert notificar_paciente(user, "T", "M", "cancelacion_cita") is False
    mock_send.assert_not_called()


@pytest.mark.django_db
def test_fallo_de_correo_se_registra_como_fallido_y_no_se_silencia():
    user = _make_patient(canalNotificacion="email")
    with patch("apps.core.notifier.send_mail", side_effect=Exception("SMTP caído")):
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is False
    fallido = Notificaciones.objects.filter(
        idUsuario=user, canal="email", estado="fallido"
    ).first()
    assert fallido is not None
    assert "SMTP caído" in fallido.errorDetalle


@pytest.mark.django_db
def test_whatsapp_error_de_proveedor_se_registra_y_no_envia_correo():
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    prov = MagicMock()
    prov.simulado = False
    prov.enviar_whatsapp.side_effect = Exception("Twilio error")
    # Con fallback habilitado (default True), el correo de respaldo se envía
    with patch("apps.core.notifier.send_mail") as mock_send, \
            patch("apps.core.notifier.get_whatsapp_provider", return_value=prov):
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is True  # fallback por correo rescató el envío
    mock_send.assert_called_once()
    fallido = Notificaciones.objects.filter(
        idUsuario=user, canal="whatsapp", estado="fallido"
    ).first()
    assert fallido is not None
    enviado = Notificaciones.objects.filter(
        idUsuario=user, canal="email", estado="enviado"
    ).first()
    assert enviado is not None


@pytest.mark.django_db
@override_settings(WHATSAPP_FALLBACK_TO_EMAIL=False)
def test_whatsapp_error_sin_fallback_no_envia_correo():
    """Sin fallback, error de Twilio no envía correo y retorna False."""
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    prov = MagicMock()
    prov.simulado = False
    prov.enviar_whatsapp.side_effect = Exception("Twilio error")
    with patch("apps.core.notifier.send_mail") as mock_send, \
            patch("apps.core.notifier.get_whatsapp_provider", return_value=prov):
        ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is False
    mock_send.assert_not_called()


@pytest.mark.django_db
def test_notificar_paciente_usa_plantilla_cuando_se_proporciona():
    user = _make_patient(canalNotificacion="email")
    with patch("apps.core.notifier.send_mail") as mock_send, \
            patch("apps.core.notifier.render_to_string", return_value="<p>html</p>"):
        ok = notificar_paciente(
            user, "T", "M", "factura",
            plantilla="emails/factura_notificacion.html",
            params={"id_factura": 5},
        )
    assert ok is True
    mock_send.assert_called_once()
    # El subject debe llevar el prefijo [PsyAI]
    args, kwargs = mock_send.call_args
    assert args[0] == "[PsyAI] T"
    assert kwargs["html_message"] == "<p>html</p>"


@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.send_mail")
@pytest.mark.django_db
def test_ambos_whatsapp_imposible_correo_ok_devuelve_exito(mock_send, mock_get_provider):
    """Canal ambos: WhatsApp sin consentimiento, pero correo OK → éxito."""
    user = _make_patient(
        canalNotificacion="ambos",
        whatsappConsentimiento=False,
        numeroTelefonico="+573001234567",
    )
    mock_send.return_value = None
    provider = MagicMock()
    provider.simulado = False
    mock_get_provider.return_value = provider

    ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is True
    mock_send.assert_called_once()
    mock_get_provider.assert_not_called()  # WhatsApp no se intenta (sin consentimiento)


@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.send_mail")
@pytest.mark.django_db
def test_ambos_correo_falla_whatsapp_ok_devuelve_exito(mock_send, mock_get_provider):
    """Canal ambos: correo falla pero WhatsApp sale → éxito."""
    user = _make_patient(
        canalNotificacion="ambos",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    mock_send.side_effect = Exception("SMTP error")
    provider = MagicMock()
    provider.simulado = False
    provider.enviar_whatsapp.return_value = "SID_OK"
    mock_get_provider.return_value = provider

    ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is True
    mock_send.assert_called_once()  # se intentó correo
    provider.enviar_whatsapp.assert_called_once()  # WhatsApp también se intentó


@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.send_mail")
@pytest.mark.django_db
@override_settings(TWILIO_TPL_FACTURA="")
def test_factura_interruptor_false_no_envia(mock_send, mock_get_provider):
    """recibirFacturas=False: tipo factura no se envía."""
    user = _make_patient(
        canalNotificacion="email",
        recibirFacturas=False,
    )
    ok = notificar_paciente(user, "Factura", "Pago pendiente", "factura")
    assert ok is False
    mock_send.assert_not_called()
    mock_get_provider.assert_not_called()


@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.send_mail")
@pytest.mark.django_db
@override_settings(TWILIO_TPL_NOTIFICACION_ADMIN="")
def test_notificacion_admin_interruptor_false_no_envia(mock_send, mock_get_provider):
    """recibirNotificacionesAdmin=False: tipo notificacion_admin no se envía."""
    user = _make_patient(
        canalNotificacion="email",
        recibirNotificacionesAdmin=False,
    )
    ok = notificar_paciente(user, "Admin", "Aviso", "notificacion_admin")
    assert ok is False
    mock_send.assert_not_called()
    mock_get_provider.assert_not_called()


@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.send_mail")
@pytest.mark.django_db
@override_settings(TWILIO_TPL_FACTURA="FAKE_SID_FACTURA")
def test_factura_con_sid_pasa_plantilla_a_twilio(mock_send, mock_get_provider):
    """Factura con TWILIO_TPL_FACTURA configurado: se pasa como plantilla a Twilio."""
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
        recibirFacturas=True,
    )
    provider = MagicMock()
    provider.simulado = False
    provider.enviar_whatsapp.return_value = "SID_FAC"
    mock_get_provider.return_value = provider

    ok = notificar_paciente(user, "Factura", "Pago pendiente", "factura")
    assert ok is True
    mock_send.assert_not_called()  # canal whatsapp, no correo
    kw = provider.enviar_whatsapp.call_args.kwargs
    assert kw.get("plantilla") == "FAKE_SID_FACTURA"
    assert not (isinstance(kw.get("plantilla"), str) and kw.get("plantilla", "").endswith(".html"))


@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.send_mail")
@pytest.mark.django_db
@override_settings(TWILIO_TPL_NOTIFICACION_ADMIN="FAKE_SID_ADMIN")
def test_notificacion_admin_con_sid_pasa_plantilla_a_twilio(mock_send, mock_get_provider):
    """Notificacion_admin con TWILIO_TPL_NOTIFICACION_ADMIN: se pasa a Twilio."""
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
        recibirNotificacionesAdmin=True,
    )
    provider = MagicMock()
    provider.simulado = False
    provider.enviar_whatsapp.return_value = "SID_ADMIN"
    mock_get_provider.return_value = provider

    ok = notificar_paciente(user, "Admin", "Aviso", "notificacion_admin")
    assert ok is True
    kw = provider.enviar_whatsapp.call_args.kwargs
    assert kw.get("plantilla") == "FAKE_SID_ADMIN"
    assert not (isinstance(kw.get("plantilla"), str) and kw.get("plantilla", "").endswith(".html"))


@patch("apps.core.notifier.get_whatsapp_provider")
@pytest.mark.django_db
def test_notifier_whatsapp_nunca_recibe_ruta_html_como_content_sid(mock_get_provider):
    """BUG: plantilla_email (ruta .html) nunca debe llegar a Twilio como content_sid."""
    user = _make_patient(
        canalNotificacion="whatsapp",
        whatsappConsentimiento=True,
        numeroTelefonico="+573001234567",
    )
    provider = MagicMock()
    provider.simulado = False
    provider.enviar_whatsapp.return_value = "SID_OK"
    mock_get_provider.return_value = provider

    with patch("apps.core.notifier.send_mail"):
        notificar_paciente(
            user, "T", "M", "factura",
            plantilla_email="emails/factura_notificacion.html",
            params_email={"id_factura": 5},
        )

    provider.enviar_whatsapp.assert_called_once()
    kw = provider.enviar_whatsapp.call_args.kwargs
    content_sid = kw.get("plantilla")
    assert not (isinstance(content_sid, str) and content_sid.endswith(".html"))


@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.logger")
@pytest.mark.django_db
@override_settings(TWILIO_TPL_FACTURA="")
def test_notifier_factura_sin_sid_texto_libre_con_warning(mock_logger, mock_get_provider):
    """Tipo factura sin SID: texto libre y warning de plantilla ausente."""
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
        notificar_paciente(user, "Factura", "Pago pendiente", "factura")

    provider.enviar_whatsapp.assert_called_once()
    kw = provider.enviar_whatsapp.call_args.kwargs
    assert kw.get("plantilla") is None  # texto libre (body)
    assert kw.get("texto") == "Pago pendiente"
    assert mock_logger.warning.called
    assert "plantilla" in mock_logger.warning.call_args[0][0].lower()


# ── Migración 0010: campos nuevos con default True, sin alterar existentes ──

@pytest.mark.django_db
def test_migracion_0010_defaults_true_sin_alterar_existentes():
    """La migración 0010 agrega recibirFacturas y recibirNotificacionesAdmin
    con default True. Pacientes creados antes conservan sus valores."""
    from django.db import connection
    from apps.patients.models import PerfilPaciente

    # Verificar que los campos existen en el modelo
    campos = [f.name for f in PerfilPaciente._meta.get_fields()]
    assert "recibirFacturas" in campos
    assert "recibirNotificacionesAdmin" in campos

    # Paciente nuevo: defaults son True
    user = Register.objects.create_user(
        email="nuevo@test.com", password="x", rol="paciente", nombre="Nuevo",
    )
    PerfilPaciente.objects.create(idPaciente=user, canalNotificacion="email")
    perfil = PerfilPaciente.objects.get(idPaciente=user)
    assert perfil.recibirFacturas is True
    assert perfil.recibirNotificacionesAdmin is True


# ── Interruptores: recibirFacturas=False / recibirNotificacionesAdmin=False ──
# Los demás avisos sí llegan

@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.send_mail")
@pytest.mark.django_db
def test_recibir_facturas_false_otros_avisos_si_llegan(mock_send, mock_get_provider):
    """recibirFacturas=False bloquea factura, pero recordatorio_cita sí llega."""
    mock_send.return_value = None
    user = _make_patient(
        canalNotificacion="email",
        recibirFacturas=False,
        recibirRecordatorioCita=True,
    )
    # Factura no se envía
    ok_factura = notificar_paciente(user, "Factura", "Pago", "factura")
    assert ok_factura is False
    mock_send.assert_not_called()
    # Recordatorio sí se envía
    mock_send.reset_mock()
    ok_recordatorio = notificar_paciente(user, "Recordatorio", "Cita mañana", "recordatorio_cita")
    assert ok_recordatorio is True
    mock_send.assert_called_once()


@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.send_mail")
@pytest.mark.django_db
def test_recibir_notificaciones_admin_false_otros_avisos_si_llegan(mock_send, mock_get_provider):
    """recibirNotificacionesAdmin=False bloquea admin, pero mensaje_profesional sí llega."""
    mock_send.return_value = None
    user = _make_patient(
        canalNotificacion="email",
        recibirNotificacionesAdmin=False,
        recibirMensajePro=True,
    )
    # Admin no se envía
    ok_admin = notificar_paciente(user, "Admin", "Aviso", "notificacion_admin")
    assert ok_admin is False
    mock_send.assert_not_called()
    # Mensaje profesional sí se envía
    mock_send.reset_mock()
    ok_pro = notificar_paciente(user, "Pro", "Mensaje", "mensaje_profesional")
    assert ok_pro is True
    mock_send.assert_called_once()


# ── Conteo de omitidos con canal "ninguno" y con interruptor apagado ──

@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.send_mail")
@pytest.mark.django_db
def test_conteo_omitidos_canal_ninguno(mock_send, mock_get_provider):
    """canalNotificacion='ninguno' → omitido, no fallido."""
    user = _make_patient(canalNotificacion="ninguno")
    ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is False
    mock_send.assert_not_called()
    mock_get_provider.assert_not_called()
    # Se registra intento interno (guardado)
    interno = Notificaciones.objects.filter(
        idUsuario=user, canal="interno", estado="guardado"
    ).first()
    assert interno is not None


@patch("apps.core.notifier.get_whatsapp_provider")
@patch("apps.core.notifier.send_mail")
@pytest.mark.django_db
def test_conteo_omitidos_interruptor_apagado(mock_send, mock_get_provider):
    """recibirRecordatorioCita=False → omitido (no se intenta envío)."""
    user = _make_patient(
        canalNotificacion="email",
        recibirRecordatorioCita=False,
    )
    ok = notificar_paciente(user, "T", "M", "recordatorio_cita")
    assert ok is False
    mock_send.assert_not_called()
    mock_get_provider.assert_not_called()
