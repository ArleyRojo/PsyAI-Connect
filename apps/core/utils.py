from django.http import JsonResponse


def get_current_user(request):
    id_usuario = request.session.get("idUsuario")
    if not id_usuario:
        return None
    return {
        "idUsuario": id_usuario,
        "rol": request.session.get("rol"),
        "nombre": request.session.get("nombre"),
    }


def require_auth(request):
    user = get_current_user(request)
    if not user:
        return None, JsonResponse(
            {"success": False, "message": "No autenticado"}, status=401
        )
    return user, None


def require_role(request, *roles):
    user, err = require_auth(request)
    if err:
        return None, err
    if user["rol"] not in roles:
        return None, JsonResponse(
            {"success": False, "message": "No autorizado"}, status=403
        )
    return user, None
