from django.urls import path

from apps.professionals.views import (
    PerfilProfesionalResource,
    DisponibilidadResource,
    DashboardResource,
    ProfesionalPacienteResource,
    DiagnosticoResource,
    ReporteResource,
    EvolucionProfesionalResource,
    PacienteChatbotHistorialResource,
    DocumentoProfesionalPacienteResource,
    DownloadResource,
    ChatContactoProfesionalResource,
    ChatMensajeProfesionalResource,
)

app_name = "professionals"

urlpatterns = [
    path("perfil/profesional/<int:id_usuario>", PerfilProfesionalResource.as_view(), name="perfil_profesional"),
    path("perfil/profesional", PerfilProfesionalResource.as_view(), name="perfil_profesional_update"),
    path("disponibilidad", DisponibilidadResource.as_view(), name="disponibilidad_crear"),
    path("disponibilidad/<int:id_profesional>", DisponibilidadResource.as_view(), name="disponibilidad_ver"),
    path("profesional/dashboard", DashboardResource.as_view(), name="dashboard"),
    path("profesional/pacientes", ProfesionalPacienteResource.as_view(), name="profesional_pacientes"),
    path("diagnosticos", DiagnosticoResource.as_view(), name="diagnosticos"),
    path("reportes", ReporteResource.as_view(), name="reportes"),
    path("reportes/<int:id_reporte>", ReporteResource.as_view(), name="reporte"),
    path("evolucion/profesional", EvolucionProfesionalResource.as_view(), name="evolucion_profesional"),
    path("profesional/pacientes/<int:id_paciente>/chatbot/historial", PacienteChatbotHistorialResource.as_view(), name="paciente_chatbot_historial"),
    path("profesional/pacientes/<int:id_paciente>/documentos", DocumentoProfesionalPacienteResource.as_view(), name="documentos_profesional_paciente"),
    path("profesional/documentos/<int:id_documento>", DocumentoProfesionalPacienteResource.as_view(), name="documento_profesional"),
    path("descargar/<str:tipo>/<int:id_documento>", DownloadResource.as_view(), name="descargar"),
    path("chat/pacientes", ChatContactoProfesionalResource.as_view(), name="chat_contactos_profesional"),
    path("profesional/chat/mensajes", ChatMensajeProfesionalResource.as_view(), name="chat_mensajes_profesional"),
    path("profesional/chat/enviar", ChatMensajeProfesionalResource.as_view(), name="chat_enviar_profesional"),
    # Legacy aliases
    path("reportes/profesional", ReporteResource.as_view(), name="reportes_profesional_legacy"),
    path("reportes/eliminados", ReporteResource.as_view(), name="reportes_eliminados_legacy"),
    path("profesional/paciente/<int:id_paciente>/chatbot-historial", PacienteChatbotHistorialResource.as_view(), name="paciente_chatbot_historial_legacy"),
    path("profesional/paciente/<int:id_paciente>/documentos", DocumentoProfesionalPacienteResource.as_view(), name="documentos_profesional_paciente_legacy"),
    path("profesional/documentos/<int:id_documento>/visibilidad", DocumentoProfesionalPacienteResource.as_view(), name="documento_visibilidad_legacy"),
    path("descargar/documento-profesional/<int:id_documento>", DownloadResource.as_view(), name="descargar_profesional_legacy"),
    path("descargar/documento-paciente/<int:id_documento>", DownloadResource.as_view(), name="descargar_paciente_legacy"),
]
