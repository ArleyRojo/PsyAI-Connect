from django.urls import path

from apps.professionals.views import (
    PerfilProfesionalViewSet,
    DisponibilidadViewSet,
    DashboardResource,
    ProfesionalPacienteResource,
    DiagnosticoViewSet,
    ReporteViewSet,
    EvolucionProfesionalResource,
    PacienteChatbotHistorialResource,
    DocumentoProfesionalPacienteViewSet,
    DownloadResource,
    ChatContactoProfesionalResource,
    ChatMensajeProfesionalResource,
    AllPacientesProfesionalResource,
)

app_name = "professionals"

urlpatterns = [
    path("perfil/profesional/<int:pk>", PerfilProfesionalViewSet.as_view({"get": "retrieve"}), name="perfil_profesional"),
    path("perfil/profesional", PerfilProfesionalViewSet.as_view({"put": "update"}), name="perfil_profesional_update"),
    path("disponibilidad", DisponibilidadViewSet.as_view({"post": "create", "get": "list"}), name="disponibilidad_crear"),
    path("disponibilidad/<int:pk>", DisponibilidadViewSet.as_view({"get": "retrieve"}), name="disponibilidad_ver"),
    path("profesional/dashboard", DashboardResource.as_view(), name="dashboard"),
    path("profesional/pacientes", ProfesionalPacienteResource.as_view(), name="profesional_pacientes"),
    path("profesional/pacientes/todos", AllPacientesProfesionalResource.as_view(), name="profesional_pacientes_todos"),
    path("diagnosticos", DiagnosticoViewSet.as_view({"get": "list", "post": "create"}), name="diagnosticos"),
    path("reportes", ReporteViewSet.as_view({"get": "list", "post": "create"}), name="reportes"),
    path("reportes/<int:pk>", ReporteViewSet.as_view({"put": "update", "delete": "destroy"}), name="reporte"),
    path("evolucion/profesional", EvolucionProfesionalResource.as_view(), name="evolucion_profesional"),
    path("profesional/pacientes/<int:id_paciente>/chatbot/historial", PacienteChatbotHistorialResource.as_view(), name="paciente_chatbot_historial"),
    path("profesional/pacientes/<int:id_paciente>/documentos", DocumentoProfesionalPacienteViewSet.as_view({"get": "list", "post": "create"}), name="documentos_profesional_paciente"),
    path("profesional/documentos/<int:pk>", DocumentoProfesionalPacienteViewSet.as_view({"patch": "partial_update", "put": "update", "delete": "destroy"}), name="documento_profesional"),
    path("descargar/<str:tipo>/<int:id_documento>", DownloadResource.as_view(), name="descargar"),
    path("chat/pacientes", ChatContactoProfesionalResource.as_view(), name="chat_contactos_profesional"),
    path("profesional/chat/mensajes", ChatMensajeProfesionalResource.as_view(), name="chat_mensajes_profesional"),
    path("profesional/chat/enviar", ChatMensajeProfesionalResource.as_view(), name="chat_enviar_profesional"),
    # Legacy aliases
    path("reportes/profesional", ReporteViewSet.as_view({"get": "list"}), name="reportes_profesional_legacy"),
    path("reportes/eliminados", ReporteViewSet.as_view({"get": "list"}), name="reportes_eliminados_legacy"),
    path("profesional/paciente/<int:id_paciente>/chatbot-historial", PacienteChatbotHistorialResource.as_view(), name="paciente_chatbot_historial_legacy"),
    path("profesional/paciente/<int:id_paciente>/documentos", DocumentoProfesionalPacienteViewSet.as_view({"get": "list", "post": "create"}), name="documentos_profesional_paciente_legacy"),
    path("profesional/documentos/<int:pk>/visibilidad", DocumentoProfesionalPacienteViewSet.as_view({"patch": "partial_update", "put": "update"}), name="documento_visibilidad_legacy"),
    path("descargar/documento-profesional/<int:id_documento>", DownloadResource.as_view(), name="descargar_profesional_legacy"),
    path("descargar/documento-paciente/<int:id_documento>", DownloadResource.as_view(), name="descargar_paciente_legacy"),
]
