from rest_framework import serializers


class PerfilProfesionalSerializer(serializers.Serializer):
    especialidad = serializers.CharField(required=False, allow_blank=True)
    tarjetaProfesional = serializers.CharField(required=False, allow_blank=True)
    numeroRethus = serializers.CharField(required=False, allow_blank=True)
    experiencia = serializers.CharField(required=False, allow_blank=True)
    idUsuario = serializers.IntegerField(required=False)

    def validate(self, attrs):
        # Al menos tarjetaProfesional o numeroRethus es requerido para profesionales
        if not attrs.get("tarjetaProfesional") and not attrs.get("numeroRethus"):
            # Permitir vacío si es actualización parcial (solo se valida si se proporciona)
            if self.instance and not attrs.get("tarjetaProfesional") and not attrs.get("numeroRethus"):
                # No hacer nada, permitir actualización parcial
                pass
        return attrs


class DisponibilidadSerializer(serializers.Serializer):
    dia = serializers.CharField(required=False)
    fecha = serializers.CharField(required=False)
    horaInicio = serializers.CharField(required=False)
    horaFin = serializers.CharField(required=False)
    hora_inicio = serializers.CharField(required=False)
    hora_fin = serializers.CharField(required=False)


class DiagnosticoSerializer(serializers.Serializer):
    idPaciente = serializers.IntegerField()
    sintomas = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    diagnostico = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tratamiento = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    fecha_diagnostico = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ReporteCreateSerializer(serializers.Serializer):
    idPaciente = serializers.IntegerField(required=False)
    tipoReporte = serializers.CharField(required=False)
    contenido = serializers.CharField(required=False, allow_blank=True)
    fechaInicio = serializers.DateField(required=False, allow_null=True)
    fechaFin = serializers.DateField(required=False, allow_null=True)
    sintomas = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    diagnostico = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tratamiento = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ReporteUpdateSerializer(serializers.Serializer):
    tipoReporte = serializers.CharField(required=False, allow_blank=True)
    estado = serializers.ChoiceField(choices=("Pendiente", "Completado"), required=False)


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


class ProfessionalPaymentInfoSerializer(serializers.Serializer):
    qr_image = serializers.ImageField(required=False, allow_null=True)
    mensaje_texto = serializers.CharField(required=False, allow_blank=True)
