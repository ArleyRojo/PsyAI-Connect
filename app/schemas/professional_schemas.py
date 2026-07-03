from app.schemas.base import BaseSchema, Field
from app.utils.validators import Validator


class ProfessionalProfileSchema(BaseSchema):
    _fields = {
        "nombre": Field(required=False, validate=[lambda v: Validator.required(v, "nombre")]),
        "email": Field(required=False, validate=[lambda v: Validator.email(v)]),
        "telefono": Field(required=False, default=None),
        "especialidad": Field(required=False, default=None),
        "titulo": Field(required=False, default=None),
        "experiencia": Field(field_type=int, required=False, default=None, validate=[lambda v: Validator.positive_integer(v, "experiencia")]),
        "precioConsulta": Field(field_type=float, required=False, default=None),
        "genero": Field(required=False, default=None),
        "edad": Field(field_type=int, required=False, default=None, validate=[lambda v: Validator.positive_integer(v, "edad")]),
    }


class DisponibilidadSchema(BaseSchema):
    _fields = {
        "fecha": Field(validate=[lambda v: Validator.required(v, "fecha")]),
        "hora_inicio": Field(validate=[lambda v: Validator.time(v, "hora_inicio")]),
        "hora_fin": Field(validate=[lambda v: Validator.time(v, "hora_fin")]),
    }


class DiagnosticoSchema(BaseSchema):
    _fields = {
        "diagnostico": Field(required=False, default=None),
        "tratamiento": Field(required=False, default=None),
    }
