# apps/core/notifier.py
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from apps.core.whatsapp import get_whatsapp_provider


def _build_email(paciente, titulo, mensaje):
    subject = f"[PsyAI] {titulo}"
    text = f"Hola {paciente.nombre},\n\n{mensaje}\n\nIngresa a la plataforma para más detalles."
    html = f"""
    <p>Hola <strong>{paciente.nombre}</strong>,</p>
    <p>{mensaje}</p>
    <p><a href="{settings.SITE_URL}/notificaciones">Ver en PsyAI Connect</a></p>
    """
    return subject, text, html


def _registrar_intento(paciente, canal, estado, error="", provider_msg_id=""):
    from apps.scheduling.models import Notificaciones
    Notificaciones.objects.create(
        idUsuario=paciente,
        rol="paciente",
        titulo="",
        mensaje="",
        tipo="sistema",
        estado=estado,
        canal=canal,
        errorDetalle=error,
        providerMsgId=provider_msg_id,
        fecha=timezone.now(),
    )


def notificar_paciente(paciente, titulo, mensaje, tipo,
                       plantilla=None, params=None):
    """
    tipo ejemplos: 'recordatorio_cita', 'confirmacion_cita',
    'cancelacion_cita', 'mensaje_profesional'
    """
    from apps.patients.services import PatientService
    svc = PatientService()
    pref_resp, _ = svc.get_preferences(paciente.idUsuario)
    prefs = pref_resp.get("preferencias", {})
    canal = prefs.get("canalNotificacion", "email")
    if canal == "ninguno":
        _registrar_intento(paciente, "interno", "guardado")
        return

    # filtrar por tipo de aviso desactivado
    if tipo == "recordatorio_cita" and not prefs.get("recibirRecordatorioCita", True):
        return
    if tipo in ("confirmacion_cita","cancelacion_cita") and not prefs.get("recibirConfirmacion", True):
        return
    if tipo == "mensaje_profesional" and not prefs.get("recibirMensajePro", True):
        return

    # ----- EMAIL -----
    if canal in ("email", "ambos"):
        try:
            subject, txt, html = _build_email(paciente, titulo, mensaje)
            send_mail(subject, txt, settings.DEFAULT_FROM_EMAIL,
                      [paciente.email], html_message=html, fail_silently=False)
            _registrar_intento(paciente, "email", "enviado")
        except Exception as e:
            _registrar_intento(paciente, "email", "fallido", str(e))
            if canal == "email":
                return

    # ----- WHATSAPP -----
    if canal in ("whatsapp", "ambos"):
        if not prefs.get("whatsappConsentimiento"):
            _registrar_intento(paciente, "whatsapp", "fallido",
                               "Sin consentimiento")
            return
        tel = prefs.get("numeroTelefonico")
        if not tel:
            _registrar_intento(paciente, "whatsapp", "fallido",
                               "Teléfono no configurado")
            return
        provider = get_whatsapp_provider()
        try:
            sid = provider.enviar_whatsapp(tel, texto=mensaje)
            _registrar_intento(paciente, "whatsapp", "enviado",
                               provider_msg_id=sid)
        except Exception as e:
            _registrar_intento(paciente, "whatsapp", "fallido", str(e))