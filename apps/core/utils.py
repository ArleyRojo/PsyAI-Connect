import logging
import zipfile
from datetime import timezone as dt_tz
from io import BytesIO

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger(__name__)

# Zona horaria de Colombia
try:
    from zoneinfo import ZoneInfo
    BOGOTA_TZ = ZoneInfo("America/Bogota")
except ImportError:
    # Fallback para Python < 3.9
    BOGOTA_TZ = timezone.get_fixed_timezone(-300)  # UTC-5


class DateTimeHelper:
    """Utilidades de fecha/hora en zona horaria de Bogotá (America/Bogota)."""

    @staticmethod
    def fmt_bogota(dt):
        """
        Convierte un datetime a zona horaria de Bogotá y lo formatea como dd/mm/YYYY HH:MM.

        Args:
            dt: datetime (aware o naive). Si es naive, se asume UTC.

        Returns:
            str: Fecha formateada en zona horaria de Bogotá, o "" si dt es None.
        """
        if not dt:
            return ""

        # Si es naive, asumir UTC
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, dt_tz.utc)

        # Convertir a Bogotá
        dt = dt.astimezone(BOGOTA_TZ)
        return dt.strftime("%d/%m/%Y %H:%M")

    @staticmethod
    def fmt_bogota_short(dt):
        """Formato corto: dd/mm/YYYY."""
        if not dt:
            return ""
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, dt_tz.utc)
        dt = dt.astimezone(BOGOTA_TZ)
        return dt.strftime("%d/%m/%Y")

    @staticmethod
    def fmt_bogota_time(dt):
        """Solo hora: HH:MM."""
        if not dt:
            return ""
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, dt_tz.utc)
        dt = dt.astimezone(BOGOTA_TZ)
        return dt.strftime("%H:%M")

    @staticmethod
    def to_bogota(dt):
        """
        Convierte un datetime a zona horaria de Bogotá (retorna datetime aware).
        """
        if not dt:
            return None
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, dt_tz.utc)
        return dt.astimezone(BOGOTA_TZ)

    @staticmethod
    def parse_bogota_datetime(value):
        """
        Parsea un string 'YYYY-MM-DDTHH:MM' (de input datetime-local)
        como hora de Bogotá y lo convierte a UTC para guardar en BD.

        Args:
            value: string en formato 'YYYY-MM-DDTHH:MM'

        Returns:
            datetime aware en UTC, o None si value es falsy.
        """
        if not value:
            return None

        # Parsear como naive y luego asignar zona de Bogotá
        naive = timezone.datetime.fromisoformat(value)
        aware = timezone.make_aware(naive, BOGOTA_TZ)

        # Convertir a UTC para almacenar
        return aware.astimezone(dt_tz.utc)


class FileValidator:
    """Validador de archivos subidos."""

    DOC_MAGIC_BYTES = {
        "jpg": (b"\xff\xd8\xff",),
        "jpeg": (b"\xff\xd8\xff",),
        "png": (b"\x89\x50\x4e\x47",),
        "gif": (b"\x47\x49\x46\x38",),
        "webp": (b"\x52\x49\x46\x46",),
        "pdf": (b"%PDF",),
    }

    def __init__(self, allowed_extensions=None, max_size_mb=None, use_magic_bytes=True):
        self.allowed_extensions = allowed_extensions or settings.ALLOWED_UPLOAD_EXTENSIONS
        self.max_size_mb = max_size_mb or settings.MAX_UPLOAD_SIZE_MB
        self.use_magic_bytes = use_magic_bytes

    def _is_docx(self, file_obj):
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

    def validate(self, file):
        """
        Valida un archivo subido.

        Returns:
            (name, None) si es válido, o (None, error_message) si no.
        """
        name = file.name or ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in self.allowed_extensions:
            return None, f"Extensión no permitida: .{ext}"

        max_size = self.max_size_mb * 1024 * 1024
        if hasattr(file, "size") and file.size > max_size:
            return None, f"El archivo excede el tamaño máximo de {self.max_size_mb}MB"

        if self.use_magic_bytes:
            raw = file.read(4096)
            file.seek(0)

            expected = self.DOC_MAGIC_BYTES.get(ext)
            if expected and not any(raw.startswith(sig) for sig in expected):
                if ext in ("docx", "doc") and self._is_docx(file):
                    pass
                else:
                    return None, f"El archivo no coincide con el formato esperado (.{ext})"

        return name, None


class AuthHelper:
    """Utilidades de autenticación basada en sesión."""

    @staticmethod
    def get_current_user(request):
        id_usuario = request.session.get("idUsuario")
        if not id_usuario:
            return None
        return {
            "idUsuario": id_usuario,
            "rol": (request.session.get("rol") or "").strip().lower(),
            "nombre": request.session.get("nombre"),
        }

    @staticmethod
    def require_auth(request):
        user = AuthHelper.get_current_user(request)
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

    @staticmethod
    def require_role(request, *roles):
        user, err = AuthHelper.require_auth(request)
        if err:
            return None, err
        if user["rol"] not in roles:
            return None, JsonResponse(
                {"success": False, "message": "No autorizado"}, status=403
            )
        return user, None


# ── Instancias listas para usar ─────────────────────────────────────────────
datetime_helper = DateTimeHelper()
file_validator = FileValidator()
auth_helper = AuthHelper()


# ── Aliases de compatibilidad hacia atrás (no eliminar) ─────────────────────
fmt_bogota = DateTimeHelper.fmt_bogota
fmt_bogota_short = DateTimeHelper.fmt_bogota_short
fmt_bogota_time = DateTimeHelper.fmt_bogota_time
to_bogota = DateTimeHelper.to_bogota
parse_bogota_datetime = DateTimeHelper.parse_bogota_datetime


def validate_file_upload(file, allowed_extensions=None, use_magic_bytes=True):
    """Wrapper de compatibilidad que mantiene la firma original."""
    validator = FileValidator(
        allowed_extensions=allowed_extensions,
        use_magic_bytes=use_magic_bytes,
    )
    return validator.validate(file)


get_current_user = AuthHelper.get_current_user
require_auth = AuthHelper.require_auth
require_role = AuthHelper.require_role
