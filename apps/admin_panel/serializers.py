from rest_framework import serializers


class AdminUsuarioCreateSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=120, required=False, default="")
    email = serializers.EmailField(required=False, default="")
    contrasena = serializers.CharField(required=False, default="")
    rol = serializers.CharField(max_length=20, required=False, default="paciente")


class AdminUsuarioUpdateSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=120, required=False, default="")
    email = serializers.EmailField(required=False, default="")
    estado = serializers.CharField(max_length=20, required=False, default="")


class AdminNotificacionCreateSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=200, required=False, default="")
    mensaje = serializers.CharField(required=False, default="")
    tipo = serializers.CharField(max_length=20, required=False, default="info")
    destinatario = serializers.CharField(max_length=200, required=False, default="")
    email_individual = serializers.EmailField(required=False, default="")
    envio = serializers.ChoiceField(choices=["inmediato", "programado"], required=False)
    fecha_programada = serializers.CharField(required=False, default="")


class AdminChatbotConfigSaveSerializer(serializers.Serializer):
    system_prompt = serializers.CharField(required=False)
    tone = serializers.CharField(required=False)
    temperature = serializers.FloatField(required=False)
    top_p = serializers.FloatField(required=False)
    max_tokens = serializers.IntegerField(required=False)
    max_tokens_user = serializers.IntegerField(required=False)
    daily_message_limit = serializers.IntegerField(required=False)


class AdminChatbotRiskTermsSerializer(serializers.Serializer):
    risk_terms = serializers.CharField()
