from django.contrib import admin

from apps.patients.models import EvolucionPaciente, PerfilPaciente


@admin.register(PerfilPaciente)
class PerfilPacienteAdmin(admin.ModelAdmin):
    list_display = ("idPaciente", "genero", "edad", "numeroTelefonico", "consentimientoDatos")
    search_fields = ("idPaciente__email", "idPaciente__nombre")
    list_filter = ("consentimientoDatos", "consentimiento_chatbot")


@admin.register(EvolucionPaciente)
class EvolucionPacienteAdmin(admin.ModelAdmin):
    list_display = ("idEvolucion", "idPaciente", "estadoEmocional", "nivelEnergia", "fecha")
    list_filter = ("estadoEmocional",)
    readonly_fields = ("fecha",)
