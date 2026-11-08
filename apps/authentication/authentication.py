import logging
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


class _CSRFCheck:
    """
    Wrapper around CsrfViewMiddleware that raises PermissionDenied
    instead of returning an HttpResponseForbidden.
    """
    def __init__(self):
        self._middleware = CsrfViewMiddleware(lambda request: None)

    def process_request(self, request):
        return self._middleware.process_request(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        return self._middleware.process_view(request, view_func, view_args, view_kwargs)


class CsrfEnforcedSessionAuthentication(SessionAuthentication):
    """
    Autenticación de sesión DRF que SIEMPRE exige CSRF en peticiones
    no seguras (POST, PUT, PATCH, DELETE) para usuarios autenticados.

    - Para usuarios sin sesión válida → 401 (NotAuthenticated)
    - Para usuarios con sesión pero CSRF inválido/faltante → 403 (PermissionDenied)
    - Para métodos seguros (GET, HEAD, OPTIONS, TRACE) → sin CSRF
    """

    def authenticate_header(self, request):
        """
        DRF llama a este método cuando lanza NotAuthenticated.
        Al definirlo, DRF responde 401 en lugar de 403.
        """
        return "Session"

    def enforce_csrf(self, request):
        """
        Verifica el token CSRF en peticiones no seguras.
        Se ejecuta solo si el usuario tiene sesión activa (idUsuario en session).
        """
        if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            return

        # Verificar si hay sesión activa (nuestro indicador manual)
        if not request.session.get("idUsuario"):
            return

        # Usar el middleware CSRF de Django para validar
        csrf_check = _CSRFCheck()
        # process_request es necesario para que CsrfViewMiddleware haga su trabajo
        csrf_check.process_request(request)
        # process_view lanza PermissionDenied si falla
        csrf_check.process_view(request, None, (), {})

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

        # Validar CSRF para peticiones no seguras una vez autenticado
        self.enforce_csrf(request)

        return (user, None)
