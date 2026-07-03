import os
import uuid
from flask import current_app


MAGIC_BYTES = {
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89\x50\x4e\x47",),
    "pdf": (b"\x25\x50\x44\x46",),
    "gif": (b"\x47\x49\x46\x38",),
    "webp": (b"\x52\x49\x46\x46",),
    "doc": (b"\xd0\xcf\x11\xe0",),
    "docx": (b"\x50\x4b\x03\x04",),
}


class UploadValidator:
    @staticmethod
    def _check_magic_bytes(data, ext):
        expected_list = MAGIC_BYTES.get(ext)
        if not expected_list:
            return True
        return any(data.startswith(sig) for sig in expected_list)

    @staticmethod
    def validate(file_field, allowed_extensions=None, max_size_mb=None):
        if allowed_extensions is None:
            allowed_extensions = current_app.config.get(
                "ALLOWED_UPLOAD_EXTENSIONS",
                {"jpg", "jpeg", "png", "pdf"},
            )
        if max_size_mb is None:
            max_size_mb = current_app.config.get("MAX_UPLOAD_SIZE_MB", 5)

        if not file_field or not file_field.filename:
            return None, "No se envi\u00f3 ning\u00fan archivo"

        filename = file_field.filename
        ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
        if ext not in allowed_extensions:
            return None, f"Extensi\u00f3n .{ext} no permitida"

        file_field.seek(0, os.SEEK_END)
        size = file_field.tell()
        file_field.seek(0)
        if size > max_size_mb * 1024 * 1024:
            return None, f"El archivo supera los {max_size_mb} MB"

        raw = file_field.read(4096)
        file_field.seek(0)
        if not UploadValidator._check_magic_bytes(raw, ext):
            return None, "El archivo no coincide con el formato esperado (magic bytes inv\u00e1lidos)"

        safe_name = f"{uuid.uuid4().hex}.{ext}"
        return safe_name, None
