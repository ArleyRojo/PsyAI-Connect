import re
from typing import Any, Optional


class ValidationError(Exception):
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class Validator:
    @staticmethod
    def required(value: Any, field_name: str) -> Any:
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"El campo '{field_name}' es requerido", field_name)
        return value

    @staticmethod
    def email(value: str, field_name: str = "email") -> str:
        if not value:
            raise ValidationError(f"El campo '{field_name}' es requerido", field_name)
        pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(pattern, value):
            raise ValidationError(f"Formato de '{field_name}' inválido", field_name)
        return value.strip().lower()

    @staticmethod
    def min_length(value: str, min_len: int, field_name: str) -> str:
        if not value or len(value) < min_len:
            raise ValidationError(f"'{field_name}' debe tener al menos {min_len} caracteres", field_name)
        return value

    @staticmethod
    def max_length(value: str, max_len: int, field_name: str) -> str:
        if value and len(value) > max_len:
            raise ValidationError(f"'{field_name}' no puede exceder {max_len} caracteres", field_name)
        return value

    @staticmethod
    def password(value: str) -> str:
        if not value:
            raise ValidationError("La contraseña es requerida", "password")
        if len(value) < 6:
            raise ValidationError("La contraseña debe tener al menos 6 caracteres", "password")
        if not re.search(r'[A-Z]', value):
            raise ValidationError("La contraseña debe contenir al menos una mayúscula", "password")
        if not re.search(r'[0-9]', value):
            raise ValidationError("La contraseña debe contener al menos un número", "password")
        return value

    @staticmethod
    def role(value: str, allowed: tuple = ("paciente", "profesional", "admin")) -> str:
        if value not in allowed:
            raise ValidationError(f"Rol inválido. Roles permitidos: {', '.join(allowed)}", "rol")
        return value

    @staticmethod
    def date(value: str, field_name: str = "fecha") -> str:
        if not value:
            raise ValidationError(f"'{field_name}' es requerida", field_name)
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, value):
            raise ValidationError(f"Formato de '{field_name}' inválido (YYYY-MM-DD)", field_name)
        return value

    @staticmethod
    def time(value: str, field_name: str = "hora") -> str:
        if not value:
            raise ValidationError(f"'{field_name}' es requerida", field_name)
        pattern = r'^([01]?\d|2[0-3]):[0-5]\d$'
        if not re.match(pattern, value):
            raise ValidationError(f"Formato de '{field_name}' inválido (HH:MM)", field_name)
        return value

    @staticmethod
    def integer(value: Any, field_name: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError(f"'{field_name}' debe ser un número entero", field_name)

    @staticmethod
    def positive_integer(value: Any, field_name: str) -> int:
        num = Validator.integer(value, field_name)
        if num <= 0:
            raise ValidationError(f"'{field_name}' debe ser un número positivo", field_name)
        return num


def sanitize_string(value: Optional[str], max_length: int = 1000) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    value = re.sub(r'[<>]', '', value)
    return value[:max_length]