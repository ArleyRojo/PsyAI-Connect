from django.contrib import admin

from apps.professionals.models import PacientesProfesional, PerfilProfesional, Reportes, Diagnostico


@admin.register(PerfilProfesional)
class PerfilProfesionalAdmin(admin.ModelAdmin):
    list_display = ("idProfesional", "especialidad", "licencia", "estado")
    search_fields = ("idProfesional__email", "especialidad", "licencia")
    list_filter = ("estado",)


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
