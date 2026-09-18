from django.db import models

from apps.authentication.models import Register


class DocumentosClinicos(models.Model):
    CATEGORIA_CHOICES = [
        ("Historia Clinica", "Historia Clinica"),
        ("Evolucion", "Evolucion"),
        ("Diagnostico", "Diagnostico"),
        ("Consentimiento", "Consentimiento"),
        ("Otro", "Otro"),
    ]
    VISIBILIDAD_CHOICES = [
        ("privado", "Privado"),
        ("compartido", "Compartido"),
    ]

    idDocumento = models.AutoField(primary_key=True)
    idProfesional = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idProfesional",
        related_name="documentos_clinicos",
    )
    idPaciente = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
        related_name="documentos_paciente_prof",
    )
    nombreArchivo = models.CharField(max_length=255)
    rutaArchivo = models.CharField(max_length=500)
    tipoMime = models.CharField(max_length=100, null=True, blank=True)
    tamanoArchivo = models.IntegerField(null=True, blank=True)
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default="Otro",
    )
    visibilidad = models.CharField(
        max_length=12,
        choices=VISIBILIDAD_CHOICES,
        default="privado",
    )
    notasInternas = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    eliminado = models.BooleanField(default=False)

    class Meta:
        db_table = "DocumentosClinicos"

    def __str__(self):
        return self.nombreArchivo

    def to_dict(self):
        return {
            "idDocumento": self.idDocumento,
            "idProfesional": self.idProfesional_id,
            "idPaciente": self.idPaciente_id,
            "nombreArchivo": self.nombreArchivo,
            "rutaArchivo": self.rutaArchivo,
            "tipoMime": self.tipoMime,
            "tamanoArchivo": self.tamanoArchivo,
            "categoria": self.categoria,
            "visibilidad": self.visibilidad,
            "notasInternas": self.notasInternas,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "eliminado": self.eliminado,
        }


class DocumentosPaciente(models.Model):
    idDocumento = models.AutoField(primary_key=True)
    idPaciente = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
        related_name="documentos_paciente",
    )
    nombreArchivo = models.CharField(max_length=255)
    rutaArchivo = models.CharField(max_length=500)
    tipoMime = models.CharField(max_length=100, null=True, blank=True)
    tamanoArchivo = models.IntegerField(null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    eliminado = models.BooleanField(default=False)

    class Meta:
        db_table = "DocumentosPaciente"

    def __str__(self):
        return self.nombreArchivo

    def to_dict(self):
        return {
            "idDocumento": self.idDocumento,
            "idPaciente": self.idPaciente_id,
            "nombreArchivo": self.nombreArchivo,
            "rutaArchivo": self.rutaArchivo,
            "tipoMime": self.tipoMime,
            "tamanoArchivo": self.tamanoArchivo,
            "descripcion": self.descripcion,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "eliminado": self.eliminado,
        }


class AutorizacionesDocumento(models.Model):
    idAutorizacion = models.AutoField(primary_key=True)
    idDocumento = models.ForeignKey(
        DocumentosClinicos,
        on_delete=models.CASCADE,
        db_column="idDocumento",
    )
    idProfesional = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idProfesional",
    )
    fechaAutorizacion = models.DateTimeField(auto_now_add=True)
    revocado = models.BooleanField(default=False)
    fechaRevocacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "AutorizacionesDocumento"
        unique_together = ("idDocumento", "idProfesional")

    def __str__(self):
        return f"Auth {self.idAutorizacion} - Doc {self.idDocumento_id}"

    def to_dict(self):
        return {
            "idAutorizacion": self.idAutorizacion,
            "idDocumento": self.idDocumento_id,
            "idProfesional": self.idProfesional_id,
            "fechaAutorizacion": self.fechaAutorizacion.isoformat() if self.fechaAutorizacion else None,
            "revocado": self.revocado,
            "fechaRevocacion": self.fechaRevocacion.isoformat() if self.fechaRevocacion else None,
        }
