from django.contrib import admin

from apps.documents.models import (
    AutorizacionesDocumento,
    DocumentosClinicos,
    DocumentosPaciente,
)


@admin.register(DocumentosClinicos)
class DocumentosClinicosAdmin(admin.ModelAdmin):
    list_display = ("idDocumento", "idProfesional", "idPaciente", "nombreArchivo", "categoria", "fecha")
    list_filter = ("categoria", "visibilidad", "eliminado")
    search_fields = ("nombreArchivo",)
    readonly_fields = ("fecha",)


@admin.register(DocumentosPaciente)
class DocumentosPacienteAdmin(admin.ModelAdmin):
    list_display = ("idDocumento", "idPaciente", "nombreArchivo", "fecha")
    list_filter = ("eliminado",)
    search_fields = ("nombreArchivo",)
    readonly_fields = ("fecha",)


@admin.register(AutorizacionesDocumento)
class AutorizacionesDocumentoAdmin(admin.ModelAdmin):
    list_display = ("idAutorizacion", "idDocumento", "idProfesional", "revocado", "fechaAutorizacion")
    list_filter = ("revocado",)
    readonly_fields = ("fechaAutorizacion",)
