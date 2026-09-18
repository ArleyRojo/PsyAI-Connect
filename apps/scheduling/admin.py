from django.contrib import admin

from apps.scheduling.models import Citas, Disponibilidad, Notificaciones


@admin.register(Disponibilidad)
class DisponibilidadAdmin(admin.ModelAdmin):
    list_display = ("idDisponibilidad", "idProfesional", "fecha", "hora_inicio", "hora_fin", "estado")
    list_filter = ("estado", "fecha")
    search_fields = ("idProfesional__email",)


@admin.register(Citas)
class CitasAdmin(admin.ModelAdmin):
    list_display = ("idCita", "idPaciente", "idProfesional", "fecha", "hora", "estado")
    list_filter = ("estado", "fecha")
    search_fields = ("idPaciente__email", "idProfesional__email")


@admin.register(Notificaciones)
class NotificacionesAdmin(admin.ModelAdmin):
    list_display = ("idNotificacion", "titulo", "rol", "estado", "leido", "fecha")
    list_filter = ("estado", "leido", "rol")
    readonly_fields = ("fecha",)
