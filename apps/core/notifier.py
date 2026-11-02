# apps/core/notifier.py
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from apps.core.whatsapp import get_whatsapp_provider

logger = logging.getLogger(__name__)


def _lazy_patient_service():
    """Importa PatientService de forma perezosa para evitar AppRegistryNotReady."""
    from apps.patients.services import PatientService
    return PatientService


def PatientService(*args, **kwargs):
    """Wrapper perezoso para PatientService de apps.patients.services.

    Existe a nivel de módulo para que @patch("apps.core.notifier.PatientService")
    funcione en los tests, pero el import real se resuelve al llamar (dentro de
    notificar_paciente), evitando AppRegistryNotReady al importar el módulo.
    """
    return _lazy_patient_service()(*args, **kwargs)


class NotificationService:
    """Servicio de notificaciones al paciente (email y WhatsApp)."""

    def _build_email(self, paciente, titulo, mensaje):
        subject = f"[PsyAI] {titulo}"
        text = f"Hola {paciente.nombre},\n\n{mensaje}\n\nIngresa a la plataforma para más detalles."
        html = f"""
        <p>Hola <strong>{paciente.nombre}</strong>,</p>
        <p>{mensaje}</p>
        <p><a href="{settings.SITE_URL}/notificaciones">Ver en PsyAI Connect</a></p>
        """
        return subject, text, html

    def _registrar_intento(self, paciente, canal, estado, error="", provider_msg_id="", titulo="", mensaje=""):
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

    def _envio_email(self, paciente, titulo, mensaje, plantilla_email=None, params_email=None):
        """
        Intenta enviar un correo al paciente y registra el intento en Notificaciones.
        plantilla_email: ruta de plantilla HTML de Django (solo canal email).
        params_email: contexto para renderizar la plantilla.
        Retorna True si el envío tuvo éxito, False si falló (incluye fallos de correo
        que ya no se silencian: se capturan y se registran con estado 'fallido').
        """
        try:
            if plantilla_email is not None:
                html = render_to_string(plantilla_email, params_email or {})
                subject = f"[PsyAI] {titulo}"
                txt = mensaje
            else:
                subject, txt, html = self._build_email(paciente, titulo, mensaje)
            send_mail(subject, txt, settings.DEFAULT_FROM_EMAIL,
                      [paciente.email], html_message=html, fail_silently=False)
            self._registrar_intento(paciente, "email", "enviado",
                                    provider_msg_id="", titulo=titulo, mensaje=mensaje)
            return True
        except Exception as e:
            self._registrar_intento(paciente, "email", "fallido", str(e),
                                    titulo=titulo, mensaje=mensaje)
            return False

    def notificar_paciente(self, paciente, titulo, mensaje, tipo,
                           plantilla_email=None, params_email=None,
                           plantilla_whatsapp=None, params_whatsapp=None,
                           plantilla=None, params=None):
        """
        tipo ejemplos: 'recordatorio_cita', 'confirmacion_cita',
        'cancelacion_cita', 'mensaje_profesional', 'factura', 'cita_general'.
        Returns True if at least one channel succeeded.

        plantilla_email / params_email: plantilla HTML de Django y contexto, solo
            para el canal email (usada por citas y facturas).
        plantilla_whatsapp / params_whatsapp: SID de plantilla de Twilio y variables,
            solo para el canal WhatsApp.
        plantilla / params: argumentos legacy de compatibilidad. Si se pasan, se
            interpretan como plantilla_email / params_email (nunca se envían a
            Twilio, evitando que una ruta HTML llegue como content_sid).

        Los correos transaccionales críticos (recuperación de contraseña, cuenta
        suspendida, alertas de riesgo) NO pasan por este método: se envían siempre
        directamente desde sus propios servicios y no respetan preferencias del canal.
        """
        # ── Compatibilidad hacia atrás ──────────────────────────────────────
        # Los llamadores antiguos usan plantilla/params. Se tratan como email
        # para que una ruta HTML nunca se envíe a Twilio como content_sid.
        if plantilla_email is None and plantilla is not None:
            plantilla_email = plantilla
        if params_email is None and params is not None:
            params_email = params

        svc = PatientService()
        pref_resp, _ = svc.get_preferences(paciente.idUsuario)
        prefs = pref_resp.get("preferencias", {})
        canal = prefs.get("canalNotificacion", "email")
        if canal == "ninguno":
            self._registrar_intento(paciente, "interno", "guardado", titulo=titulo, mensaje=mensaje)
            return False

        # filtrar por tipo de aviso desactivado (interruptores por tipo de aviso)
        if tipo == "recordatorio_cita" and not prefs.get("recibirRecordatorioCita", True):
            return False
        if tipo in ("confirmacion_cita", "cancelacion_cita") and not prefs.get("recibirConfirmacion", True):
            return False
        if tipo == "mensaje_profesional" and not prefs.get("recibirMensajePro", True):
            return False
        if tipo == "factura" and not prefs.get("recibirFacturas", True):
            return False
        if tipo == "notificacion_admin" and not prefs.get("recibirNotificacionesAdmin", True):
            return False

        success_any = False
        email_intentado = False
        # Cuando WhatsApp no puede usarse (sin consentimiento o sin teléfono),
        # ¿rehacer el envío por correo como respaldo? Configurable vía settings.
        fallback_email = getattr(settings, "WHATSAPP_FALLBACK_TO_EMAIL", True)

        # ----- EMAIL -----
        if canal in ("email", "ambos"):
            email_intentado = True
            if self._envio_email(paciente, titulo, mensaje,
                                 plantilla_email=plantilla_email, params_email=params_email):
                success_any = True
            elif canal == "email":
                return False

        # ----- WHATSAPP -----
        if canal in ("whatsapp", "ambos"):
            tiene_consentimiento = bool(prefs.get("whatsappConsentimiento"))
            tiene_telefono = bool(prefs.get("numeroTelefonico"))
            if not tiene_consentimiento or not tiene_telefono:
                if not tiene_consentimiento:
                    self._registrar_intento(paciente, "whatsapp", "fallido",
                                            "Sin consentimiento", titulo=titulo, mensaje=mensaje)
                else:
                    self._registrar_intento(paciente, "whatsapp", "fallido",
                                            "Teléfono no configurado", titulo=titulo, mensaje=mensaje)
                # Respaldo por correo solo si el canal era exclusivamente whatsapp
                # y no se logró enviar por ningún otro canal.
                if fallback_email and canal == "whatsapp" and not success_any and not email_intentado:
                    if self._envio_email(paciente, titulo, mensaje):
                        success_any = True
                return success_any

            # Determinar SID de plantilla de Twilio (solo WhatsApp).
            # plantilla_whatsapp nunca debe ser una ruta HTML de Django.
            if plantilla_whatsapp is None:
                if tipo == "recordatorio_cita":
                    plantilla_whatsapp = getattr(settings, "TWILIO_TPL_RECORDATORIO", "")
                elif tipo == "confirmacion_cita":
                    plantilla_whatsapp = getattr(settings, "TWILIO_TPL_CONFIRMACION", "")
                elif tipo == "cancelacion_cita":
                    plantilla_whatsapp = getattr(settings, "TWILIO_TPL_CANCELACION", "")
                elif tipo == "mensaje_profesional":
                    plantilla_whatsapp = getattr(settings, "TWILIO_TPL_MENSAJE_PRO", "")
                elif tipo == "factura":
                    plantilla_whatsapp = getattr(settings, "TWILIO_TPL_FACTURA", "")
                elif tipo == "cita_general":
                    plantilla_whatsapp = getattr(settings, "TWILIO_TPL_CITA_GENERAL", "")
                elif tipo == "notificacion_admin":
                    plantilla_whatsapp = getattr(settings, "TWILIO_TPL_NOTIFICACION_ADMIN", "")

            tel = prefs.get("numeroTelefonico")
            provider = get_whatsapp_provider()
            try:
                if plantilla_whatsapp:
                    sid = provider.enviar_whatsapp(
                        tel, texto=mensaje, plantilla=plantilla_whatsapp,
                        params=params_whatsapp)
                else:
                    # Texto libre: Twilio exige plantilla fuera de la ventana de 24 h.
                    logger.warning(
                        "Twilio sin plantilla configurada para tipo '%s': enviando "
                        "texto libre (body). Fuera de la ventana de 24 h Twilio puede "
                        "rechazar el mensaje.", tipo)
                    sid = provider.enviar_whatsapp(tel, texto=mensaje, plantilla=None, params=None)
                estado = "enviado" if not provider.simulado else "simulado"
                self._registrar_intento(paciente, "whatsapp", estado,
                                        provider_msg_id=sid, titulo=titulo, mensaje=mensaje)
                if estado == "enviado":
                    success_any = True
            except Exception as e:
                self._registrar_intento(paciente, "whatsapp", "fallido", str(e),
                                        titulo=titulo, mensaje=mensaje)
                # Respaldo por correo para canal whatsapp (o ambos sin email exitoso)
                # cuando Twilio falla y el fallback está habilitado. No reintentar
                # el correo si ya se intentó (y falló) en el paso de email.
                if fallback_email and not success_any and not email_intentado:
                    if self._envio_email(paciente, titulo, mensaje):
                        success_any = True

        return success_any

    def enviar_prueba(self, numero_e164: str, texto: str = "✅ Prueba desde PsyAI Connect"):
        """Envía un mensaje de prueba; retorna (ok: bool, mensaje: str)."""
        provider = get_whatsapp_provider()
        try:
            sid = provider.enviar_whatsapp(numero_e164, texto=texto)
            if provider.simulado:
                return True, f"Simulado (sid={sid})"
            return True, f"Enviado (sid={sid})"
        except Exception as exc:
            return False, str(exc)


# ── Instancia lista para usar ────────────────────────────────────────────────
notification_service = NotificationService()


# ── Aliases de compatibilidad hacia atrás (no eliminar) ─────────────────────
_build_email = notification_service._build_email
_registrar_intento = notification_service._registrar_intento
notificar_paciente = notification_service.notificar_paciente
enviar_prueba = notification_service.enviar_prueba
