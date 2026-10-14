# apps/core/whatsapp.py
import json
import logging
from abc import ABC, abstractmethod
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppProvider(ABC):
    @property
    @abstractmethod
    def simulado(self) -> bool:
        """True si el proveedor no envía mensajes reales."""
        ...

    @abstractmethod
    def enviar_whatsapp(self, numero_e164: str,
                        texto: str = None,
                        plantilla: str = None,
                        params: dict = None) -> str:
        """Devuelve message SID / ID del proveedor"""
        pass


class TwilioProvider(WhatsAppProvider):
    def __init__(self):
        self._simulado = False
        self.enabled = getattr(settings, "WHATSAPP_ENABLED", False)
        self.sid = getattr(settings, "TWILIO_SID", "")
        self.token = getattr(settings, "TWILIO_TOKEN", "")
        self.from_ = getattr(settings, "TWILIO_WHATSAPP_FROM", "")
        if self.enabled:
            if not (self.sid and self.token and self.from_):
                logger.error("Twilio credenciales incompletas – WHATSAPP_ENABLED=True pero faltan SID/TOKEN/FROM")
                raise RuntimeError("Twilio credentials missing")
            try:
                from twilio.rest import Client
                from twilio.base.exceptions import TwilioRestException
                self._client = Client(self.sid, self.token)
                self._TwilioRestException = TwilioRestException
            except Exception as exc:
                logger.error("Error inicializando Twilio client: %s", exc)
                raise
        else:
            self._client = None
            self._TwilioRestException = None

    @property
    def simulado(self) -> bool:
        return self._simulado

    def enviar_whatsapp(self, numero_e164: str,
                        texto: str = None,
                        plantilla: str = None,
                        params: dict = None) -> str:
        if not self.enabled:
            self._simulado = True
            logger.info("[SIMULADO] WhatsApp a %s → %s", numero_e164, texto or plantilla)
            return "SIMULATED_SID"

        to = f"whatsapp:{numero_e164}"
        try:
            if plantilla:
                msg = self._client.messages.create(
                    from_=self.from_,
                    content_sid=plantilla,
                    content_variables=json.dumps(params or {}),
                    to=to,
                )
            else:
                msg = self._client.messages.create(
                    from_=self.from_,
                    body=texto,
                    to=to,
                )
            return msg.sid
        except self._TwilioRestException as exc:
            logger.error("Twilio error enviando a %s: %s", numero_e164, exc)
            raise


class DummyProvider(WhatsAppProvider):
    """Fallback cuando WHATSAPP_ENABLED=False"""
    @property
    def simulado(self) -> bool:
        return True

    def enviar_whatsapp(self, numero_e164: str,
                        texto: str = None,
                        plantilla: str = None,
                        params: dict = None) -> str:
        logger.info("[DUMMY] WhatsApp a %s → %s", numero_e164, texto or plantilla)
        return "DUMMY_SID"


def get_whatsapp_provider() -> WhatsAppProvider:
    if getattr(settings, "WHATSAPP_ENABLED", False):
        return TwilioProvider()
    return DummyProvider()