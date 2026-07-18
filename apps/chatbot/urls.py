from django.urls import path

from apps.chatbot.views import (
    ChatbotResource,
    ChatbotEncuestaResource,
    ChatbotConfigResource,
    ChatbotConfigEventsResource,
    ConsentimientoChatbotResource,
    ChatContactoResource,
    ChatMensajeResource,
    ChatHistorialDeleteResource,
)

app_name = "chatbot"

urlpatterns = [
    path("chatbot", ChatbotResource.as_view(), name="chatbot"),
    path("chatbot/historial", ChatbotResource.as_view(), name="chatbot_historial"),
    path("chatbot/encuesta", ChatbotEncuestaResource.as_view(), name="chatbot_encuesta"),
    path("chatbot/config", ChatbotConfigResource.as_view(), name="chatbot_config"),
    path("chatbot/config/events", ChatbotConfigEventsResource.as_view(), name="chatbot_config_events"),
    path("paciente/consentimiento-chatbot", ConsentimientoChatbotResource.as_view(), name="consentimiento_chatbot"),
    path("chat/contactos", ChatContactoResource.as_view(), name="chat_contactos"),
    path("chat/mensajes", ChatMensajeResource.as_view(), name="chat_mensajes"),
    path("chat/historial", ChatHistorialDeleteResource.as_view(), name="chat_historial_delete"),
    path("chatbot/enviar", ChatbotResource.as_view(), name="chatbot_enviar_legacy"),
    path("chat/profesionales", ChatContactoResource.as_view(), name="chat_profesionales_legacy"),
    path("paciente/chat/mensajes", ChatMensajeResource.as_view(), name="chat_mensajes_paciente_legacy"),
    path("chat/enviar", ChatMensajeResource.as_view(), name="chat_enviar_legacy"),
    path("paciente/chat/enviar", ChatMensajeResource.as_view(), name="chat_paciente_enviar_legacy"),
]
