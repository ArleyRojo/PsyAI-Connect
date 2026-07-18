from django.contrib import admin

from apps.chatbot.models import (
    ChatbotConfig,
    ConversacionesChatbot,
    EncuestaChatbot,
    MensajesChat,
)


@admin.register(ConversacionesChatbot)
class ConversacionesChatbotAdmin(admin.ModelAdmin):
    list_display = ("idConversacion", "idPaciente", "nivelEmocionalDetectado", "fecha")
    list_filter = ("nivelEmocionalDetectado",)
    readonly_fields = ("fecha",)


@admin.register(EncuestaChatbot)
class EncuestaChatbotAdmin(admin.ModelAdmin):
    list_display = ("id", "idPaciente", "utilidad", "claridad", "recomendaria", "fecha")
    list_filter = ("recomendaria",)
    readonly_fields = ("fecha",)


@admin.register(ChatbotConfig)
class ChatbotConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "tone", "temperature", "daily_message_limit", "fecha_actualizacion")
    readonly_fields = ("fecha_actualizacion",)


@admin.register(MensajesChat)
class MensajesChatAdmin(admin.ModelAdmin):
    list_display = ("idMensaje", "idEmisor", "idReceptor", "leido", "fecha")
    list_filter = ("leido",)
    readonly_fields = ("fecha",)
