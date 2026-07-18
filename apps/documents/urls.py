from django.urls import path

from apps.documents import views

app_name = "documents"

urlpatterns = [
    path(
        "documentos/profesional/<int:id_paciente>",
        views.DocumentoProfesionalListView.as_view(),
        name="documento_profesional_list",
    ),
    path(
        "documentos/profesional/doc/<int:id_documento>",
        views.DocumentoProfesionalDetailView.as_view(),
        name="documento_profesional_detail",
    ),
    path(
        "documentos/profesional/doc/<int:id_documento>/descargar",
        views.DocumentoProfesionalDownloadView.as_view(),
        name="documento_profesional_download",
    ),
    path(
        "documentos/paciente/dashboard",
        views.DocumentoPacienteDashboardView.as_view(),
        name="documento_paciente_dashboard",
    ),
    path(
        "documentos/paciente",
        views.DocumentoPacienteOwnListView.as_view(),
        name="documento_paciente_list",
    ),
    path(
        "documentos/paciente/doc/<int:id_documento>",
        views.DocumentoPacienteOwnDetailView.as_view(),
        name="documento_paciente_detail",
    ),
    path(
        "documentos/paciente/doc/<int:id_documento>/descargar",
        views.DocumentoPacienteDownloadView.as_view(),
        name="documento_paciente_download",
    ),
    path(
        "documentos/autorizacion/<int:id_documento>",
        views.AutorizacionToggleView.as_view(),
        name="autorizacion_toggle",
    ),
]
