from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import resolve, Resolver404
from django.utils.deprecation import MiddlewareMixin

from apps.authentication.models import Register


EXEMPT_PATHS = {
    "/static/",
    "/healthz/",
    "/api/login",
    "/api/logout",
    "/login.html",
    "/favicon.ico",
    "/api/session",
    "/api/csrf",
}


def _is_exempt(request):
    path = request.path
    if any(path.startswith(p) for p in EXEMPT_PATHS):
        return True
    # allow public legal pages
    if path.startswith("/legal/"):
        return True
    # allow uploads and media (they are served via serve_pages)
    if path.startswith("/uploads/"):
        return True
    return False


def _wants_json(request):
    accept = request.META.get("HTTP_ACCEPT", "")
    xrw = request.META.get("HTTP_X_REQUESTED_WITH", "")
    return (
        "application/json" in accept
        or xrw == "XMLHttpRequest"
        or request.META.get("CONTENT_TYPE", "").startswith("application/json")
        or request.META.get("HTTP_ACCEPT", "").startswith("text/event-stream")
    )


class AccountStatusMiddleware(MiddlewareMixin):
    """
    Middleware que verifica el estado de la cuenta (activo/estadoCuenta)
    en cada request autenticado. Si la cuenta está suspendida, cierra la
    sesión y devuelve 403 JSON o redirige a login con ?suspendida=1.
    """

    def process_request(self, request):
        if _is_exempt(request):
            return None

        user_id = request.session.get("idUsuario")
        if not user_id:
            return None

        # Consulta ligera a BD
        try:
            user = Register.objects.only("activo", "estadoCuenta").get(pk=user_id)
        except Register.DoesNotExist:
            request.session.flush()
            if _wants_json(request):
                return JsonResponse(
                    {
                        "success": False,
                        "code": "account_suspended",
                        "message": "Tu cuenta ha sido suspendida. Contacta al administrador.",
                    },
                    status=403,
                )
            return redirect("/login.html?suspendida=1")

        if not user.activo or user.estadoCuenta != "Activa":
            request.session.flush()
            if _wants_json(request):
                return JsonResponse(
                    {
                        "success": False,
                        "code": "account_suspended",
                        "message": "Tu cuenta ha sido suspendida. Contacta al administrador.",
                    },
                    status=403,
                )
            return redirect("/login.html?suspendida=1")

        return None