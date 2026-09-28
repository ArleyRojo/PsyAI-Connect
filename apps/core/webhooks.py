# apps/core/webhooks.py
import hmac, hashlib
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from apps.patients.models import PerfilPaciente
from apps.authentication.models import Register
from apps.core.whatsapp import get_whatsapp_provider

@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhook(View):
    def post(self, request):
        twilio_sig = request.headers.get('X-Twilio-Signature', '')
        url = request.build_absolute_uri()
        post_data = request.POST.dict()
        if not self._verify_signature(twilio_sig, url, post_data):
            return HttpResponse(status=403)

        body = post_data.get('Body', '').strip().upper()
        from_num = post_data.get('From', '').replace('whatsapp:', '')

        if body in ("STOP", "BAJA", "UNSUBSCRIBE"):
            try:
                user = Register.objects.get(telefono=from_num)   # assumes Register has telefono field
                perfil = PerfilPaciente.objects.get(idPaciente=user)
                perfil.whatsappConsentimiento = False
                perfil.canalNotificacion = "email"
                perfil.whatsappConsentimientoFecha = None
                perfil.save(update_fields=["whatsappConsentimiento","canalNotificacion","whatsappConsentimientoFecha"])
                get_whatsapp_provider().enviar_whatsapp(from_num,
                    texto="Has sido dado de baja de notificaciones por WhatsApp. Seguirás recibiendo correos.")
            except Exception:
                pass
        return HttpResponse(status=200)

    def _verify_signature(self, signature, url, params):
        data = url + ''.join(f'{k}{v}' for k, v in sorted(params.items()))
        expected = hmac.new(settings.TWILIO_TOKEN.encode(),
                            data.encode(), hashlib.sha1).hexdigest()
        return hmac.compare_digest(signature, expected)