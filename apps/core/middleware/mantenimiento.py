"""
Modo mantenimiento (HU-24).

Cuando el admin lo activa, pacientes, profesionales y visitantes ven la página
"Estamos en mantenimiento" (y las APIs responden 503). El administrador sigue
entrando normal y la página de login sigue disponible para que pueda iniciar sesión.
"""
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

ROLES_ADMIN = {"admin", "administrador"}
# Siempre disponibles: login/logout y lo que el login necesita
API_LIBRES = ("/api/login", "/api/logout", "/api/csrf", "/api/session", "/api/politicas/")
PAGINAS_LIBRES = ("/login.html",)


class MantenimientoMiddleware(MiddlewareMixin):
    def process_request(self, request):
        path = request.path
        es_api = path.startswith("/api/")
        es_pagina = path == "/" or path.endswith(".html")
        if not (es_api or es_pagina):
            return None  # css, js, imágenes, etc.

        from apps.admin_panel.mantenimiento import modo_actual
        activo, mensaje = modo_actual()
        if not activo:
            return None

        session = getattr(request, "session", None)
        rol = ((session.get("rol") if session else None) or "").strip().lower()
        if rol in ROLES_ADMIN:
            return None
        if path.startswith(API_LIBRES) or path in PAGINAS_LIBRES:
            return None

        if es_api:
            return JsonResponse({"success": False, "code": "maintenance", "message": mensaje}, status=503)
        respuesta = render(request, "mantenimiento.html", {"mensaje": mensaje}, status=503)
        respuesta["Retry-After"] = "300"
        return respuesta
