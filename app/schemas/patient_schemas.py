from app.schemas.base import BaseSchema, Field
from app.utils.validators import Validator


class PatientProfileSchema(BaseSchema):
    _fields = {
        "nombre": Field(required=False, validate=[lambda v: Validator.required(v, "nombre")]),
        "email": Field(required=False, validate=[lambda v: Validator.email(v)]),
        "telefono": Field(required=False, default=None),
        "direccion": Field(required=False, default=None),
        "fechaNacimiento": Field(required=False, default=None, validate=[lambda v: Validator.date(v, "fechaNacimiento")]),
        "genero": Field(required=False, default=None),
        "edad": Field(field_type=int, required=False, default=None, validate=[lambda v: Validator.positive_integer(v, "edad")]),
        "ocupacion": Field(required=False, default=None),
        "motivoConsulta": Field(required=False, default=None),
    }


class ChatbotConsentSchema(BaseSchema):
    _fields = {
        "consentimiento_chatbot": Field(field_type=bool),
    }


class EvolutionSchema(BaseSchema):
    _fields = {
        "evolucion": Field(validate=[lambda v: Validator.required(v, "evolucion")]),
        "fecha": Field(required=False, default=None, validate=[lambda v: Validator.date(v, "fecha")]),
    }


class ChatbotSurveySchema(BaseSchema):
    _fields = {
        "respuesta1": Field(required=False, default=None),
        "respuesta2": Field(required=False, default=None),
        "respuesta3": Field(required=False, default=None),
        "comentario": Field(required=False, default=None),
    }
