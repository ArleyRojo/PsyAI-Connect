from rest_framework import serializers


class FacturaCreateSerializer(serializers.Serializer):
    idProfesional = serializers.IntegerField(required=False)
    idPaciente = serializers.IntegerField(required=False)
    idCita = serializers.IntegerField(required=False, allow_null=True)
    items = serializers.ListField(
        child=serializers.DictField(), required=True
    )


class FacturaUpdateSerializer(serializers.Serializer):
    anular = serializers.BooleanField(required=False, default=False)
    motivoAnulacion = serializers.CharField(required=False, allow_blank=True, default="")
    estadoPago = serializers.CharField(required=False, allow_null=True)