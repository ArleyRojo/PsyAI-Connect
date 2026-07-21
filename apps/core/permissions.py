import json

from django.http import JsonResponse

from apps.core.utils import require_auth as _require_auth_strong, get_current_user


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
