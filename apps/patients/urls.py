from django.urls import path

from apps.patients.views import (
    PerfilPacienteResource,
    PerfilFotoResource,
    EvolucionResource,
    PacienteResource,
    ProfesionalResource,
    ChatbotResource,
    ChatbotEncuestaResource,
    ChatbotConfigResource,
    ChatbotConfigEventsResource,
    ConsentimientoChatbotResource,
    DocumentoPacienteResource,
    ChatContactoResource,
    ChatMensajeResource,
)

app_name = "patients"

urlpatterns = [
    path("perfil/paciente/<int:id_usuario>", PerfilPacienteResource.as_view(), name="perfil_paciente"),
    path("perfil/paciente", PerfilPacienteResource.as_view(), name="perfil_paciente_update"),
    path("perfil/paciente/foto", PerfilFotoResource.as_view(), name="perfil_foto"),
    path("evolucion", EvolucionResource.as_view(), name="evolucion"),
    path("pacientes", PacienteResource.as_view(), name="pacientes"),
    path("profesionales", ProfesionalResource.as_view(), name="profesionales"),
    path("chatbot", ChatbotResource.as_view(), name="chatbot"),
    path("chatbot/historial", ChatbotResource.as_view(), name="chatbot_historial"),
    path("chatbot/encuesta", ChatbotEncuestaResource.as_view(), name="chatbot_encuesta"),
    path("chatbot/config", ChatbotConfigResource.as_view(), name="chatbot_config"),
    path("chatbot/config/events", ChatbotConfigEventsResource.as_view(), name="chatbot_config_events"),
    path("paciente/consentimiento-chatbot", ConsentimientoChatbotResource.as_view(), name="consentimiento_chatbot"),
    path("paciente/documentos/subir", DocumentoPacienteResource.as_view(), name="documento_subir"),
    path("paciente/documentos/<int:id_documento>", DocumentoPacienteResource.as_view(), name="documento_paciente"),
    path("paciente/documentos", DocumentoPacienteResource.as_view(), name="documentos_paciente"),
    path("chat/contactos", ChatContactoResource.as_view(), name="chat_contactos"),
    path("chat/mensajes", ChatMensajeResource.as_view(), name="chat_mensajes"),
    # Legacy aliases
    path("chatbot/enviar", ChatbotResource.as_view(), name="chatbot_enviar_legacy"),
    path("perfil/foto", PerfilFotoResource.as_view(), name="perfil_foto_legacy"),
    path("chat/profesionales", ChatContactoResource.as_view(), name="chat_profesionales_legacy"),
    path("paciente/chat/mensajes", ChatMensajeResource.as_view(), name="chat_mensajes_paciente_legacy"),
    path("chat/enviar", ChatMensajeResource.as_view(), name="chat_enviar_legacy"),
    path("paciente/chat/enviar", ChatMensajeResource.as_view(), name="chat_paciente_enviar_legacy"),
]
