from rest_framework import serializers


class ChatbotMensajeSerializer(serializers.Serializer):
    mensaje = serializers.CharField(max_length=2000)


class ChatbotEncuestaSerializer(serializers.Serializer):
    utilidad = serializers.BooleanField()
    claridad = serializers.BooleanField()
    recomendaria = serializers.ChoiceField(choices=["si", "no", "tal vez"])
    comentario = serializers.CharField(required=False, allow_blank=True, default="")


class ConsentimientoSerializer(serializers.Serializer):
    consentimiento_chatbot = serializers.BooleanField()


class ChatMensajeSerializer(serializers.Serializer):
    receptor = serializers.IntegerField()
    mensaje = serializers.CharField(max_length=2000)
