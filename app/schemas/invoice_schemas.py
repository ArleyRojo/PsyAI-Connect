from app.schemas.base import BaseSchema, Field
from app.utils.validators import Validator


class CreateFacturaSchema(BaseSchema):
    _fields = {
        "idPaciente": Field(field_type=int, required=False, default=None, validate=[lambda v: Validator.positive_integer(v, "idPaciente")]),
        "idProfesional": Field(field_type=int, required=False, default=None, validate=[lambda v: Validator.positive_integer(v, "idProfesional")]),
        "monto": Field(field_type=float, required=False, default=None),
        "descripcion": Field(required=False, default=None),
        "metodoPago": Field(required=False, default=None),
    }


class UpdateFacturaSchema(BaseSchema):
    _fields = {
        "estadoPago": Field(required=False),
        "metodoPago": Field(required=False),
        "monto": Field(field_type=float, required=False),
        "descripcion": Field(required=False),
    }
