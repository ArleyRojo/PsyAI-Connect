from rest_framework import serializers


class PerfilPacienteSerializer(serializers.Serializer):
    idUsuario = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(max_length=120, required=False)
    email = serializers.EmailField(required=False)
    numeroTelefonico = serializers.CharField(max_length=20, required=False, allow_blank=True)
    fechaNacimiento = serializers.DateField(required=False, allow_null=True)
    genero = serializers.CharField(max_length=20, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)


class PreferenciasSerializer(serializers.Serializer):
    notificaciones = serializers.BooleanField(required=False)
    tema = serializers.CharField(max_length=20, required=False)
    idioma = serializers.CharField(max_length=10, required=False)


class EvolucionSerializer(serializers.Serializer):
    estadoEmocional = serializers.CharField(max_length=50, required=False)
    nivelEnergia = serializers.IntegerField(required=False, min_value=1, max_value=10)
    notasPersonales = serializers.CharField(required=False, allow_blank=True)
    fecha = serializers.DateField(required=False)


class PacienteListSerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    limit = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)


class ChatbotMessageSerializer(serializers.Serializer):
    mensaje = serializers.CharField(max_length=2000)


class ChatbotEncuestaSerializer(serializers.Serializer):
    utilidad = serializers.BooleanField()
    claridad = serializers.BooleanField()
    recomendaria = serializers.ChoiceField(choices=["si", "no", "tal vez"])
    comentario = serializers.CharField(required=False, allow_blank=True, default="")


class ConsentimientoSerializer(serializers.Serializer):
    consentimiento_chatbot = serializers.BooleanField()


class DocumentoUploadSerializer(serializers.Serializer):
    archivo = serializers.FileField()
    descripcion = serializers.CharField(required=False, allow_blank=True, default="")


class DocumentoAutorizacionSerializer(serializers.Serializer):
    profesionalId = serializers.IntegerField(required=False)
    autorizar = serializers.BooleanField(required=False, allow_null=True)


class ChatMensajeSerializer(serializers.Serializer):
    receptor = serializers.IntegerField()
    mensaje = serializers.CharField(max_length=2000)
