import mimetypes
import os

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
from django.views.decorators.csrf import csrf_exempt

from apps.core.services import log_client_error, subscribe_newsletter

UPLOADS_DIR = os.path.join(settings.MEDIA_ROOT, "uploads")

MIME_OVERRIDES = {
    ".js": "text/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
}


def _template_root():
    return os.path.join(settings.BASE_DIR, "templates")


def _static_root():
    return settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else os.path.join(settings.BASE_DIR, "static")


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


@csrf_exempt
def health_check(request):
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


@csrf_exempt
def client_errors(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    log_client_error(request.body)
    return JsonResponse({"status": "ok"})


def serve_pages(request, filename):
    if ".." in filename:
        raise Http404

    if filename.startswith("uploads/"):
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
        return response

    user_role = request.session.get("rol")

    if filename.startswith("legal/"):
        page = filename.removeprefix("legal/").removesuffix("/")
        if page in PAGES_LEGAL:
            info = PAGES_LEGAL[page]
            return render(request, info["template"], {"title": info["title"], "updated": "18 de junio de 2026"})
        return HttpResponseRedirect("/")

    if settings.DEBUG:
        # En desarrollo permitimos abrir las pantallas protegidas sin sesión para
        # facilitar la vista previa del frontend y la depuración local.
        pass
    elif filename == "admin.dashboard.html" or filename.startswith("aside-admin/"):
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

    if filename.startswith("aside-admin/"):
        rel = "admin/aside-admin/" + filename.removeprefix("aside-admin/")
        try:
            resolved = safe_join(root, rel)
        except (ValueError, SuspiciousOperation):
            raise Http404
        if os.path.exists(resolved):
            return render(request, rel)

    if filename.startswith("aside-patient/"):
        rel = "patient/aside-patient/" + filename.removeprefix("aside-patient/")
        try:
            resolved = safe_join(root, rel)
        except (ValueError, SuspiciousOperation):
            raise Http404
        if os.path.exists(resolved):
            return render(request, rel)

    if filename.startswith("aside-professional/"):
        rel = "professional/aside-professional/" + filename.removeprefix("aside-professional/")
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
    elif any(filename.startswith(p) for p in ("css/", "js/", "img/", "responsive/")):
        cache_max_age = 86400
    else:
        cache_max_age = None

    ext = os.path.splitext(file_path)[1].lower()
    content_type = MIME_OVERRIDES.get(ext) or mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    response = FileResponse(open(file_path, "rb"), content_type=content_type)
    if cache_max_age is not None:
        response["Cache-Control"] = f"max-age={cache_max_age}"
    return response


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)


def error_403(request, exception=None):
    return render(request, "403.html", status=403)


@csrf_exempt
def notificacion_prueba(request):
    """POST /api/notificaciones/probar/
    body: { "canal": "whatsapp|email", "numero": "+57300..." }.
    Si canal=email, se usa el email del usuario en sesión.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        import json
        data = json.loads(request.body)
        canal = (data.get("canal") or "whatsapp").strip().lower()
        numero = (data.get("numero") or "").strip()
    except Exception:
        return JsonResponse({"error": "Datos inválidos"}, status=400)

    if canal == "whatsapp":
        if not numero:
            return JsonResponse({"error": "Número requerido"}, status=400)
        from apps.core.notifier import enviar_prueba
        ok, msg = enviar_prueba(numero)
        return JsonResponse({"ok": ok, "mensaje": msg}, status=200 if ok else 500)

    if canal == "email":
        # obtener usuario de la sesión
        uid = request.session.get("idUsuario")
        if not uid:
            return JsonResponse({"error": "Sesión no válida"}, status=401)
        from apps.authentication.models import Register
        from django.core.mail import send_mail
        from django.conf import settings
        try:
            user = Register.objects.get(pk=uid)
        except Register.DoesNotExist:
            return JsonResponse({"error": "Usuario no encontrado"}, status=404)
        try:
            subject = "[PsyAI] Prueba de notificación por correo"
            message = f"Hola {user.nombre},\n\nEste es un correo de prueba desde PsyAI Connect."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            return JsonResponse({"ok": True, "mensaje": "Correo de prueba enviado"})
        except Exception as exc:
            return JsonResponse({"ok": False, "mensaje": str(exc)}, status=500)

    return JsonResponse({"error": "Canal no soportado"}, status=400)


@csrf_exempt
def config_pago(request):
    """Public endpoint returning manual payment config."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    from django.conf import settings
    url = (getattr(settings, "PAGO_CUENTA_URL", "") or "").strip()
    nombre = (getattr(settings, "PAGO_CUENTA_NOMBRE", "") or "").strip()
    # Solo considerar configurada si la URL empieza por https://
    configurada = url.startswith("https://")
    if not configurada:
        url = ""
        nombre = ""
    return JsonResponse({
        "url": url,
        "nombre": nombre,
        "configurada": configurada
    })


@csrf_exempt
def theme_preference(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        import json
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Datos invalidos"}, status=400)

    theme = (data.get("theme") or "").strip().lower()
    if theme not in ("light", "dark"):
        return JsonResponse({"error": "Tema invalido"}, status=400)

    response = JsonResponse({"status": "ok", "theme": theme})
    response.set_cookie("theme", theme, max_age=365 * 24 * 60 * 60, path="/", samesite="Lax")
    return response


@csrf_exempt
def newsletter_subscribe(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        import json
        data = json.loads(request.body)
        email = (data.get("email") or "").strip().lower()
    except Exception:
        return JsonResponse({"error": "Datos invalidos"}, status=400)

    payload, status = subscribe_newsletter(email)
    return JsonResponse(payload, status=status)
