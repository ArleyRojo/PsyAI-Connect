"""
Cierre automático de sesión por inactividad (HU-13).

Guarda en la sesión la hora del último request. Si pasan más minutos de los
configurados por el administrador, borra la sesión y el request sigue como
anónimo (las APIs responden 401 y las páginas mandan al login).

El navegador lleva su propio temporizador (inactividad.js) que avisa 1 minuto
antes y cierra la sesión; esto es el respaldo del servidor, por ejemplo si el
usuario cerró la pestaña y vuelve horas después.
"""
import time

from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin

CLAVE = "ultimaActividad"
# Para no escribir la sesión en la base de datos en cada request
GUARDAR_CADA_SEGUNDOS = 30

EXENTAS = ("/static/", "/healthz/", "/api/logout", "/api/csrf", "/favicon.ico")


class InactividadMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith(EXENTAS):
            return None

        session = getattr(request, "session", None)
        if session is None or not session.get("idUsuario"):
            return None

        from apps.admin_panel.seguridad import aplica_a_rol, minutos_inactividad

        rol = session.get("rol") or (session.get("usuario") or {}).get("rol")
        if not aplica_a_rol(rol):
            return None

        ahora = int(time.time())
        ultima = session.get(CLAVE)

        if ultima and ahora - int(ultima) > minutos_inactividad() * 60:
            session.flush()
            request.user = AnonymousUser()
            return None

        if not ultima or ahora - int(ultima) >= GUARDAR_CADA_SEGUNDOS:
            session[CLAVE] = ahora
        return None
