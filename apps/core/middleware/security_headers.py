import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Cabeceras de seguridad estándar
        response["X-Content-Type-Options"] = "nosniff"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (CSP)
        # Configuración que permite recursos locales + Google OAuth
        if getattr(settings, "CSP_ENABLED", True):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://accounts.google.com https://apis.google.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' data: https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://accounts.google.com https://oauth2.googleapis.com; "
                "frame-src 'self' https://accounts.google.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
            # En desarrollo usar Report-Only para no romper funcionalidad mientras se ajusta
            if settings.DEBUG:
                response["Content-Security-Policy-Report-Only"] = csp
            else:
                response["Content-Security-Policy"] = csp

        return response
