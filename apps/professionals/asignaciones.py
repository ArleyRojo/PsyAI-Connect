"""
Asignación y reasignación de pacientes por el administrador (HU-57 / HU-58, RN-27).

Reasignar un caso:
- El historial clínico pasa completo al nuevo profesional: diagnósticos y consejos
  (cuelgan de la asignación), anamnesis, documentos clínicos y reportes.
- El profesional anterior deja de tener acceso al paciente.
- Las citas futuras (Pendiente/Confirmada) con el profesional anterior se cancelan.
- Queda registrado (ReasignacionesCaso + Logs) y se avisa al paciente y a los dos profesionales.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.authentication.repositories import AuthRepository
from apps.documents.repositories import DocumentoRepository
from apps.patients.repositories import PatientRepository
from apps.professionals.repositories import ProfessionalRepository
from apps.scheduling.repositories import AppointmentRepository

logger = logging.getLogger(__name__)

MOTIVO_MIN = 5
MOTIVO_MAX = 500
ESTADOS_CITA_ACTIVA = ("Pendiente", "Confirmada")


# ── Consultas ──────────────────────────────────────────────────────────────
def listar_asignaciones():
    """Pacientes activos con sus profesionales y los profesionales verificados disponibles."""
    auth_repo = AuthRepository()
    professional_repo = ProfessionalRepository()
    pacientes = auth_repo.get_active_patients_for_assignment()
    asignaciones = professional_repo.list_patient_assignments()
    citas = {
        (r["idPaciente_id"], r["idProfesional_id"]): r["n"]
        for r in AppointmentRepository().get_future_appointment_counts_by_pair(
            ESTADOS_CITA_ACTIVA, timezone.localdate()
        )
    }
    por_paciente = {}
    for a in asignaciones:
        por_paciente.setdefault(a.idPaciente_id, []).append({
            "idProfesional": a.idProfesional_id,
            "nombre": a.idProfesional.nombre,
            "desde": a.fecha.isoformat() if a.fecha else None,
            "citasFuturas": citas.get((a.idPaciente_id, a.idProfesional_id), 0),
        })

    profesionales = auth_repo.get_verified_professionals_for_assignment()
    return {
        "success": True,
        "pacientes": [
            {
                "idPaciente": p["idUsuario"],
                "nombre": p["nombre"],
                "email": p["email"],
                "fotoPerfil": p["fotoPerfil"],
                "profesionales": por_paciente.get(p["idUsuario"], []),
            }
            for p in pacientes
        ],
        "profesionales": [
            {
                "idProfesional": p["idUsuario"],
                "nombre": p["nombre"],
                "especialidad": p["perfil_profesional__especialidad"],
                "pacientes": p["pacientes"],
            }
            for p in profesionales
        ],
    }, 200


def historial():
    filas = ProfessionalRepository().get_assignment_history_rows()
    return {"success": True, "historial": [f.to_dict() for f in filas]}, 200


# ── Validaciones ───────────────────────────────────────────────────────────
def _entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _paciente(paciente_id):
    return AuthRepository().get_active_patient_for_assignment(paciente_id)


def _profesional_verificado(profesional_id):
    return AuthRepository().get_verified_professional_for_assignment(profesional_id)


def _motivo(data):
    motivo = str((data or {}).get("motivo") or "").strip()
    if len(motivo) < MOTIVO_MIN:
        return None, f"Escribe el motivo (mínimo {MOTIVO_MIN} caracteres)."
    if len(motivo) > MOTIVO_MAX:
        return None, f"El motivo no puede superar {MOTIVO_MAX} caracteres."
    return motivo, None


# ── Asignar (HU-57) ────────────────────────────────────────────────────────
def asignar(data, administrador="Admin"):
    paciente = _paciente(_entero((data or {}).get("idPaciente")))
    if not paciente:
        return {"success": False, "message": "Paciente no encontrado"}, 404
    profesional = _profesional_verificado(_entero((data or {}).get("idProfesional")))
    if not profesional:
        return {"success": False, "message": "Elige un profesional verificado"}, 400
    motivo, error = _motivo(data)
    if error:
        return {"success": False, "message": error}, 400
    repo = ProfessionalRepository()
    if repo.assignment_exists_for_users(paciente, profesional):
        return {"success": False, "message": f"{paciente.nombre} ya está asignado a {profesional.nombre}"}, 400

    with transaction.atomic():
        repo.create_case_assignment(paciente, profesional)
        registro = repo.create_case_history(
            idPaciente=paciente, idProfesionalNuevo=profesional, motivo=motivo, administrador=administrador,
        )
    _registrar_log("Asignar paciente", f"{paciente.nombre} asignado a {profesional.nombre}. Motivo: {motivo}",
                   administrador, paciente.nombre)
    _avisar_asignacion(paciente, profesional)
    return {"success": True, "message": f"{paciente.nombre} quedó asignado a {profesional.nombre}",
            "registro": registro.to_dict()}, 201


# ── Reasignar (HU-58) ──────────────────────────────────────────────────────
def reasignar(data, administrador="Admin"):
    data = data or {}
    paciente = _paciente(_entero(data.get("idPaciente")))
    if not paciente:
        return {"success": False, "message": "Paciente no encontrado"}, 404

    anterior_id = _entero(data.get("idProfesionalAnterior"))
    repo = ProfessionalRepository()
    asignacion = repo.get_case_assignment(paciente, anterior_id)
    if not asignacion:
        return {"success": False, "message": "El paciente no está asignado a ese profesional"}, 400
    anterior = asignacion.idProfesional

    nuevo = _profesional_verificado(_entero(data.get("idProfesionalNuevo")))
    if not nuevo:
        return {"success": False, "message": "Elige un profesional verificado"}, 400
    if nuevo.idUsuario == anterior.idUsuario:
        return {"success": False, "message": "Elige un profesional diferente al actual"}, 400

    motivo, error = _motivo(data)
    if error:
        return {"success": False, "message": error}, 400

    with transaction.atomic():
        destino = repo.get_destination_assignment(paciente, nuevo)
        if destino:
            # El nuevo ya atendía al paciente: se le pasan los registros y se quita la asignación anterior
            repo.transfer_assignment_records(asignacion, destino)
            repo.delete_assignment(asignacion)
        else:
            repo.change_assignment_professional(asignacion, nuevo)

        _transferir_historial(paciente.idUsuario, anterior.idUsuario, nuevo.idUsuario)

        citas_canceladas = AppointmentRepository().cancel_future_appointments_for_reassignment(
            paciente.idUsuario, anterior.idUsuario, nuevo.nombre,
            ESTADOS_CITA_ACTIVA, timezone.localdate(),
        )
        registro = repo.create_case_history(
            idPaciente=paciente, idProfesionalAnterior=anterior, idProfesionalNuevo=nuevo,
            motivo=motivo, administrador=administrador, citasCanceladas=citas_canceladas,
        )

    _registrar_log(
        "Reasignar caso",
        f"{paciente.nombre}: de {anterior.nombre} a {nuevo.nombre}. "
        f"Citas canceladas: {citas_canceladas}. Motivo: {motivo}",
        administrador, paciente.nombre,
    )
    _avisar_reasignacion(paciente, anterior, nuevo, citas_canceladas)

    mensaje = f"{paciente.nombre} ahora está con {nuevo.nombre}"
    if citas_canceladas:
        mensaje += f". Se cancelaron {citas_canceladas} cita(s) con {anterior.nombre}"
    return {"success": True, "message": mensaje, "registro": registro.to_dict()}, 200


def _transferir_historial(paciente_id, anterior_id, nuevo_id):
    """Pasa al nuevo profesional los registros clínicos del paciente que tenía el anterior."""
    PatientRepository().transfer_anamnesis(paciente_id, anterior_id, nuevo_id)
    DocumentoRepository().transfer_clinical_documents(paciente_id, anterior_id, nuevo_id)
    ProfessionalRepository().transfer_professional_reports(paciente_id, anterior_id, nuevo_id)


# ── Registro y avisos ──────────────────────────────────────────────────────
def _registrar_log(accion, detalle, administrador, paciente_nombre):
    from apps.admin_panel.repositories import AdminRepository
    AdminRepository().registrar_log(
        modulo="Asignaciones", accion=accion, detalle=detalle,
        usuario_afectado=paciente_nombre, administrador=administrador,
    )


def _campana(usuario, rol, titulo, mensaje, tipo):
    try:
        AppointmentRepository().create_notification_attempt(
            idUsuario=usuario, rol=rol, titulo=titulo, mensaje=mensaje, tipo=tipo,
            enviado_por="Sistema", estado="enviado", canal="interno",
        )
    except Exception as e:  # el aviso nunca debe romper la reasignación
        logger.error("No se pudo crear la notificación interna: %s", e)


def _avisar_paciente(paciente, titulo, mensaje):
    _campana(paciente, "paciente", titulo, mensaje, "Asignacion")
    try:
        from apps.core.notifier import notificar_paciente
        notificar_paciente(paciente, titulo, mensaje, "notificacion_admin")
    except Exception as e:
        logger.error("No se pudo avisar al paciente: %s", e)


def _avisar_profesional(profesional, titulo, mensaje):
    _campana(profesional, "profesional", titulo, mensaje, "Asignacion")
    if not profesional.email:
        return
    try:
        enlace = f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/aside-professional/patients.html"
        send_mail(
            f"[PsyAI] {titulo}",
            f"Hola {profesional.nombre},\n\n{mensaje}\n\nVer en PsyAI Connect: {enlace}",
            settings.DEFAULT_FROM_EMAIL, [profesional.email], fail_silently=True,
        )
    except Exception as e:
        logger.error("No se pudo enviar el correo al profesional: %s", e)


def _avisar_asignacion(paciente, profesional):
    _avisar_paciente(
        paciente, "Tienes un profesional asignado",
        f"{profesional.nombre} será tu profesional en PsyAI Connect. Ya puedes agendar tus citas.",
    )
    _avisar_profesional(
        profesional, "Nuevo paciente asignado",
        f"El administrador te asignó a {paciente.nombre}.",
    )


def _avisar_reasignacion(paciente, anterior, nuevo, citas_canceladas):
    extra = (f" Se cancelaron {citas_canceladas} cita(s) que tenías con {anterior.nombre}; "
             f"agenda de nuevo con {nuevo.nombre}." if citas_canceladas else "")
    _avisar_paciente(
        paciente, "Cambio de profesional",
        f"Tu caso ahora lo atiende {nuevo.nombre}. Tu historial clínico se conserva.{extra}",
    )
    _avisar_profesional(
        nuevo, "Nuevo paciente reasignado",
        f"El administrador te reasignó a {paciente.nombre}, que antes atendía {anterior.nombre}. "
        f"Ya tienes acceso a todo su historial clínico.",
    )
    _avisar_profesional(
        anterior, "Paciente reasignado",
        f"{paciente.nombre} fue reasignado a {nuevo.nombre}. Ya no aparecerá en tu lista de pacientes"
        + (f" y se cancelaron {citas_canceladas} cita(s) futuras." if citas_canceladas else "."),
    )
