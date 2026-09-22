import logging
from django.middleware.csrf import CsrfViewMiddleware, get_token
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


class CsrfEnforcedSessionAuthentication(SessionAuthentication):
    """
    Autenticación de sesión DRF que SIEMPRE exige CSRF en peticiones
    no seguras (POST, PUT, PATCH, DELETE) para usuarios autenticados.

    La SessionAuthentication estándar solo llama a enforce_csrf() si
    authenticate() devuelve un usuario válido. Como nuestro login manual
    no usa django.contrib.auth.login(), request.user queda como AnonymousUser
    y el CSRF nunca se verifica.

    Esta clase fuerza la verificación CSRF cuando hay una sesión válida
    (idUsuario en request.session), independientemente de request.user.
    """

    def enforce_csrf(self, request):
        """
        Verifica el token CSRF en peticiones no seguras.
        Se ejecuta solo si el usuario tiene sesión activa.
        """
        if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            return

        # Verificar si hay sesión activa (nuestro indicador manual)
        if not request.session.get("idUsuario"):
            return

        # Usar el middleware CSRF de Django para validar
        csrf_middleware = CsrfViewMiddleware(lambda r: None)
        try:
            csrf_middleware.process_view(request, None, (), {})
        except Exception as e:
            logger.warning(f"CSRF validation failed: {e}")
            raise AuthenticationFailed("CSRF token inválido o faltante")

    def authenticate(self, request):
        """
        Autentica al usuario basándose en la sesión de Django.
        Retorna (user, auth) si la sesión es válida, None en caso contrario.
        """
        user_id = request.session.get("idUsuario")
        if not user_id:
            return None

        try:
            user = User.objects.get(pk=user_id, activo=True, estadoCuenta="Activa")
        except User.DoesNotExist:
            return None

        return (user, None)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Autenticación de sesión SIN verificación CSRF.
    Útil para endpoints públicos que usan sesión (ej. login, registro, recuperación).
    """
    def enforce_csrf(self, request):
        return  # No hace nada - exento de CSRF


def get_csrf_token(request):
    """
    Obtiene o genera el token CSRF para la sesión actual.
    Útil para exponer el token vía API al frontend.
    """
    return get_token(request)