from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.chatbot.views import (
    ChatbotViewSet,
    ChatbotEncuestaViewSet,
    ChatbotConfigViewSet,
    ChatbotConfigEventsResource,
    ConsentimientoChatbotViewSet,
    ChatContactoViewSet,
    ChatMensajeViewSet,
    ChatHistorialDeleteViewSet,
)

app_name = "chatbot"

router = DefaultRouter()
router.register(r"chatbot", ChatbotViewSet, basename="chatbot")
router.register(r"chatbot/encuesta", ChatbotEncuestaViewSet, basename="chatbot-encuesta")
router.register(r"chatbot/config", ChatbotConfigViewSet, basename="chatbot-config")
router.register(r"paciente/consentimiento-chatbot", ConsentimientoChatbotViewSet, basename="consentimiento-chatbot")
router.register(r"chat/contactos", ChatContactoViewSet, basename="chat-contactos")
router.register(r"chat/mensajes", ChatMensajeViewSet, basename="chat-mensajes")
router.register(r"chat/historial", ChatHistorialDeleteViewSet, basename="chat-historial-delete")

urlpatterns = [
    path("", include(router.urls)),
    path("chatbot/config/events", ChatbotConfigEventsResource.as_view(), name="chatbot_config_events"),
    path("chatbot/enviar", ChatbotViewSet.as_view({"post": "create"}), name="chatbot_enviar_legacy"),
    path("chat/profesionales", ChatContactoViewSet.as_view({"get": "list"}), name="chat_profesionales_legacy"),
    path("paciente/chat/mensajes", ChatMensajeViewSet.as_view({"get": "list", "post": "create"}), name="chat_mensajes_paciente_legacy"),
    path("chat/enviar", ChatMensajeViewSet.as_view({"post": "create"}), name="chat_enviar_legacy"),
    path("paciente/chat/enviar", ChatMensajeViewSet.as_view({"post": "create"}), name="chat_paciente_enviar_legacy"),
]
