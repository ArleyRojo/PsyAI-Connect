from app.schemas.base import BaseSchema, Field
from app.utils.validators import Validator


class RegisterSchema(BaseSchema):
    _fields = {
        "nombre": Field(validate=[lambda v: Validator.required(v, "nombre")]),
        "email": Field(validate=[lambda v: Validator.email(v)]),
        "password": Field(validate=[lambda v: Validator.password(v)]),
        "rol": Field(required=False, default="paciente", validate=[lambda v: Validator.role(v)]),
        "genero": Field(required=False, default=None),
        "edad": Field(field_type=int, required=False, default=None, validate=[lambda v: Validator.positive_integer(v, "edad")]),
    }


class LoginSchema(BaseSchema):
    _fields = {
        "email": Field(validate=[lambda v: Validator.required(v, "email")]),
        "password": Field(validate=[lambda v: Validator.required(v, "password")]),
    }


class ForgotPasswordSchema(BaseSchema):
    _fields = {
        "email": Field(validate=[lambda v: Validator.email(v)]),
    }


class ResetPasswordSchema(BaseSchema):
    _fields = {
        "token": Field(validate=[lambda v: Validator.required(v, "token")]),
        "new_password": Field(validate=[lambda v: Validator.password(v)]),
    }
