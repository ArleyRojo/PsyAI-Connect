from django.contrib import admin

from apps.admin_panel.models import AuditoriaAccesos, Logs


@admin.register(AuditoriaAccesos)
class AuditoriaAccesosAdmin(admin.ModelAdmin):
    list_display = ("idAuditoria", "idUsuario", "accion", "ip", "fecha")
    list_filter = ("accion",)
    search_fields = ("idUsuario__email", "ip")
    readonly_fields = ("fecha",)


@admin.register(Logs)
class LogsAdmin(admin.ModelAdmin):
    list_display = ("idLog", "administrador", "modulo", "accion", "fecha")
    list_filter = ("modulo", "accion")
    search_fields = ("administrador", "usuario_afectado")
    readonly_fields = ("fecha",)
