from django.db.models import OuterRef, Subquery
from django.utils import timezone

from apps.authentication.models import Register
from apps.patients.models import PerfilPaciente, EvolucionPaciente
from apps.professionals.models import PerfilProfesional


class PatientRepository:
    def update_profile_photo(self, filename, user_id):
        Register.objects.filter(idUsuario=user_id).update(fotoPerfil=filename)

    def get_patient_profile(self, user_id):
        try:
            user = Register.objects.get(idUsuario=user_id)
        except Register.DoesNotExist:
            return None
        try:
            perfil = PerfilPaciente.objects.get(idPaciente=user_id)
        except PerfilPaciente.DoesNotExist:
            perfil = None
        return {
            "nombre": user.nombre,
            "email": user.email,
            "fotoPerfil": user.fotoPerfil,
            "fechaRegistro": user.fechaRegistro,
            "edad": perfil.edad if perfil else None,
            "genero": perfil.genero if perfil else None,
            "numeroTelefonico": perfil.numeroTelefonico if perfil else None,
            "consentimiento_chatbot": perfil.consentimiento_chatbot if perfil else None,
            "prefNotificaciones": perfil.prefNotificaciones if perfil else "Activadas",
            "prefRecordatorios": perfil.prefRecordatorios if perfil else "Activados",
            "prefContacto": perfil.prefContacto if perfil else "Correo",
        }

    def save_chatbot_survey(self, user_id, data):
        try:
            from apps.chatbot.models import EncuestaChatbot
            EncuestaChatbot.objects.create(
                idPaciente_id=user_id,
                utilidad=data.get("utilidad"),
                claridad=data.get("claridad"),
                recomendaria=data.get("recomendaria"),
                comentario=data.get("comentario"),
            )
        except (ImportError, LookupError):
            pass

    def update_patient_profile(self, data):
        user_id = data.get("idUsuario")
        numero = data.get("numeroTelefonico")
        perfil, created = PerfilPaciente.objects.get_or_create(
            idPaciente_id=user_id,
            defaults={"consentimiento_chatbot": False},
        )
        perfil.numeroTelefonico = numero
        perfil.save(update_fields=["numeroTelefonico"])

    def get_preferences(self, user_id):
        try:
            perfil = PerfilPaciente.objects.get(idPaciente=user_id)
            return {
                "notificaciones": perfil.prefNotificaciones,
                "recordatorios": perfil.prefRecordatorios,
                "contacto": perfil.prefContacto,
            }
        except PerfilPaciente.DoesNotExist:
            return {
                "notificaciones": "Activadas",
                "recordatorios": "Activados",
                "contacto": "Correo",
            }

    def save_preferences(self, user_id, notificaciones, recordatorios, contacto):
        perfil, _ = PerfilPaciente.objects.get_or_create(
            idPaciente_id=user_id,
            defaults={"consentimiento_chatbot": False},
        )
        perfil.prefNotificaciones = notificaciones
        perfil.prefRecordatorios = recordatorios
        perfil.prefContacto = contacto
        perfil.save(update_fields=["prefNotificaciones", "prefRecordatorios", "prefContacto"])

    def get_chatbot_consent(self, user_id):
        try:
            perfil = PerfilPaciente.objects.get(idPaciente=user_id)
            return bool(perfil.consentimiento_chatbot)
        except PerfilPaciente.DoesNotExist:
            return False

    def update_chatbot_consent(self, user_id, consent):
        perfil, created = PerfilPaciente.objects.get_or_create(
            idPaciente_id=user_id,
        )
        perfil.consentimiento_chatbot = bool(consent)
        perfil.save(update_fields=["consentimiento_chatbot"])

    def create_patient_evolution(self, user_id, data):
        EvolucionPaciente.objects.create(
            idPaciente_id=user_id,
            estadoEmocional=data.get("estadoEmocional"),
            nivelEnergia=data.get("nivelEnergia"),
            notasPersonales=data.get("notasPersonales"),
        )

    def get_patient_evolution_history(self, user_id):
        rows = EvolucionPaciente.objects.filter(
            idPaciente_id=user_id
        ).order_by("-fecha")
        return [
            {
                "estadoEmocional": r.estadoEmocional,
                "nivelEnergia": r.nivelEnergia,
                "notasPersonales": r.notasPersonales,
                "fecha": r.fecha.strftime("%d/%m/%Y") if r.fecha else None,
                "fechaRaw": r.fecha,
            }
            for r in rows
        ]

    def list_patients(self, page=1, limit=20):
        offset = (page - 1) * limit
        users = Register.objects.filter(
            rol="paciente"
        ).order_by("nombre")[offset : offset + limit]
        return [
            {
                "idUsuario": u.idUsuario,
                "nombre": u.nombre,
                "email": u.email,
                "fotoPerfil": u.fotoPerfil,
            }
            for u in users
        ]

    def list_professionals(self):
        rows = Register.objects.filter(
            rol="profesional"
        ).order_by("nombre").values("idUsuario", "nombre")
        return [{"idUsuario": r["idUsuario"], "nombre": r["nombre"]} for r in rows]

    def list_professionals_for_patient(self, patient_id):
        rows = (
            Register.objects.filter(rol="profesional")
            .order_by("nombre")
            .values("idUsuario", "nombre", "fotoPerfil")
        )
        especialidades = {
            p.idProfesional_id: p.especialidad
            for p in PerfilProfesional.objects.filter(
                idProfesional_id__in=rows.values_list("idUsuario", flat=True)
            )
        }
        return [
            {
                "idUsuario": r["idUsuario"],
                "nombre": r["nombre"],
                "fotoPerfil": r["fotoPerfil"],
                "especialidad": especialidades.get(r["idUsuario"]),
            }
            for r in rows
        ]
