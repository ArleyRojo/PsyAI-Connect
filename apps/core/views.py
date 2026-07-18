import mimetypes
import os

from django.conf import settings
from django.http import (
    FileResponse,
    Http404,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


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
    "recover.html": "auth/recover.html",
    "reset-password.html": "auth/reset-password.html",
    "admin.dashboard.html": "admin/admin.dashboard.html",
    "patient.dashboard.html": "patient/patient.dashboard.html",
    "professional.dashboard.html": "professional/professional.dashboard.html",
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
    try:
        import json
        data = json.loads(request.body)
        print(f"[ClientError] {data.get('type', 'unknown')}: {data.get('message', '')} | {data.get('details', '')} | page={data.get('page', '')}")
    except Exception:
        pass
    return JsonResponse({"status": "ok"})


def serve_pages(request, filename):
    user_role = request.session.get("rol")

    if filename.startswith("legal/"):
        page = filename.removeprefix("legal/").removesuffix("/")
        if page in PAGES_LEGAL:
            info = PAGES_LEGAL[page]
            return render(request, info["template"], {"title": info["title"], "updated": "18 de junio de 2026"})
        return HttpResponseRedirect("/")

    if filename == "admin.dashboard.html" or filename.startswith("aside-admin/"):
        if user_role != "admin":
            return HttpResponseRedirect("/login.html")

    if filename == "patient.dashboard.html" or filename.startswith("aside-patient/"):
        if user_role != "paciente":
            return HttpResponseRedirect("/login.html")

    if filename == "professional.dashboard.html" or filename.startswith("aside-professional/"):
        if user_role != "profesional":
            return HttpResponseRedirect("/login.html")

    root = _template_root()

    if filename in DIRECT_MAP:
        return render(request, DIRECT_MAP[filename])

    if filename.startswith("aside-admin/"):
        rel = "admin/aside-admin/" + filename.removeprefix("aside-admin/")
        if os.path.exists(os.path.join(root, *rel.split("/"))):
            return render(request, rel)

    if filename.startswith("aside-patient/"):
        rel = "patient/aside-patient/" + filename.removeprefix("aside-patient/")
        if os.path.exists(os.path.join(root, *rel.split("/"))):
            return render(request, rel)

    if filename.startswith("aside-professional/"):
        rel = "professional/aside-professional/" + filename.removeprefix("aside-professional/")
        if os.path.exists(os.path.join(root, *rel.split("/"))):
            return render(request, rel)

    if os.path.exists(os.path.join(root, filename)):
        return render(request, filename)

    static_root = _static_root()
    file_path = os.path.join(static_root, filename)

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

    MIME_OVERRIDES = {
        ".js": "text/javascript",
        ".css": "text/css",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".woff2": "font/woff2",
    }
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
