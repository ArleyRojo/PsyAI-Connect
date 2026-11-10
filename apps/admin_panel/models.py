from datetime import date as date_cls
from datetime import time as dt_time
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
    """Políticas de seguridad del sistema (una sola fila).
    HU-13: cierre por inactividad. HU-23: contraseñas, bloqueo por intentos y revisión periódica."""

    MINUTOS_MIN = 5
    MINUTOS_MAX = 120
    MINUTOS_DEFECTO = 15

    # Rangos permitidos para cada política: campo -> (mínimo, máximo)
    RANGOS = {
        "minutosInactividad": (MINUTOS_MIN, MINUTOS_MAX),
        "passMinimo": (6, 32),
        "intentosMaximos": (3, 10),
        "minutosBloqueo": (5, 120),
        "revisionMeses": (1, 24),
    }

    minutosInactividad = models.PositiveSmallIntegerField(default=MINUTOS_DEFECTO)
    # Contraseñas (los valores por defecto son las reglas que ya tenía el registro)
    passMinimo = models.PositiveSmallIntegerField(default=6)
    passMayuscula = models.BooleanField(default=True)
    passNumero = models.BooleanField(default=True)
    passSimbolo = models.BooleanField(default=False)
    # Bloqueo por intentos fallidos de inicio de sesión
    intentosMaximos = models.PositiveSmallIntegerField(default=5)
    minutosBloqueo = models.PositiveSmallIntegerField(default=15)
    # Revisión periódica de las políticas (RN-14)
    revisionMeses = models.PositiveSmallIntegerField(default=6)
    fechaUltimaRevision = models.DateTimeField(null=True, blank=True)
    revisadoPor = models.CharField(max_length=120, null=True, blank=True)

    actualizadoPor = models.CharField(max_length=120, null=True, blank=True)
    fechaActualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ConfiguracionSeguridad"

    @classmethod
    def obtener(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def proxima_revision(self):
        if not self.fechaUltimaRevision:
            return None
        import calendar
        fecha = self.fechaUltimaRevision
        meses = fecha.month - 1 + self.revisionMeses
        anio, mes = fecha.year + meses // 12, meses % 12 + 1
        dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
        return fecha.replace(year=anio, month=mes, day=dia)

    def revision_vencida(self):
        from django.utils import timezone
        proxima = self.proxima_revision()
        return proxima is None or proxima <= timezone.now()

    def to_dict(self):
        proxima = self.proxima_revision()
        return {
            "minutosInactividad": self.minutosInactividad,
            "minutosMin": self.MINUTOS_MIN,
            "minutosMax": self.MINUTOS_MAX,
            "passMinimo": self.passMinimo,
            "passMayuscula": self.passMayuscula,
            "passNumero": self.passNumero,
            "passSimbolo": self.passSimbolo,
            "intentosMaximos": self.intentosMaximos,
            "minutosBloqueo": self.minutosBloqueo,
            "revisionMeses": self.revisionMeses,
            "fechaUltimaRevision": self.fechaUltimaRevision.isoformat() if self.fechaUltimaRevision else None,
            "revisadoPor": self.revisadoPor,
            "proximaRevision": proxima.isoformat() if proxima else None,
            "revisionVencida": self.revision_vencida(),
            "rangos": {k: list(v) for k, v in self.RANGOS.items()},
            "actualizadoPor": self.actualizadoPor,
            "fechaActualizacion": self.fechaActualizacion.isoformat() if self.fechaActualizacion else None,
        }


class ConfiguracionSistema(models.Model):
    """Ajustes de mantenimiento del sistema (una sola fila). HU-24 y HU-30."""

    modoMantenimiento = models.BooleanField(default=False)
    mensajeMantenimiento = models.CharField(
        max_length=300, blank=True,
        default="Estamos haciendo mejoras en la plataforma. Vuelve a intentarlo en unos minutos.",
    )
    horaCopia = models.TimeField(default=dt_time(2, 0))
    programadorLatido = models.DateTimeField(null=True, blank=True)
    actualizadoPor = models.CharField(max_length=120, null=True, blank=True)
    fechaActualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ConfiguracionSistema"

    @classmethod
    def obtener(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def to_dict(self):
        return {
            "modoMantenimiento": self.modoMantenimiento,
            "mensajeMantenimiento": self.mensajeMantenimiento,
            "horaCopia": self.horaCopia.strftime("%H:%M") if self.horaCopia else "02:00",
            "programadorLatido": self.programadorLatido.isoformat() if self.programadorLatido else None,
            "actualizadoPor": self.actualizadoPor,
            "fechaActualizacion": self.fechaActualizacion.isoformat() if self.fechaActualizacion else None,
        }
