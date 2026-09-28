# apps/core/whatsapp.py
import os, json, logging
from abc import ABC, abstractmethod
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppProvider(ABC):
    @abstractmethod
    def enviar_whatsapp(self, numero_e164: str,
                        texto: str = None,
                        plantilla: str = None,
                        params: dict = None) -> str:
        """Devuelve message SID / ID del proveedor"""
        pass


class TwilioProvider(WhatsAppProvider):
    def __init__(self):
        self.enabled = getattr(settings, "WHATSAPP_ENABLED", False)
        self.sid = os.getenv("TWILIO_SID")
        self.token = os.getenv("TWILIO_TOKEN")
        self.from_ = os.getenv("TWILIO_WHATSAPP_FROM")   # ej. "whatsapp:+14155238886"
        if self.enabled and not (self.sid and self.token and self.from_):
            logger.warning("Twilio credenciales incompletas – modo simulado")
            self.enabled = False
        if self.enabled:
            from twilio.rest import Client
            self.client = Client(self.sid, self.token)

    def enviar_whatsapp(self, numero_e164, texto=None, plantilla=None, params=None):
        if not self.enabled:
            logger.info("[SIMULADO] WhatsApp a %s → %s", numero_e164, texto or plantilla)
            return "SIMULATED_SID"
        to = f"whatsapp:{numero_e164}"
        if plantilla:
            msg = self.client.messages.create(
                from_=self.from_,
                content_sid=plantilla,
                content_variables=json.dumps(params or {}),
                to=to,
            )
        else:
            msg = self.client.messages.create(
                from_=self.from_,
                body=texto,
                to=to,
            )
        return msg.sid


class DummyProvider(WhatsAppProvider):
    """Fallback cuando WHATSAPP_ENABLED=False"""
    def enviar_whatsapp(self, numero_e164, texto=None, plantilla=None, params=None):
        logger.info("[DUMMY] WhatsApp a %s → %s", numero_e164, texto or plantilla)
        return "DUMMY_SID"


def get_whatsapp_provider() -> WhatsAppProvider:
    if getattr(settings, "WHATSAPP_ENABLED", False):
        return TwilioProvider()
    return DummyProvider()