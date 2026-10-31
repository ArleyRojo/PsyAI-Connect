import json
import logging
import mimetypes
import os
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import (
    FileResponse,
    Http404,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.utils._os import safe_join
from django.views import View
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from rest_framework.views import APIView

from apps.core.services import core_service

logger = logging.getLogger(__name__)

UPLOADS_DIR = os.path.join(settings.MEDIA_ROOT, "uploads")

MIME_OVERRIDES = {
    ".js": "text/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
}

PAGES_LEGAL = {
    "privacidad": {"title": "Pol\u00edtica de Privacidad", "template": "legal/privacidad.html"},
    "terminos": {"title": "T\u00e9rminos y Condiciones", "template": "legal/terminos.html"},
    "cookies": {"title": "Pol\u00edtica de Cookies", "template": "legal/cookies.html"},
}

DIRECT_MAP = {
    "index.html": "base/index.html",
    "login.html": "auth/login.html",
    "register.html": "auth/register.html",
    "recover": "auth/recover.html",
    "recover.html": "auth/recover.html",
    "reset-password": "auth/reset-password.html",
    "reset-password.html": "auth/reset-password.html",
    "admin.dashboard.html": "admin/admin.dashboard.html",
    "patient.dashboard.html": "patient/patient.dashboard.html",
    "professional.dashboard.html": "professional/professional.dashboard.html",
    "patient/agendaquotes.html": "patient/aside-patient/agenda-quotes.html",
}


def _template_root():
    return os.path.join(settings.BASE_DIR, "templates")


def _static_root():
    return settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else os.path.join(settings.BASE_DIR, "static")


@method_decorator(csrf_exempt, name="dispatch")
class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        db_connected = False
        try:
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_connected = True
        except Exception:
            pass

        status_code = 200 if db_connected else 503
        return JsonResponse(
            {
                "status": "healthy" if db_connected else "degraded",
                "version": "1.0.0",
                "db": "Conectada" if db_connected else "Sin conexion",
                "db_connected": db_connected,
                "environment": getattr(settings, "ENV", os.getenv("DJANGO_SETTINGS_MODULE", "development")),
            },
            status=status_code,
        )


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(ratelimit(key="ip", rate="30/m", method="POST", block=True), name="dispatch")
class ClientErrorsView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        max_body_bytes = 2048
        content_length = request.META.get("CONTENT_LENGTH")
        try:
            if content_length and int(content_length) > max_body_bytes:
                return JsonResponse({"error": "Solicitud demasiado grande"}, status=413)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Longitud de solicitud inválida"}, status=400)

        body = request.body
        if len(body) > max_body_bytes:
            return JsonResponse({"error": "Solicitud demasiado grande"}, status=413)
        core_service.log_client_error(body, max_bytes=max_body_bytes)
        return JsonResponse({"status": "ok"})

    def get(self, request):
        return JsonResponse({"error": "Method not allowed"}, status=405)


class ServePagesView(View):
    def get(self, request, filename="index.html"):
        if ".." in filename:
            raise Http404

        if filename.startswith("uploads/"):
            # Only registered profile images are public. Other uploaded files
            # can contain sensitive clinical documents and must use protected APIs.
            relative_name = filename.removeprefix("uploads/")
            if "/" in relative_name or "\\" in relative_name:
                raise Http404
            if os.path.splitext(relative_name)[1].lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                raise Http404
            from apps.authentication.models import Register

            if not Register.objects.filter(fotoPerfil=relative_name).exists():
                raise Http404
            try:
                safe_path = safe_join(settings.MEDIA_ROOT, filename)
            except (ValueError, SuspiciousOperation):
                raise Http404
            if not os.path.isfile(safe_path):
                raise Http404
            ext = os.path.splitext(safe_path)[1].lower()
            content_type = MIME_OVERRIDES.get(ext) or mimetypes.guess_type(safe_path)[0] or "application/octet-stream"
            response = FileResponse(open(safe_path, "rb"), content_type=content_type)
            response["Cache-Control"] = "max-age=86400"
            response["X-Content-Type-Options"] = "nosniff"
            return response

        user_role = request.session.get("rol")
        if filename.startswith("legal/"):
            page = filename.removeprefix("legal/").removesuffix("/")
            if page in PAGES_LEGAL:
                info = PAGES_LEGAL[page]
                return render(request, info["template"], {"title": info["title"], "updated": "18 de junio de 2026"})
            return HttpResponseRedirect("/")

        preview = settings.DEBUG and getattr(settings, "ALLOW_PAGE_PREVIEW_WITHOUT_SESSION", False)
        if not preview:
            if filename == "admin.dashboard.html" or filename.startswith("aside-admin/"):
                if user_role is None:
                    return HttpResponseRedirect("/login.html")
                if user_role != "admin":
                    raise PermissionDenied
            elif filename == "patient.dashboard.html" or filename.startswith("aside-patient/"):
                if user_role is None:
                    return HttpResponseRedirect("/login.html")
                if user_role != "paciente":
                    raise PermissionDenied
            elif filename == "professional.dashboard.html" or filename.startswith("aside-professional/"):
                if user_role is None:
                    return HttpResponseRedirect("/login.html")
                if user_role != "profesional":
                    raise PermissionDenied

        root = _template_root()
        if filename in DIRECT_MAP:
            return render(request, DIRECT_MAP[filename])

        template_dirs = (
            ("aside-admin/", "admin/aside-admin/"),
            ("aside-patient/", "patient/aside-patient/"),
            ("aside-professional/", "professional/aside-professional/"),
        )
        for prefix, template_prefix in template_dirs:
            if filename.startswith(prefix):
                rel = template_prefix + filename.removeprefix(prefix)
                try:
                    resolved = safe_join(root, rel)
                except (ValueError, SuspiciousOperation):
                    raise Http404
                if os.path.exists(resolved):
                    return render(request, rel)

        try:
            resolved_root = safe_join(root, filename)
        except (ValueError, SuspiciousOperation):
            raise Http404
        if os.path.exists(resolved_root):
            return render(request, filename)

        static_root = _static_root()
        try:
            file_path = safe_join(static_root, filename)
        except (ValueError, SuspiciousOperation):
            raise Http404
        if not os.path.isfile(file_path):
            raise Http404

        if settings.DEBUG:
            cache_max_age = 60
        elif filename.startswith("uploads/"):
            cache_max_age = 0
        elif any(filename.startswith(prefix) for prefix in ("css/", "js/", "img/", "responsive/")):
            cache_max_age = 86400
        else:
            cache_max_age = None

        ext = os.path.splitext(file_path)[1].lower()
        content_type = MIME_OVERRIDES.get(ext) or mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        response = FileResponse(open(file_path, "rb"), content_type=content_type)
        if cache_max_age is not None:
            response["Cache-Control"] = f"max-age={cache_max_age}"
        return response

def serve_public_qr(request, filename):
    """Serve only professional payment QR images from public media."""
    try:
        file_path = safe_join(settings.MEDIA_ROOT, "qr_codes", filename)
    except (ValueError, SuspiciousOperation):
        raise Http404
    if not os.path.isfile(file_path) or os.path.splitext(file_path)[1].lower() not in {
        ".png", ".jpg", ".jpeg", ".webp"
    }:
        raise Http404
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    response = FileResponse(open(file_path, "rb"), content_type=content_type)
    response["Cache-Control"] = "public, max-age=86400"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)


def error_403(request, exception=None):
    return render(request, "403.html", status=403)


def _notificacion_prueba(request):
    """Envía una notificación de prueba al paciente autenticado."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    uid = request.session.get("idUsuario")
    if not uid:
        return JsonResponse({"success": False, "message": "Debes iniciar sesión"}, status=401)

    from apps.authentication.models import Register
    from apps.patients.models import PerfilPaciente

    user = Register.objects.filter(
        idUsuario=uid, rol="paciente", activo=True, estadoCuenta="Activa"
    ).first()
    if not user:
        return JsonResponse({"success": False, "message": "No autorizado"}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"success": False, "message": "Datos inválidos"}, status=400)

    canal = (data.get("canal") or "whatsapp").strip().lower()
    numero = (data.get("numero") or "").strip()

    if canal == "whatsapp":
        if not numero:
            return JsonResponse({"error": "Número requerido"}, status=400)
        perfil = PerfilPaciente.objects.filter(idPaciente_id=uid).first()

        def normalizar(value):
            digits = "".join(c for c in value if c.isdigit())
            return "57" + digits if len(digits) == 10 and digits.startswith("3") else digits

        if (
            not perfil
            or not perfil.whatsappConsentimiento
            or perfil.canalNotificacion not in ("whatsapp", "ambos")
            or normalizar(numero) != normalizar(perfil.numeroTelefonico or "")
        ):
            return JsonResponse(
                {"success": False, "message": "Solo puedes probar WhatsApp en tu número con consentimiento activo"},
                status=403,
            )
        from apps.core.notifier import enviar_prueba
        ok, msg = enviar_prueba(perfil.numeroTelefonico)
        return JsonResponse(
            {"success": ok, "ok": ok, "message": msg, "mensaje": msg},
            status=200 if ok else 500,
        )

    if canal == "email":
        from django.conf import settings
        from django.core.mail import send_mail

        try:
            subject = "[PsyAI] Prueba de notificación por correo"
            message = f"Hola {user.nombre},\n\nEste es un correo de prueba desde PsyAI Connect."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            return JsonResponse({"success": True, "ok": True, "message": "Correo de prueba enviado", "mensaje": "Correo de prueba enviado"})
        except Exception:
            return JsonResponse({"success": False, "ok": False, "message": "No se pudo enviar el correo", "mensaje": "No se pudo enviar el correo"}, status=500)

    return JsonResponse({"error": "Canal no soportado"}, status=400)


@method_decorator(csrf_protect, name="dispatch")
class NotificacionPruebaView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        return _notificacion_prueba(request)

    def get(self, request):
        return JsonResponse({"error": "Method not allowed"}, status=405)


def notificacion_prueba(request):
    return _notificacion_prueba(request)


@method_decorator(csrf_exempt, name="dispatch")
class ConfigPagoView(APIView):
    authentication_classes = []
    permission_classes = []

    """Public endpoint returning manual payment config."""

    def get(self, request):
        url = (getattr(settings, "PAGO_CUENTA_URL", "") or "").strip()
        nombre = (getattr(settings, "PAGO_CUENTA_NOMBRE", "") or "").strip()
        parsed_url = urlparse(url)
        configurada = parsed_url.scheme.lower() == "https" and bool(parsed_url.netloc)
        if not configurada:
            url = ""
            nombre = ""
        return JsonResponse({
            "url": url,
            "nombre": nombre,
            "configurada": configurada
        })

    def post(self, request):
        return JsonResponse({"error": "Method not allowed"}, status=405)


@method_decorator(csrf_exempt, name="dispatch")
class ThemePreferenceView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Datos invalidos"}, status=400)

        theme = (data.get("theme") or "").strip().lower()
        if theme not in ("light", "dark"):
            return JsonResponse({"error": "Tema invalido"}, status=400)

        response = JsonResponse({"status": "ok", "theme": theme})
        response.set_cookie("theme", theme, max_age=365 * 24 * 60 * 60, path="/", samesite="Lax")
        return response

    def get(self, request):
        return JsonResponse({"error": "Method not allowed"}, status=405)


@method_decorator(csrf_exempt, name="dispatch")
class NewsletterSubscribeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            data = json.loads(request.body)
            email = (data.get("email") or "").strip().lower()
        except Exception:
            return JsonResponse({"error": "Datos invalidos"}, status=400)

        payload, status = core_service.subscribe_newsletter(email)
        return JsonResponse(payload, status=status)

    def get(self, request):
        return JsonResponse({"error": "Method not allowed"}, status=405)


# â”€â”€ Aliases de compatibilidad hacia atrÃ¡s (no eliminar) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
health_check = HealthCheckView.as_view()
client_errors = ClientErrorsView.as_view()
serve_pages = ServePagesView.as_view()
config_pago = ConfigPagoView.as_view()
theme_preference = ThemePreferenceView.as_view()
newsletter_subscribe = NewsletterSubscribeView.as_view()
