import logging
from datetime import timedelta

from django.db.models import Q, Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.chatbot.models import (
    ChatbotConfig,
    ConversacionesChatbot,
    EncuestaChatbot,
    MensajesChat,
    PrediagnosticoChatbot,
)
from apps.authentication.models import Register

logger = logging.getLogger(__name__)


class ChatRepository:
    def save_conversation(self, patient_id, mensaje_usuario, respuesta_bot, nivel_emocional, palabras_riesgo):
        ConversacionesChatbot.objects.create(
            idPaciente_id=patient_id,
            mensajeUsuario=mensaje_usuario,
            respuestaChatbot=respuesta_bot,
            nivelEmocionalDetectado=nivel_emocional,
            palabrasRiesgoDetectadas=palabras_riesgo,
        )

    def get_history(self, patient_id, limit=40, today_only=False):
        qs = ConversacionesChatbot.objects.filter(
            idPaciente_id=patient_id,
        )
        if today_only:
            qs = qs.filter(fecha__date=timezone.now().date())
        qs = qs.order_by("-fecha")[:limit]
        rows = list(reversed(qs))

        historial = []
        for row in rows:
            if row.mensajeUsuario:
                historial.append({"tipo": "usuario", "mensaje": row.mensajeUsuario})
            if row.respuestaChatbot:
                historial.append({"tipo": "bot", "mensaje": row.respuestaChatbot})
        return historial

    def delete_history(self, patient_id):
        ConversacionesChatbot.objects.filter(idPaciente_id=patient_id).delete()

    def count_today_messages(self, patient_id):
        return ConversacionesChatbot.objects.filter(
            idPaciente_id=patient_id,
            fecha__date=timezone.now().date(),
        ).exclude(
            nivelEmocionalDetectado="Alto",
        ).count()

    def get_assigned_professionals(self, patient_id):
        try:
            from apps.professionals.models import PacientesProfesional
            rows = PacientesProfesional.objects.filter(
                idPaciente_id=patient_id,
                idProfesional__isnull=False,
            ).values_list("idProfesional_id", flat=True)
            return list(rows)
        except ImportError:
            return []

    def get_all_professional_ids(self):
        return list(
            Register.objects.filter(rol="profesional").values_list("idUsuario", flat=True)
        )

    def get_patient_name(self, patient_id):
        try:
            user = Register.objects.get(idUsuario=patient_id)
            return user.nombre
        except Register.DoesNotExist:
            return None

    def get_patient_email(self, patient_id):
        try:
            user = Register.objects.get(idUsuario=patient_id)
            return user.email
        except Register.DoesNotExist:
            return None

    def get_professional_emails(self, professional_ids):
        if not professional_ids:
            return []
        return list(
            Register.objects.filter(
                idUsuario__in=professional_ids, rol="profesional"
            ).values_list("email", "nombre")
        )

    def notificacion_reciente_existe(self, patient_name, tipo, horas=12):
        from apps.scheduling.models import Notificaciones
        cutoff = timezone.now() - timedelta(hours=horas)
        return Notificaciones.objects.filter(
            tipo=tipo,
            mensaje__icontains=patient_name,
            fecha__gte=cutoff,
        ).exists()

    def save_prediagnostico(self, patient_id, data):
        return PrediagnosticoChatbot.objects.create(
            idPaciente_id=patient_id,
            resumenPaciente=data.get("resumen_paciente", ""),
            resumenProfesional=data.get("resumen_profesional", ""),
            posiblesAreas=data.get("posibles_areas", []),
            recomendaciones=data.get("recomendaciones_paciente", []),
            nivelRiesgo=data.get("nivel_riesgo", "bajo"),
            requiereAtencionUrgente=bool(data.get("requiere_atencion_urgente")),
        )

    def get_prediagnosticos_for_professional(self, professional_id, days=30):
        from apps.professionals.models import PacientesProfesional
        cutoff = timezone.now() - timedelta(days=days)
        try:
            patient_ids = PacientesProfesional.objects.filter(
                idProfesional_id=professional_id
            ).values_list("idPaciente_id", flat=True)
            rows = PrediagnosticoChatbot.objects.filter(
                idPaciente_id__in=patient_ids,
                fecha__gte=cutoff,
            ).select_related("idPaciente").order_by("-fecha")
            return [
                {**r.to_dict(), "paciente": r.idPaciente.nombre}
                for r in rows
            ]
        except ImportError:
            return []

    def get_low_risk_counts_for_professional(self, professional_id, days=7):
        cutoff = timezone.now() - timedelta(days=days)
        try:
            from apps.professionals.models import PacientesProfesional

            patient_ids = PacientesProfesional.objects.filter(
                idProfesional_id=professional_id
            ).values_list("idPaciente_id", flat=True)

            rows = (
                ConversacionesChatbot.objects.filter(
                    nivelEmocionalDetectado="Bajo",
                    fecha__gte=cutoff,
                    idPaciente_id__in=patient_ids,
                )
                .values("idPaciente_id")
                .annotate(total=Count("idConversacion"))
            )
            return {str(r["idPaciente_id"]): r["total"] for r in rows}
        except ImportError:
            return {}


class ChatbotConfigRepository:
    def get_config(self):
        try:
            config = ChatbotConfig.objects.get(id=1)
            return config.to_dict()
        except ChatbotConfig.DoesNotExist:
            return None

    def save_config(self, data, admin_id):
        config, _ = ChatbotConfig.objects.get_or_create(id=1, defaults={"id": 1})
        field_map = {
            "system_prompt": "system_prompt",
            "tone": "tone",
            "interaction_rules": "interaction_rules",
            "risk_terms": "risk_terms",
            "crisis_response": "crisis_response",
            "medium_terms": "medium_terms",
            "medium_response": "medium_response",
            "fallback_response": "fallback_response",
            "crisis_phone": "crisis_phone",
            "thinking_level": "thinking_level",
            "prompt_history_window": "prompt_history_window",
            "gemini_history_window": "gemini_history_window",
            "temperature": "temperature",
            "top_p": "top_p",
            "max_tokens": "max_tokens",
            "max_tokens_user": "max_tokens_user",
            "daily_message_limit": "daily_message_limit",
        }
        update_fields = []
        for data_key, field in field_map.items():
            if data_key in data:
                setattr(config, field, data[data_key])
                update_fields.append(field)
        config.actualizado_por_id = admin_id
        update_fields.append("actualizado_por")
        config.fecha_actualizacion = timezone.now()
        update_fields.append("fecha_actualizacion")
        config.save(update_fields=update_fields)
        return 1

    def save_risk_terms_only(self, risk_terms_str, admin_id):
        config, _ = ChatbotConfig.objects.get_or_create(id=1, defaults={"id": 1})
        config.risk_terms = risk_terms_str
        config.actualizado_por_id = admin_id
        config.save(update_fields=["risk_terms", "actualizado_por"])
        return 1

    def clear_risk_terms(self, admin_id):
        try:
            config = ChatbotConfig.objects.get(id=1)
            config.risk_terms = ""
            config.save(update_fields=["risk_terms"])
            return 1
        except ChatbotConfig.DoesNotExist:
            return 0

    def get_historial_palabras_riesgo(self):
        rows = ConversacionesChatbot.objects.filter(
            palabrasRiesgoDetectadas__isnull=False,
        ).exclude(
            palabrasRiesgoDetectadas="",
        ).values(
            "idPaciente__nombre",
            "palabrasRiesgoDetectadas",
            "nivelEmocionalDetectado",
        )
        return [
            {
                "nombre": r["idPaciente__nombre"],
                "palabrasRiesgoDetectadas": r["palabrasRiesgoDetectadas"],
                "nivelEmocionalDetectado": r["nivelEmocionalDetectado"],
            }
            for r in rows
        ]


class MensajesRepository:
    def enviar_mensaje(self, id_emisor, id_receptor, mensaje):
        msg = MensajesChat.objects.create(
            idEmisor_id=id_emisor,
            idReceptor_id=id_receptor,
            mensaje=mensaje,
        )
        return msg.idMensaje

    def get_conversacion(self, id_usuario, id_otro, desde_id=0, limit=60):
        base_q = Q(idEmisor_id=id_usuario, idReceptor_id=id_otro) | Q(
            idEmisor_id=id_otro, idReceptor_id=id_usuario
        )
        if desde_id <= 0:
            qs = MensajesChat.objects.filter(base_q).order_by(
                "-fecha", "-idMensaje"
            )[:limit]
            rows = list(reversed(qs))
        else:
            qs = MensajesChat.objects.filter(base_q).filter(
                idMensaje__gt=desde_id,
            ).order_by("fecha", "idMensaje")[:limit]
            rows = list(qs)
        return [m.to_dict() for m in rows]

    def marcar_leidos(self, id_receptor, id_emisor):
        MensajesChat.objects.filter(
            idReceptor_id=id_receptor,
            idEmisor_id=id_emisor,
            leido=False,
        ).update(leido=True)

    def contar_no_leidos(self, id_receptor, id_emisor):
        return MensajesChat.objects.filter(
            idReceptor_id=id_receptor,
            idEmisor_id=id_emisor,
            leido=False,
        ).count()

    def get_ultimo_mensaje(self, id_usuario, id_otro):
        qs = MensajesChat.objects.filter(
            Q(idEmisor_id=id_usuario, idReceptor_id=id_otro)
            | Q(idEmisor_id=id_otro, idReceptor_id=id_usuario)
        ).order_by("-fecha")
        msg = qs.first()
        if msg:
            return {
                "idMensaje": msg.idMensaje,
                "idEmisor": msg.idEmisor_id,
                "mensaje": msg.mensaje,
                "fecha": msg.fecha,
            }
        return None

    def get_ultimos_mensajes_batch(self, id_usuario, id_otro_ids):
        if not id_otro_ids:
            return {}
        from django.db.models import Max, Q, Subquery, OuterRef, CharField
        from django.db.models.functions import Coalesce

        base_q = Q(idEmisor_id=id_usuario) | Q(idReceptor_id=id_usuario)
        other_ids = set(id_otro_ids)

        qs = MensajesChat.objects.filter(base_q).filter(
            Q(idEmisor_id__in=other_ids) | Q(idReceptor_id__in=other_ids)
        ).order_by("-fecha")

        result = {}
        for msg in qs:
            other = msg.idReceptor_id if msg.idEmisor_id == id_usuario else msg.idEmisor_id
            if other not in other_ids:
                continue
            if other not in result:
                result[other] = {
                    "idMensaje": msg.idMensaje,
                    "idEmisor": msg.idEmisor_id,
                    "mensaje": msg.mensaje,
                    "fecha": msg.fecha,
                }
        return result

    def contar_no_leidos_batch(self, id_usuario, id_otro_ids):
        if not id_otro_ids:
            return {}
        from django.db.models import Q, Count

        rows = (
            MensajesChat.objects.filter(
                idReceptor_id=id_usuario,
                leido=False,
                idEmisor_id__in=set(id_otro_ids),
            )
            .values("idEmisor_id")
            .annotate(total=Count("idMensaje"))
        )
        return {str(r["idEmisor_id"]): r["total"] for r in rows}