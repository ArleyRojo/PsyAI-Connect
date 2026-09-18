from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.documents import views

app_name = "documents"

router = DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path(
        "documentos/profesional/<int:id_paciente>",
        views.DocumentoProfesionalViewSet.as_view(
            {"get": "list", "post": "create"}
        ),
        name="documento_profesional_list",
    ),
    path(
        "documentos/profesional/doc/<int:id_documento>",
        views.DocumentoProfesionalViewSet.as_view(
            {"patch": "partial_update", "delete": "destroy"}
        ),
        name="documento_profesional_detail",
    ),
    path(
        "documentos/profesional/doc/<int:id_documento>/descargar",
        views.DocumentoProfesionalDownloadView.as_view(),
        name="documento_profesional_download",
    ),
    path(
        "documentos/paciente/dashboard",
        views.DocumentoPacienteDashboardViewSet.as_view({"get": "list"}),
        name="documento_paciente_dashboard",
    ),
    path(
        "documentos/paciente",
        views.DocumentoPacienteOwnViewSet.as_view(
            {"get": "list", "post": "create"}
        ),
        name="documento_paciente_list",
    ),
    path(
        "documentos/paciente/doc/<int:id_documento>",
        views.DocumentoPacienteOwnViewSet.as_view({"delete": "destroy"}),
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
