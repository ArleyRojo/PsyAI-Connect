import re
from rest_framework import serializers
from .models import PerfilPaciente


class PerfilPacienteSerializer(serializers.Serializer):
    idUsuario = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(max_length=120, required=False)
    email = serializers.EmailField(required=False)
    numeroTelefonico = serializers.CharField(max_length=20, required=False, allow_blank=True)
    fechaNacimiento = serializers.DateField(required=False, allow_null=True)
    genero = serializers.CharField(max_length=20, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)
    # Nuevos campos de preferencias de notificación
    canalNotificacion = serializers.ChoiceField(
        choices=PerfilPaciente.CANAL_CHOICES, required=False)
    whatsappConsentimiento = serializers.BooleanField(required=False)
    whatsappConsentimientoFecha = serializers.DateTimeField(read_only=True)
    recibirRecordatorioCita = serializers.BooleanField(required=False)
    recibirConfirmacion = serializers.BooleanField(required=False)
    recibirMensajePro = serializers.BooleanField(required=False)

    def validate(self, attrs):
        canal = attrs.get("canalNotificacion",
                          getattr(self.instance, "canalNotificacion", "email"))
        tel = attrs.get("numeroTelefonico",
                        getattr(self.instance, "numeroTelefonico", "") if self.instance else "")
        consent = attrs.get("whatsappConsentimiento",
                            getattr(self.instance, "whatsappConsentimiento", False))

        # Normalizar a E.164
        if tel:
            tel_clean = re.sub(r"\D", "", tel)
            if tel.startswith("+"):
                tel = "+" + tel_clean
            elif len(tel_clean) == 10:
                tel = "+57" + tel_clean
            elif len(tel_clean) > 10:
                tel = "+" + tel_clean
            else:
                raise serializers.ValidationError(
                    {"numeroTelefonico": "Formato internacional requerido (+57…)"})
            attrs["numeroTelefonico"] = tel

        if canal in ("whatsapp", "ambos"):
            if not tel:
                raise serializers.ValidationError(
                    {"numeroTelefonico": "Teléfono obligatorio para WhatsApp"})
            if not consent:
                raise serializers.ValidationError(
                    {"whatsappConsentimiento": "Debe aceptar el consentimiento WhatsApp"})

        return attrs


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
