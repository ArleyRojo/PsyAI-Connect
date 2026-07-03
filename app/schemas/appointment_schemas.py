from app.schemas.base import BaseSchema, Field
from app.utils.validators import Validator


class CreateCitaSchema(BaseSchema):
    _fields = {
        "idProfesional": Field(field_type=int, validate=[lambda v: Validator.positive_integer(v, "idProfesional")]),
        "fecha": Field(validate=[lambda v: Validator.date(v)]),
        "hora": Field(validate=[lambda v: Validator.time(v)]),
        "motivo": Field(validate=[lambda v: Validator.required(v, "motivo")]),
        "idPaciente": Field(field_type=int, required=False, default=None),
    }


class UpdateCitaSchema(BaseSchema):
    _fields = {
        "fecha": Field(required=False, validate=[lambda v: Validator.date(v, "fecha")]),
        "hora": Field(required=False, validate=[lambda v: Validator.time(v, "hora")]),
        "motivo": Field(required=False),
        "estado": Field(required=False),
        "motivoCancelacion": Field(required=False, default=None),
    }
