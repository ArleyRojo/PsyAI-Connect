from rest_framework import serializers


class PerfilProfesionalSerializer(serializers.Serializer):
    especialidad = serializers.CharField(required=False, allow_blank=True)
    licencia = serializers.CharField(required=False, allow_blank=True)
    experiencia = serializers.IntegerField(required=False)
    idUsuario = serializers.IntegerField(required=False)


class DisponibilidadSerializer(serializers.Serializer):
    dia = serializers.CharField(required=False)
    fecha = serializers.CharField(required=False)
    horaInicio = serializers.CharField(required=False)
    horaFin = serializers.CharField(required=False)
    hora_inicio = serializers.CharField(required=False)
    hora_fin = serializers.CharField(required=False)


class DiagnosticoSerializer(serializers.Serializer):
    idPaciente = serializers.IntegerField()
    diagnostico = serializers.CharField(required=False, allow_blank=True)


class ReporteCreateSerializer(serializers.Serializer):
    idPaciente = serializers.IntegerField(required=False)
    tipoReporte = serializers.CharField(required=False)
    contenido = serializers.CharField(required=False, allow_blank=True)


class ReporteUpdateSerializer(serializers.Serializer):
    idReporte = serializers.IntegerField(required=False)
    contenido = serializers.CharField(required=False, allow_blank=True)


class DocumentoUploadSerializer(serializers.Serializer):
    archivo = serializers.FileField()
    categoria = serializers.CharField(required=False, default="Otro")
    visibilidad = serializers.CharField(required=False, default="privado")
    notas = serializers.CharField(required=False, allow_blank=True, default="")


class VisibilidadSerializer(serializers.Serializer):
    visibilidad = serializers.CharField()


class ChatMensajeSerializer(serializers.Serializer):
    receptor = serializers.IntegerField()
    mensaje = serializers.CharField(max_length=2000)
