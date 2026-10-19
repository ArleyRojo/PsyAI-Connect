from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.patients.views import (
    PerfilPacienteViewSet,
    PerfilFotoViewSet,
    PreferenciasPacienteViewSet,
    EvolucionViewSet,
    PacienteViewSet,
    ProfesionalViewSet,
    ChatbotAPIView,
    ChatbotEncuestaViewSet,
    ChatbotConfigViewSet,
    ChatbotConfigEventsResource,
    ConsentimientoChatbotViewSet,
    DocumentoPacienteViewSet,
    ChatContactoViewSet,
    ChatMensajeViewSet,
    AnamnesisViewSet,
)
from apps.core.webhooks import WhatsAppWebhook

app_name = "patients"

router = DefaultRouter()
router.register(r"perfil/paciente", PerfilPacienteViewSet, basename="perfil-paciente")
router.register(r"preferencias/paciente", PreferenciasPacienteViewSet, basename="preferencias-paciente")
router.register(r"evolucion", EvolucionViewSet, basename="evolucion")
router.register(r"pacientes", PacienteViewSet, basename="pacientes")
router.register(r"profesionales", ProfesionalViewSet, basename="profesionales")
router.register(r"chatbot/encuesta", ChatbotEncuestaViewSet, basename="chatbot-encuesta")
router.register(r"chatbot/config", ChatbotConfigViewSet, basename="chatbot-config")
router.register(r"paciente/consentimiento-chatbot", ConsentimientoChatbotViewSet, basename="consentimiento-chatbot")
router.register(r"paciente/documentos", DocumentoPacienteViewSet, basename="documento-paciente")
router.register(r"chat/contactos", ChatContactoViewSet, basename="chat-contactos")
router.register(r"chat/mensajes", ChatMensajeViewSet, basename="chat-mensajes")

urlpatterns = [
    path("", include(router.urls)),
    path("perfil/paciente/foto", PerfilFotoViewSet.as_view({"put": "update", "post": "create"}), name="perfil-foto"),
    path("chatbot", ChatbotAPIView.as_view(), name="chatbot"),
    path("chatbot/historial", ChatbotAPIView.as_view(), name="chatbot_historial"),
    path("chatbot/config", ChatbotConfigViewSet.as_view({"get": "list"}), name="chatbot_config_legacy"),
    path("chatbot/config/events", ChatbotConfigEventsResource.as_view(), name="chatbot_config_events"),
    path("paciente/documentos/subir", DocumentoPacienteViewSet.as_view({"post": "create"}), name="documento_subir"),
    path("paciente/documentos", DocumentoPacienteViewSet.as_view({"get": "list"}), name="documento_list"),
    path("chatbot/enviar", ChatbotAPIView.as_view(), name="chatbot_enviar_legacy"),
    path("perfil/foto", PerfilFotoViewSet.as_view({"put": "update", "post": "create"}), name="perfil_foto_legacy"),
    path("perfil/paciente/<int:pk>", PerfilPacienteViewSet.as_view({"get": "retrieve", "put": "update"}), name="perfil-paciente-detail"),
    path("chat/profesionales", ChatContactoViewSet.as_view({"get": "list"}), name="chat_profesionales_legacy"),
    path("paciente/chat/mensajes", ChatMensajeViewSet.as_view({"get": "list", "post": "create"}), name="chat_mensajes_paciente_legacy"),
    path("chat/enviar", ChatMensajeViewSet.as_view({"post": "create"}), name="chat_enviar_legacy"),
    path("paciente/chat/enviar", ChatMensajeViewSet.as_view({"post": "create"}), name="chat_paciente_enviar_legacy"),
    path("evolucion", EvolucionViewSet.as_view({"get": "list", "post": "create"}), name="evolucion"),
    # Legacy aliases sin barra final (compatibles con API.md y el frontend)
    path("pacientes", PacienteViewSet.as_view({"get": "list"}), name="pacientes"),
    path("profesionales", ProfesionalViewSet.as_view({"get": "list"}), name="profesionales"),
    # Alias con tilde para compatibilidad con frontend
    path("evolución", EvolucionViewSet.as_view({"get": "list", "post": "create"}), name="evolucion_tilde"),
    # Anamnesis — con y sin barra final (el JS llama sin barra)
    path(
        "paciente/<int:paciente_id>/anamnesis",
        AnamnesisViewSet.as_view({
            "get": "retrieve", "post": "create",
            "put": "update", "delete": "destroy",
        }),
        name="anamnesis",
    ),
    path(
        "paciente/<int:paciente_id>/anamnesis/",
        AnamnesisViewSet.as_view({
            "get": "retrieve", "post": "create",
            "put": "update", "delete": "destroy",
        }),
        name="anamnesis-trailing",
    ),
    # Webhook WhatsApp
    path("whatsapp/webhook/", WhatsAppWebhook.as_view(), name="whatsapp-webhook"),
]
