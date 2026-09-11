from rest_framework import serializers


class CitaCreateSerializer(serializers.Serializer):
    idProfesional = serializers.IntegerField()
    fecha = serializers.CharField(max_length=10)
    hora = serializers.CharField(max_length=5)
    motivo = serializers.CharField(required=False, allow_blank=True, default="")
    tipoCita = serializers.CharField(required=False, allow_blank=True, default="")
    creado_por_profesional = serializers.BooleanField(required=False, default=False)
    idPaciente = serializers.IntegerField(required=False)


class CitaUpdateStatusSerializer(serializers.Serializer):
    estado = serializers.CharField(max_length=20)


class CitaCancelSerializer(serializers.Serializer):
    motivoCancelacion = serializers.CharField(required=False, allow_blank=True, default="")
