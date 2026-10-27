from django.db import models

from apps.authentication.models import Register


class ProfessionalPaymentInfo(models.Model):
    idProfesional = models.OneToOneField(
        Register,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="idProfesional",
        related_name="payment_info",
    )
    qr_image = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    mensaje_texto = models.TextField(null=True, blank=True, help_text="Número de cuenta, Nequi, llaves Bre-B, etc.")

    class Meta:
        db_table = "ProfessionalPaymentInfo"

    def __str__(self):
        return f"PaymentInfo Prof {self.idProfesional_id}"


class PerfilProfesional(models.Model):
    ESTADO_CHOICES = [
        ("Activo", "Activo"),
        ("Inactivo", "Inactivo"),
    ]

    idProfesional = models.OneToOneField(
        Register,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="idProfesional",
        related_name="perfil_profesional",
    )
    genero = models.CharField(max_length=20, null=True, blank=True)
    edad = models.IntegerField(null=True, blank=True)
    especialidad = models.CharField(max_length=120, null=True, blank=True)
    tarjetaProfesional = models.CharField(max_length=50, null=True, blank=True, help_text="Número de tarjeta profesional")
    numeroRethus = models.CharField(max_length=50, null=True, blank=True, help_text="Número de registro ReTHUS")
    experiencia = models.TextField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="Activo"
    )
    verificado = models.BooleanField(default=False, help_text="Profesional verificado por administrador")
    fechaVerificacion = models.DateTimeField(null=True, blank=True, help_text="Fecha de verificación")
    verificadoPor = models.ForeignKey(
        Register,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="verificadoPor",
        related_name="profesionales_verificados",
        help_text="Administrador que verificó al profesional"
    )

    class Meta:
        db_table = "PerfilProfesional"

    def __str__(self):
        return f"Profesional {self.idProfesional_id}"

    def to_dict(self):
        return {
            "idProfesional": self.idProfesional_id,
            "genero": self.genero,
            "edad": self.edad,
            "especialidad": self.especialidad,
            "tarjetaProfesional": self.tarjetaProfesional,
            "numeroRethus": self.numeroRethus,
            "experiencia": self.experiencia,
            "estado": self.estado,
            "verificado": self.verificado,
            "fechaVerificacion": self.fechaVerificacion.isoformat() if self.fechaVerificacion else None,
            "verificadoPor": self.verificadoPor_id,
        }


class PacientesProfesional(models.Model):
    idRegistro = models.AutoField(primary_key=True)
    idProfesional = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idProfesional",
        related_name="pacientes_profesional",
    )
    idPaciente = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
        related_name="pacientes_asignados",
        null=True,
        blank=True,
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "PacientesProfesional"
        constraints = [
            models.UniqueConstraint(
                fields=["idProfesional", "idPaciente"],
                name="uq_profesional_paciente",
            )
        ]

    def __str__(self):
        return f"Registro {self.idRegistro} - Prof {self.idProfesional_id}"

    def to_dict(self):
        return {
            "idRegistro": self.idRegistro,
            "idProfesional": self.idProfesional_id,
            "idPaciente": self.idPaciente_id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }


class Diagnostico(models.Model):
    idDiagnostico = models.AutoField(primary_key=True)
    idAsignacion = models.ForeignKey(
        PacientesProfesional,
        on_delete=models.CASCADE,
        db_column="idAsignacion",
        related_name="diagnosticos",
    )
    sintomas = models.TextField(null=True, blank=True)
    diagnostico = models.TextField(null=True, blank=True)
    tratamiento = models.TextField(null=True, blank=True)
    fechaDiagnostico = models.DateField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Diagnostico"
        ordering = ["-fechaDiagnostico", "-fecha"]

    def __str__(self):
        return f"Diagnostico {self.idDiagnostico} - Asignacion {self.idAsignacion_id}"

    def to_dict(self):
        return {
            "idDiagnostico": self.idDiagnostico,
            "idAsignacion": self.idAsignacion_id,
            "sintomas": self.sintomas,
            "diagnostico": self.diagnostico,
            "tratamiento": self.tratamiento,
            "fechaDiagnostico": (
                self.fechaDiagnostico.isoformat()
                if hasattr(self.fechaDiagnostico, "isoformat")
                else (str(self.fechaDiagnostico) if self.fechaDiagnostico else None)
            ),
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }


class Reportes(models.Model):
    idReporte = models.AutoField(primary_key=True)
    idProfesional = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idProfesional",
        related_name="reportes_profesional",
    )
    idPaciente = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
        related_name="reportes_paciente",
        null=True,
        blank=True,
    )
    tipoReporte = models.CharField(max_length=80, null=True, blank=True)
    fechaInicio = models.DateField(null=True, blank=True)
    fechaFin = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, default="Pendiente")
    fecha = models.DateTimeField(auto_now_add=True)
    eliminado = models.BooleanField(default=False)
    sintomas = models.TextField(null=True, blank=True)
    diagnostico = models.TextField(null=True, blank=True)
    tratamiento = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "Reportes"

    def __str__(self):
        return f"Reporte {self.idReporte} - Prof {self.idProfesional_id}"

    def to_dict(self):
        return {
            "idReporte": self.idReporte,
            "idProfesional": self.idProfesional_id,
            "idPaciente": self.idPaciente_id,
            "tipoReporte": self.tipoReporte,
            "fechaInicio": self.fechaInicio.isoformat() if self.fechaInicio else None,
            "fechaFin": self.fechaFin.isoformat() if self.fechaFin else None,
            "estado": self.estado,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "eliminado": self.eliminado,
            "sintomas": self.sintomas,
            "diagnostico": self.diagnostico,
            "tratamiento": self.tratamiento,
        }
