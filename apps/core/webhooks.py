# apps/core/webhooks.py
import logging
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from apps.patients.models import PerfilPaciente
from apps.core.whatsapp import get_whatsapp_provider

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhook(View):
    def post(self, request):
        auth_token = getattr(settings, "TWILIO_TOKEN", "").strip()
        if not auth_token:
            logger.error("TWILIO_TOKEN no configurado; webhook de WhatsApp deshabilitado")
            return HttpResponse(status=503)

        twilio_sig = request.headers.get('X-Twilio-Signature', '')
        url = getattr(settings, "TWILIO_WEBHOOK_URL", "") or request.build_absolute_uri()
        post_data = request.POST

        try:
            if not self._verify_signature(twilio_sig, url, post_data, auth_token):
                logger.warning("Invalid Twilio signature from %s", request.META.get('REMOTE_ADDR'))
                return HttpResponse(status=403)
        except ImportError:
            logger.exception("Twilio SDK no disponible; webhook de WhatsApp deshabilitado")
            return HttpResponse(status=503)

        body = post_data.get('Body', '').strip().upper()
        from_num = post_data.get('From', '').replace('whatsapp:', '')

        if body in ("STOP", "BAJA", "UNSUBSCRIBE"):
            try:
                perfil = PerfilPaciente.objects.get(numeroTelefonico=from_num)
                perfil.whatsappConsentimiento = False
                perfil.canalNotificacion = "email"
                perfil.whatsappConsentimientoFecha = None
                perfil.save(update_fields=["whatsappConsentimiento", "canalNotificacion", "whatsappConsentimientoFecha"])
                provider = get_whatsapp_provider()
                provider.enviar_whatsapp(from_num,
                    texto="Has sido dado de baja de notificaciones por WhatsApp. Seguirás recibiendo correos.")
                logger.info("Opt-out processed for %s", from_num)
            except PerfilPaciente.DoesNotExist:
                logger.warning("Opt-out from unknown number %s", from_num)
            except Exception as exc:
                logger.error("Error processing opt-out for %s: %s", from_num, exc)
        return HttpResponse(status=200)

    def _verify_signature(self, signature, url, params, auth_token=None):
        auth_token = auth_token or getattr(settings, "TWILIO_TOKEN", "").strip()
        if not auth_token or not signature:
            return False
        from twilio.request_validator import RequestValidator

        return RequestValidator(auth_token).validate(url, params, signature)


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppStatusCallback(View):
    """Optional endpoint to update Notificaciones status via Twilio status callbacks."""
    def post(self, request):
        sid = request.POST.get('MessageSid')
        status = request.POST.get('MessageStatus')  # sent, delivered, failed, undelivered
        if not sid:
            return HttpResponse(status=400)
        from apps.scheduling.models import Notificaciones
        try:
            notif = Notificaciones.objects.get(providerMsgId=sid)
            notif.estado = status
            notif.save(update_fields=["estado"])
        except Notificaciones.DoesNotExist:
            logger.warning("Status callback for unknown SID %s", sid)
        return HttpResponse(status=200)
