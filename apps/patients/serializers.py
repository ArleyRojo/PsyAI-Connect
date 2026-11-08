from rest_framework import serializers


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


class ChatMensajeSerializer(serializers.Serializer):
    receptor = serializers.IntegerField()
    mensaje = serializers.CharField(max_length=2000)




class RevocarConsentimientoSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=[
        ("datos_sensibles_ia", "Datos Sensibles e IA"),
        ("whatsapp", "WhatsApp / Notificaciones"),
    ])
    confirmar = serializers.BooleanField(help_text="Confirmar revocación")


class EliminarCuentaSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    confirmar = serializers.BooleanField(help_text="Confirmar que desea eliminar su cuenta permanentemente")
