from django.db import models

from apps.authentication.models import Register


class ConversacionesChatbot(models.Model):
    idConversacion = models.AutoField(primary_key=True)
    idPaciente = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
    )
    mensajeUsuario = models.TextField(null=True, blank=True)
    respuestaChatbot = models.TextField(null=True, blank=True)
    nivelEmocionalDetectado = models.CharField(max_length=50, null=True, blank=True)
    palabrasRiesgoDetectadas = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "ConversacionesChatbot"

    def to_dict(self):
        return {
            "idConversacion": self.idConversacion,
            "idPaciente": self.idPaciente_id,
            "mensajeUsuario": self.mensajeUsuario,
            "respuestaChatbot": self.respuestaChatbot,
            "nivelEmocionalDetectado": self.nivelEmocionalDetectado,
            "palabrasRiesgoDetectadas": self.palabrasRiesgoDetectadas,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }


class EncuestaChatbot(models.Model):
    RECOMENDARIA_CHOICES = [
        ("si", "si"),
        ("no", "no"),
    ]

    id = models.AutoField(primary_key=True)
    idPaciente = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
    )
    fecha = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    utilidad = models.BooleanField()
    claridad = models.BooleanField()
    recomendaria = models.CharField(max_length=5, choices=RECOMENDARIA_CHOICES)
    comentario = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "EncuestaChatbot"

    def to_dict(self):
        return {
            "id": self.id,
            "idPaciente": self.idPaciente_id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "utilidad": self.utilidad,
            "claridad": self.claridad,
            "recomendaria": self.recomendaria,
            "comentario": self.comentario,
        }


class ChatbotConfig(models.Model):
    id = models.AutoField(primary_key=True)
    system_prompt = models.TextField(null=True, blank=True)
    tone = models.CharField(max_length=120, null=True, blank=True)
    interaction_rules = models.TextField(null=True, blank=True)
    risk_terms = models.TextField(null=True, blank=True)
    crisis_response = models.TextField(null=True, blank=True)
    medium_terms = models.TextField(null=True, blank=True)
    medium_response = models.TextField(null=True, blank=True)
    fallback_response = models.TextField(null=True, blank=True)
    off_topic_response = models.TextField(null=True, blank=True)
    crisis_phone = models.CharField(max_length=30, default="106", null=True, blank=True)
    thinking_level = models.CharField(max_length=20, default="low", null=True, blank=True)
    prompt_history_window = models.IntegerField(default=4, null=True, blank=True)
    gemini_history_window = models.IntegerField(default=12, null=True, blank=True)
    temperature = models.FloatField(default=0.55, null=True, blank=True)
    top_p = models.FloatField(default=0.9, null=True, blank=True)
    max_tokens = models.IntegerField(default=600, null=True, blank=True)
    max_tokens_user = models.IntegerField(default=1000, null=True, blank=True)
    daily_message_limit = models.IntegerField(default=20, null=True, blank=True)
    actualizado_por = models.ForeignKey(
        Register,
        on_delete=models.SET_NULL,
        db_column="actualizado_por",
        null=True,
        blank=True,
    )
    fecha_actualizacion = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "ChatbotConfig"

    def to_dict(self):
        return {
            "id": self.id,
            "system_prompt": self.system_prompt,
            "tone": self.tone,
            "interaction_rules": self.interaction_rules,
            "risk_terms": self.risk_terms,
            "crisis_response": self.crisis_response,
            "medium_terms": self.medium_terms,
            "medium_response": self.medium_response,
            "fallback_response": self.fallback_response,
            "off_topic_response": self.off_topic_response,
            "crisis_phone": self.crisis_phone,
            "thinking_level": self.thinking_level,
            "prompt_history_window": self.prompt_history_window,
            "gemini_history_window": self.gemini_history_window,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "max_tokens_user": self.max_tokens_user,
            "daily_message_limit": self.daily_message_limit,
            "actualizado_por": self.actualizado_por_id,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
        }


class MensajesChat(models.Model):
    idMensaje = models.AutoField(primary_key=True)
    idEmisor = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idEmisor",
        related_name="mensajes_enviados",
    )
    idReceptor = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idReceptor",
        related_name="mensajes_recibidos",
    )
    mensaje = models.TextField()
    leido = models.BooleanField(default=False, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "MensajesChat"

    def to_dict(self):
        return {
            "idMensaje": self.idMensaje,
            "idEmisor": self.idEmisor_id,
            "idReceptor": self.idReceptor_id,
            "mensaje": self.mensaje,
            "leido": self.leido,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }


class PrediagnosticoChatbot(models.Model):
    NIVEL_RIESGO_CHOICES = [
        ("bajo", "Bajo"),
        ("moderado", "Moderado"),
        ("alto", "Alto"),
        ("critico", "Crítico"),
    ]

    idPrediagnostico = models.AutoField(primary_key=True)
    idPaciente = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
    )
    resumenPaciente = models.TextField()
    resumenProfesional = models.TextField()
    posiblesAreas = models.JSONField(default=list)
    recomendaciones = models.JSONField(default=list)
    nivelRiesgo = models.CharField(max_length=20, choices=NIVEL_RIESGO_CHOICES, default="bajo")
    requiereAtencionUrgente = models.BooleanField(default=False)
    profesionalNotificado = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "PrediagnosticoChatbot"

    def to_dict(self):
        return {
            "idPrediagnostico": self.idPrediagnostico,
            "idPaciente": self.idPaciente_id,
            "resumenPaciente": self.resumenPaciente,
            "resumenProfesional": self.resumenProfesional,
            "posiblesAreas": self.posiblesAreas,
            "recomendaciones": self.recomendaciones,
            "nivelRiesgo": self.nivelRiesgo,
            "requiereAtencionUrgente": self.requiereAtencionUrgente,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }