import json
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.template.loader import render_to_string

from apps.core.models import NewsletterSubscriber

logger = logging.getLogger(__name__)


class CoreService:
    """Servicios generales de la app core (newsletter, bienvenida, errores de cliente)."""

    def _get_site_url(self):
        return getattr(settings, "SITE_URL", "http://localhost:8000")

    def send_welcome_email(self, to_email):
        try:
            subject = "Bienvenido a PsyAI Connect"
            from_email = settings.DEFAULT_FROM_EMAIL or "PsyAI Connect <noreply@psyaiconnect.com>"
            site_url = self._get_site_url()

            plain_message = (
                "Bienvenido a PsyAI Connect!\n\n"
                "Gracias por suscribirte. Cada dia recibiras un tip de bienestar emocional en tu correo.\n\n"
                "Tu primer tip: Respiracion 4-7-8\n"
                "Inhala 4 segundos, sostén 7, exhala 8. Repite 4 veces.\n\n"
                f"Crea tu cuenta gratis: {site_url}/register.html\n\n"
                "---\n"
                'Si ya no deseas recibir estos correos, responde con "cancelar".'
            )

            html_message = render_to_string("emails/newsletter_welcome.html")

            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=from_email,
                to=[to_email],
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send(fail_silently=True)
        except Exception:
            logger.exception("Error enviando email de bienvenida a %s", to_email)

    def subscribe_newsletter(self, email):
        if not email:
            return {"error": "El correo es obligatorio"}, 400

        try:
            validate_email(email)
        except ValidationError:
            return {"error": "Correo electronico invalido"}, 400

        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={"is_active": True},
        )

        if not created and not subscriber.is_active:
            subscriber.is_active = True
            subscriber.save(update_fields=["is_active"])

        if created:
            self.send_welcome_email(email)

        message = "Te has suscrito correctamente" if created else "Ya estas suscrito"
        return {"success": True, "message": message, "created": created}, 200

    def log_client_error(self, request_body, max_bytes=2048):
        try:
            if len(request_body) > max_bytes:
                return
            data = json.loads(request_body)
            if not isinstance(data, dict):
                return

            def safe_field(value, limit):
                if value is None:
                    return ""
                text = "".join(
                    " " if ord(character) < 32 or ord(character) == 127 else character
                    for character in str(value)
                )
                text = " ".join(text.split())
                return text[:limit]

            msg = safe_field(data.get("message", ""), 500)
            # Ignore benign View Transition opt‑in warnings from browsers that don't support the API yet
            if "ViewTransition opt-in disabled" in msg:
                return
            logger.warning(
                "[ClientError] %s: %s | %s | page=%s",
                safe_field(data.get("type", "unknown"), 50),
                msg,
                safe_field(data.get("details", ""), 1000),
                safe_field(data.get("page", ""), 200),
            )
        except Exception:
            pass


# ── Instancia lista para usar (patrón usado en otras apps) ───────────────────
core_service = CoreService()


# ── Aliases de compatibilidad hacia atrás (no eliminar) ─────────────────────
_get_site_url = core_service._get_site_url
send_welcome_email = core_service.send_welcome_email
subscribe_newsletter = core_service.subscribe_newsletter
log_client_error = core_service.log_client_error
