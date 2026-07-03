from typing import Any, Optional
from app.utils.validators import ValidationError


class SchemaValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__(str(errors))


class Field:
    def __init__(
        self,
        field_type: type = str,
        required: bool = True,
        default: Any = None,
        validate: Optional[list] = None,
        dump_only: bool = False,
    ):
        self.field_type = field_type
        self.required = required
        self.default = default
        self.validate = validate or []
        self.dump_only = dump_only

    def coerce(self, value: Any) -> Any:
        if value is None or value == "":
            return self.default
        try:
            if self.field_type is bool:
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "sí")
                return bool(value)
            return self.field_type(value)
        except (TypeError, ValueError):
            raise ValidationError(
                f"Debe ser de tipo {self.field_type.__name__}",
                str(value),
            )


class BaseSchema:
    _fields: dict[str, Field] = {}

    @classmethod
    def get_fields(cls) -> dict[str, Field]:
        return cls._fields

    @classmethod
    def load(cls, data: dict) -> dict:
        validated: dict[str, Any] = {}
        errors: dict[str, str] = {}

        for name, field in cls.get_fields().items():
            if field.dump_only:
                continue

            value = data.get(name)

            if value is None or (isinstance(value, str) and not value.strip()):
                if field.required:
                    errors[name] = f"'{name}' es requerido"
                else:
                    validated[name] = field.default
                continue

            try:
                coerced = field.coerce(value)
                for validator_fn in field.validate:
                    coerced = validator_fn(coerced)
                validated[name] = coerced
            except ValidationError as e:
                errors[name] = e.message if e.message else f"'{name}' inválido"

        if errors:
            raise SchemaValidationError(errors)

        return validated

    @classmethod
    def dump(cls, data: dict) -> dict:
        result = {}
        for name, field in cls.get_fields().items():
            if name in data:
                result[name] = data[name]
        return result
