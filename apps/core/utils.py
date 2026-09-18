import logging
import zipfile
from io import BytesIO

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

DOC_MAGIC_BYTES = {
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89\x50\x4e\x47",),
    "gif": (b"\x47\x49\x46\x38",),
    "webp": (b"\x52\x49\x46\x46",),
    "pdf": (b"%PDF",),
}


def _is_docx(file_obj):
    raw = file_obj.read(4096)
    file_obj.seek(0)
    if raw[:2] == b"PK":
        try:
            zf = zipfile.ZipFile(BytesIO(raw))
            zf.close()
            return True
        except (zipfile.BadZipFile, Exception):
            return False
    return False


def validate_file_upload(file, allowed_extensions=None, use_magic_bytes=True):
    if allowed_extensions is None:
        allowed_extensions = settings.ALLOWED_UPLOAD_EXTENSIONS

    name = file.name or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in allowed_extensions:
        return None, f"Extensión no permitida: .{ext}"

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if hasattr(file, "size") and file.size > max_size:
        return None, f"El archivo excede el tamaño máximo de {settings.MAX_UPLOAD_SIZE_MB}MB"

    if use_magic_bytes:
        raw = file.read(4096)
        file.seek(0)

        expected = DOC_MAGIC_BYTES.get(ext)
        if expected and not any(raw.startswith(sig) for sig in expected):
            if ext in ("docx", "doc") and _is_docx(file):
                pass
            else:
                return None, f"El archivo no coincide con el formato esperado (.{ext})"

    return name, None


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

    from apps.authentication.models import Register

    try:
        db_user = Register.objects.get(idUsuario=user["idUsuario"])
    except Register.DoesNotExist:
        request.session.flush()
        return None, JsonResponse(
            {"success": False, "message": "Usuario no encontrado"}, status=401
        )

    if not db_user.activo or db_user.estadoCuenta != "Activa":
        request.session.flush()
        return None, JsonResponse(
            {"success": False, "message": "Tu cuenta ha sido suspendida. Contacta al administrador."},
            status=403,
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
