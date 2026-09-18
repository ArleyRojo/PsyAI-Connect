from django.db import models

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

    class Meta:
        db_table = "Logs"

    def __str__(self):
        return f"Log {self.idLog} - {self.accion}"

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
        }
