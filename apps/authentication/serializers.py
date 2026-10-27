from rest_framework import serializers


import re
from datetime import date
from rest_framework import serializers

from django.conf import settings


def calcular_edad(fecha_nacimiento):
    """Calcula la edad a partir de la fecha de nacimiento."""
    hoy = date.today()
    edad = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return edad


class RegisterSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    rol = serializers.ChoiceField(
        choices=["paciente", "profesional", "admin"], default="paciente"
    )
    genero = serializers.CharField()
    fecha_nacimiento = serializers.DateField()
    acepta_terminos = serializers.BooleanField(required=True)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        if not data.get("acepta_terminos"):
            raise serializers.ValidationError("Debes aceptar los términos y la política de privacidad")

        # Validar edad mínima
        edad = calcular_edad(data["fecha_nacimiento"])
        edad_minima = getattr(settings, "EDAD_MINIMA_REGISTRO", 18)
        if edad < edad_minima:
            raise serializers.ValidationError(
                f"Debes tener al menos {edad_minima} años para registrarte"
            )

        return data


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    rol = serializers.ChoiceField(
        choices=["paciente", "profesional", "admin"],
        default="paciente",
        required=False,
    )


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=6)
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return data


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


# ── TOTP / 2FA Serializers ──

class TOTPSetupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False, default="")

class TOTPVerifySerializer(serializers.Serializer):
    token = serializers.CharField(min_length=6, max_length=6)

class TOTPDisableSerializer(serializers.Serializer):
    password = serializers.CharField()
