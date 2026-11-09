from datetime import date as date_cls
from django.db import models
from django.utils import timezone

from apps.authentication.models import Register


class AuditoriaAccesos(models.Model):
    idAuditoria = models.AutoField(primary_key=True)
    idUsuario = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idUsuario",
        related_name="accesos",
    )
    accion = models.CharField(max_length=100, null=True, blank=True)
    ip = models.CharField(max_length=50, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "AuditoriaAccesos"

    def __str__(self):
        return f"Auditoría {self.idAuditoria} - Usuario {self.idUsuario_id}"

    def clean(self):
        # Handle naive date objects passed to DateTimeField
        if isinstance(self.fecha, date_cls) and not isinstance(self.fecha, timezone.datetime):
            self.fecha = timezone.make_aware(
                timezone.datetime(self.fecha.year, self.fecha.month, self.fecha.day),
                timezone.get_default_timezone()
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "idAuditoria": self.idAuditoria,
            "idUsuario": self.idUsuario_id,
            "accion": self.accion,
            "ip": self.ip,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }


class Logs(models.Model):
    idLog = models.AutoField(primary_key=True)
    administrador = models.CharField(max_length=120, null=True, blank=True)
    modulo = models.CharField(max_length=80, null=True, blank=True)
    accion = models.CharField(max_length=120, null=True, blank=True)
    detalle = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    rol_anterior = models.CharField(max_length=20, null=True, blank=True)
    rol_nuevo = models.CharField(max_length=20, null=True, blank=True)
    usuario_afectado = models.CharField(max_length=100, null=True, blank=True)
    origen = models.CharField(max_length=20, default="admin", null=True, blank=True)

    class Meta:
        db_table = "Logs"

    def __str__(self):
        return f"Log {self.idLog} - {self.accion}"

    def clean(self):
        # Handle naive date objects passed to DateTimeField
        # This prevents: "DateTimeField Logs.fecha received a naive datetime while time zone support is active"
        if isinstance(self.fecha, date_cls) and not isinstance(self.fecha, timezone.datetime):
            self.fecha = timezone.make_aware(
                timezone.datetime(self.fecha.year, self.fecha.month, self.fecha.day),
                timezone.get_default_timezone()
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "idLog": self.idLog,
            "administrador": self.administrador,
            "modulo": self.modulo,
            "accion": self.accion,
            "detalle": self.detalle,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "rol_anterior": self.rol_anterior,
            "rol_nuevo": self.rol_nuevo,
            "usuario_afectado": self.usuario_afectado,
            "origen": self.origen or "admin",
        }


class ConfiguracionSeguridad(models.Model):
    """Ajustes de seguridad del sistema (una sola fila). HU-13: cierre por inactividad."""

    MINUTOS_MIN = 5
    MINUTOS_MAX = 120
    MINUTOS_DEFECTO = 15

    minutosInactividad = models.PositiveSmallIntegerField(default=MINUTOS_DEFECTO)
    actualizadoPor = models.CharField(max_length=120, null=True, blank=True)
    fechaActualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ConfiguracionSeguridad"

    @classmethod
    def obtener(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def to_dict(self):
        return {
            "minutosInactividad": self.minutosInactividad,
            "minutosMin": self.MINUTOS_MIN,
            "minutosMax": self.MINUTOS_MAX,
            "actualizadoPor": self.actualizadoPor,
            "fechaActualizacion": self.fechaActualizacion.isoformat() if self.fechaActualizacion else None,
        }
