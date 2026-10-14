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


def _registrar_intento(paciente, canal, estado, error="", provider_msg_id="", titulo="", mensaje=""):
    from apps.scheduling.models import Notificaciones
    Notificaciones.objects.create(
        idUsuario=paciente,
        rol="paciente",
        titulo=titulo,
        mensaje=mensaje,
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
    Returns True if at least one channel succeeded.
    """
    from apps.patients.services import PatientService
    svc = PatientService()
    pref_resp, _ = svc.get_preferences(paciente.idUsuario)
    prefs = pref_resp.get("preferencias", {})
    canal = prefs.get("canalNotificacion", "email")
    if canal == "ninguno":
        _registrar_intento(paciente, "interno", "guardado", titulo=titulo, mensaje=mensaje)
        return False

    # filtrar por tipo de aviso desactivado
    if tipo == "recordatorio_cita" and not prefs.get("recibirRecordatorioCita", True):
        return False
    if tipo in ("confirmacion_cita", "cancelacion_cita") and not prefs.get("recibirConfirmacion", True):
        return False
    if tipo == "mensaje_profesional" and not prefs.get("recibirMensajePro", True):
        return False

    success_any = False

    # ----- EMAIL -----
    if canal in ("email", "ambos"):
        try:
            subject, txt, html = _build_email(paciente, titulo, mensaje)
            send_mail(subject, txt, settings.DEFAULT_FROM_EMAIL,
                      [paciente.email], html_message=html, fail_silently=False)
            _registrar_intento(paciente, "email", "enviado",
                               provider_msg_id="", titulo=titulo, mensaje=mensaje)
            success_any = True
        except Exception as e:
            _registrar_intento(paciente, "email", "fallido", str(e),
                               titulo=titulo, mensaje=mensaje)
            if canal == "email":
                return False

    # ----- WHATSAPP -----
    if canal in ("whatsapp", "ambos"):
        if not prefs.get("whatsappConsentimiento"):
            _registrar_intento(paciente, "whatsapp", "fallido",
                               "Sin consentimiento", titulo=titulo, mensaje=mensaje)
            return success_any
        tel = prefs.get("numeroTelefonico")
        if not tel:
            _registrar_intento(paciente, "whatsapp", "fallido",
                               "Teléfono no configurado", titulo=titulo, mensaje=mensaje)
            return success_any

        # Determine template SID if not provided
        if plantilla is None:
            if tipo == "recordatorio_cita":
                plantilla = getattr(settings, "TWILIO_TPL_RECORDATORIO", "")
            elif tipo == "confirmacion_cita":
                plantilla = getattr(settings, "TWILIO_TPL_CONFIRMACION", "")
            elif tipo == "cancelacion_cita":
                plantilla = getattr(settings, "TWILIO_TPL_CANCELACION", "")
            elif tipo == "mensaje_profesional":
                plantilla = getattr(settings, "TWILIO_TPL_MENSAJE_PRO", "")

        provider = get_whatsapp_provider()
        try:
            sid = provider.enviar_whatsapp(tel, texto=mensaje, plantilla=plantilla, params=params)
            estado = "enviado" if not provider.simulado else "simulado"
            _registrar_intento(paciente, "whatsapp", estado,
                               provider_msg_id=sid, titulo=titulo, mensaje=mensaje)
            if estado == "enviado":
                success_any = True
        except Exception as e:
            _registrar_intento(paciente, "whatsapp", "fallido", str(e),
                               titulo=titulo, mensaje=mensaje)

    return success_any


def enviar_prueba(numero_e164: str, texto: str = "✅ Prueba desde PsyAI Connect"):
    """Envía un mensaje de prueba; retorna (ok: bool, mensaje: str)."""
    provider = get_whatsapp_provider()
    try:
        sid = provider.enviar_whatsapp(numero_e164, texto=texto)
        if provider.simulado:
            return True, f"Simulado (sid={sid})"
        return True, f"Enviado (sid={sid})"
    except Exception as exc:
        return False, str(exc)