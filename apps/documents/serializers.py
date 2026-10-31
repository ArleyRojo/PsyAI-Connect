from rest_framework import serializers


class DocumentoProfesionalUploadSerializer(serializers.Serializer):
    archivo = serializers.FileField()
    categoria = serializers.CharField(required=False, allow_blank=True, default="Otro")
    visibilidad = serializers.CharField(required=False, allow_blank=True, default="privado")
    notasInternas = serializers.CharField(required=False, allow_blank=True, default="")


class DocumentoPacienteUploadSerializer(serializers.Serializer):
    archivo = serializers.FileField()
    descripcion = serializers.CharField(required=False, allow_blank=True, default="")


class AutorizacionToggleSerializer(serializers.Serializer):
    idProfesional = serializers.IntegerField()
