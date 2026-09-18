import json

from django.http import JsonResponse
from rest_framework.permissions import BasePermission

from apps.core.utils import get_current_user, require_auth as _require_auth_strong


def require_auth(request):
    return _require_auth_strong(request)


def require_role(request, *roles):
    user, err = require_auth(request)
    if err:
        return None, err
    if user["rol"] not in roles:
        return None, JsonResponse(
            {"success": False, "message": "No autorizado"}, status=403
        )
    return user, None


def parse_json_body(request):
    if not request.body:
        return {}, None
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None, JsonResponse(
            {"success": False, "message": "JSON inválido"}, status=400
        )


class IsAuthenticatedDRF(BasePermission):
    def has_permission(self, request, view):
        user = get_current_user(request)
        if not user:
            return False

        from apps.authentication.models import Register

        try:
            db_user = Register.objects.get(idUsuario=user["idUsuario"])
        except Register.DoesNotExist:
            return False

        if not db_user.activo or db_user.estadoCuenta != "Activa":
            return False

        request.user_id = user["idUsuario"]
        request.user_role = user["rol"]
        request.user_name = user["nombre"]
        return True


class IsPaciente(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, "user_role", None) == "paciente"


class IsProfesional(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, "user_role", None) == "profesional"


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, "user_role", None) == "admin"


class IsPacienteOrProfesional(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, "user_role", None) in ("paciente", "profesional")


class IsAdminOrProfesional(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, "user_role", None) in ("admin", "profesional")


class IsOwnerOrStaff(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, "user_role", None) is not None

    def has_object_permission(self, request, view, obj):
        if getattr(request, "user_role", None) in ("admin", "profesional"):
            return True
        return getattr(request, "user_id", None) == getattr(obj, "idUsuario", None)
