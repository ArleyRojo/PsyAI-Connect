# apps/core/notifier.py
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from apps.core.whatsapp import get_whatsapp_provider


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

    def notificar_paciente(self, paciente, titulo, mensaje, tipo,
                           plantilla=None, params=None):
        """
        tipo ejemplos: 'recordatorio_cita', 'confirmacion_cita',
        'cancelacion_cita', 'mensaje_profesional'
        Returns True if at least one channel succeeded.
        """
        svc = PatientService()
        pref_resp, _ = svc.get_preferences(paciente.idUsuario)
        prefs = pref_resp.get("preferencias", {})
        canal = prefs.get("canalNotificacion", "email")
        if canal == "ninguno":
            self._registrar_intento(paciente, "interno", "guardado", titulo=titulo, mensaje=mensaje)
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
                subject, txt, html = self._build_email(paciente, titulo, mensaje)
                send_mail(subject, txt, settings.DEFAULT_FROM_EMAIL,
                          [paciente.email], html_message=html, fail_silently=False)
                self._registrar_intento(paciente, "email", "enviado",
                                        provider_msg_id="", titulo=titulo, mensaje=mensaje)
                success_any = True
            except Exception as e:
                self._registrar_intento(paciente, "email", "fallido", str(e),
                                        titulo=titulo, mensaje=mensaje)
                if canal == "email":
                    return False

        # ----- WHATSAPP -----
        if canal in ("whatsapp", "ambos"):
            if not prefs.get("whatsappConsentimiento"):
                self._registrar_intento(paciente, "whatsapp", "fallido",
                                        "Sin consentimiento", titulo=titulo, mensaje=mensaje)
                return success_any
            tel = prefs.get("numeroTelefonico")
            if not tel:
                self._registrar_intento(paciente, "whatsapp", "fallido",
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
                self._registrar_intento(paciente, "whatsapp", estado,
                                        provider_msg_id=sid, titulo=titulo, mensaje=mensaje)
                if estado == "enviado":
                    success_any = True
            except Exception as e:
                self._registrar_intento(paciente, "whatsapp", "fallido", str(e),
                                        titulo=titulo, mensaje=mensaje)

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
