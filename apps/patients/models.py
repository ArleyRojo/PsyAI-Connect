from django.db import models
from django.utils import timezone

from apps.authentication.models import Register


class PerfilPaciente(models.Model):
    NOTIF_CHOICES = [("Activadas", "Activadas"), ("Desactivadas", "Desactivadas")]
    RECORDAT_CHOICES = [("Activados", "Activados"), ("Desactivados", "Desactivados")]
    CONTACTO_CHOICES = [
        ("Correo", "Correo"),
        ("WhatsApp", "WhatsApp"),
        ("Teléfono", "Teléfono"),
    ]

    idPaciente = models.OneToOneField(
        Register,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="idPaciente",
        related_name="perfil_paciente",
    )
    genero = models.CharField(max_length=20, null=True, blank=True)
    edad = models.IntegerField(null=True, blank=True)
    numeroTelefonico = models.CharField(max_length=20, null=True, blank=True)
    consentimientoDatos = models.BooleanField(default=False)
    consentimiento_chatbot = models.BooleanField(default=False)
    prefNotificaciones = models.CharField(
        max_length=15, choices=NOTIF_CHOICES, default="Activadas"
    )
    prefRecordatorios = models.CharField(
        max_length=15, choices=RECORDAT_CHOICES, default="Activados"
    )
    prefContacto = models.CharField(
        max_length=15, choices=CONTACTO_CHOICES, default="Correo"
    )

    class Meta:
        db_table = "PerfilPaciente"

    def __str__(self):
        return f"Paciente {self.idPaciente_id}"

    def to_dict(self):
        return {
            "idPaciente": self.idPaciente_id,
            "genero": self.genero,
            "edad": self.edad,
            "numeroTelefonico": self.numeroTelefonico,
            "consentimientoDatos": self.consentimientoDatos,
            "consentimiento_chatbot": self.consentimiento_chatbot,
            "prefNotificaciones": self.prefNotificaciones,
            "prefRecordatorios": self.prefRecordatorios,
            "prefContacto": self.prefContacto,
        }


class EvolucionPaciente(models.Model):
    idEvolucion = models.AutoField(primary_key=True)
    idPaciente = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
        related_name="evoluciones",
    )
    idConversacion = models.IntegerField(null=True, blank=True)
    estadoEmocional = models.CharField(max_length=100, null=True, blank=True)
    nivelEnergia = models.IntegerField(null=True, blank=True)
    notasPersonales = models.TextField(null=True, blank=True)
    resultadoEmocional = models.CharField(max_length=100, null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "EvolucionPaciente"

    def __str__(self):
        return f"Evolucion {self.idEvolucion} - Paciente {self.idPaciente_id}"

    def to_dict(self):
        return {
            "idEvolucion": self.idEvolucion,
            "idPaciente": self.idPaciente_id,
            "idConversacion": self.idConversacion,
            "estadoEmocional": self.estadoEmocional,
            "nivelEnergia": self.nivelEnergia,
            "notasPersonales": self.notasPersonales,
            "resultadoEmocional": self.resultadoEmocional,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }
