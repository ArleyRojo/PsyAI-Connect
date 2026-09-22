from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    rol = serializers.ChoiceField(
        choices=["paciente", "profesional", "admin"], default="paciente"
    )
    genero = serializers.CharField()
    edad = serializers.IntegerField(required=False, min_value=1, max_value=120)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Las contraseñas no coinciden")
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
