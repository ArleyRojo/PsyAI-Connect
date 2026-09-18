from django.db import models
from django.db.models import Q

from apps.authentication.models import Register


class Disponibilidad(models.Model):
    ESTADO_CHOICES = [
        ("Disponible", "Disponible"),
        ("Bloqueado", "Bloqueado"),
        ("Ocupado", "Ocupado"),
    ]

    idDisponibilidad = models.AutoField(primary_key=True)
    idProfesional = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idProfesional",
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="Disponible", null=True, blank=True
    )

    class Meta:
        db_table = "Disponibilidad"

    def to_dict(self):
        return {
            "idDisponibilidad": self.idDisponibilidad,
            "idProfesional": self.idProfesional_id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "hora_inicio": self.hora_inicio.strftime("%H:%M") if self.hora_inicio else None,
            "hora_fin": self.hora_fin.strftime("%H:%M") if self.hora_fin else None,
            "estado": self.estado,
        }


class Citas(models.Model):
    ESTADO_CHOICES = [
        ("Pendiente", "Pendiente"),
        ("Confirmada", "Confirmada"),
        ("Completada", "Completada"),
        ("Cancelada", "Cancelada"),
    ]

    idCita = models.AutoField(primary_key=True)
    idPaciente = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
        related_name="citas_paciente",
    )
    idProfesional = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idProfesional",
        related_name="citas_profesional",
    )
    fecha = models.DateField()
    hora = models.TimeField()
    tipoCita = models.CharField(max_length=80, null=True, blank=True)
    tipoSesion = models.CharField(max_length=80, null=True, blank=True)
    motivo = models.TextField(null=True, blank=True)
    notas = models.TextField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="Pendiente", null=True, blank=True
    )
    creado_por_profesional = models.BooleanField(default=False, null=True, blank=True)
    motivoCancelacion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "Citas"
        constraints = [
            models.UniqueConstraint(
                fields=["idProfesional", "fecha", "hora"],
                condition=Q(estado__in=["Pendiente", "Confirmada"]),
                name="uniq_cita_prof_fecha_hora_active",
            ),
        ]

    def to_dict(self):
        return {
            "idCita": self.idCita,
            "idPaciente": self.idPaciente_id,
            "idProfesional": self.idProfesional_id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "hora": self.hora.strftime("%H:%M") if self.hora else None,
            "tipoCita": self.tipoCita,
            "tipoSesion": self.tipoSesion,
            "motivo": self.motivo,
            "notas": self.notas,
            "estado": self.estado,
            "creado_por_profesional": self.creado_por_profesional,
            "motivoCancelacion": self.motivoCancelacion,
        }


class Notificaciones(models.Model):
    ROL_CHOICES = [
        ("admin", "admin"),
        ("profesional", "profesional"),
        ("paciente", "paciente"),
    ]
    ESTADO_CHOICES = [
        ("enviado", "enviado"),
        ("pendiente", "pendiente"),
    ]

    idNotificacion = models.AutoField(primary_key=True)
    idUsuario = models.ForeignKey(
        Register,
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
    )
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, null=True, blank=True)
    titulo = models.CharField(max_length=200, null=True, blank=True)
    mensaje = models.TextField(null=True, blank=True)
    tipo = models.CharField(max_length=50, null=True, blank=True)
    destinatario = models.CharField(max_length=80, null=True, blank=True)
    email_individual = models.CharField(max_length=120, null=True, blank=True)
    enviado_por = models.CharField(max_length=120, null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="enviado", null=True, blank=True
    )
    leido = models.BooleanField(default=False, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    fecha_programada = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "Notificaciones"

    def to_dict(self):
        return {
            "idNotificacion": self.idNotificacion,
            "idUsuario": self.idUsuario_id,
            "rol": self.rol,
            "titulo": self.titulo,
            "mensaje": self.mensaje,
            "tipo": self.tipo,
            "destinatario": self.destinatario,
            "email_individual": self.email_individual,
            "enviado_por": self.enviado_por,
            "estado": self.estado,
            "leido": self.leido,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "fecha_programada": self.fecha_programada.isoformat() if self.fecha_programada else None,
        }
