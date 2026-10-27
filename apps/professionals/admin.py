from django.contrib import admin

from apps.professionals.models import PacientesProfesional, PerfilProfesional, Reportes, Diagnostico


@admin.register(PerfilProfesional)
class PerfilProfesionalAdmin(admin.ModelAdmin):
    list_display = ("idProfesional", "especialidad", "tarjetaProfesional", "numeroRethus", "verificado", "estado")
    search_fields = ("idProfesional__email", "especialidad", "tarjetaProfesional", "numeroRethus")
    list_filter = ("estado", "verificado")

    actions = ["verificar_profesionales", "desverificar_profesionales"]

    @admin.action(description="Verificar profesionales seleccionados")
    def verificar_profesionales(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(verificado=True, fechaVerificacion=timezone.now(), verificadoPor=request.user)
        self.message_user(request, f"{updated} profesionales verificados.")

    @admin.action(description="Desverificar profesionales seleccionados")
    def desverificar_profesionales(self, request, queryset):
        updated = queryset.update(verificado=False, fechaVerificacion=None, verificadoPor=None)
        self.message_user(request, f"{updated} profesionales desverificados.")


@admin.register(PacientesProfesional)
class PacientesProfesionalAdmin(admin.ModelAdmin):
    list_display = ("idRegistro", "idProfesional", "idPaciente", "fecha")
    readonly_fields = ("fecha",)


@admin.register(Diagnostico)
class DiagnosticoAdmin(admin.ModelAdmin):
    list_display = ("idDiagnostico", "idAsignacion", "fechaDiagnostico", "fecha")
    search_fields = ("diagnostico", "sintomas")
    readonly_fields = ("fecha",)


@admin.register(Reportes)
class ReportesAdmin(admin.ModelAdmin):
    list_display = ("idReporte", "idProfesional", "tipoReporte", "estado", "fecha")
    list_filter = ("estado", "eliminado")
    readonly_fields = ("fecha",)
