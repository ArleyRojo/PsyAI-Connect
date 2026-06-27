# ============================================================
# ARCHIVO: services/professional_service.py
# ============================================================

from app.repositories import professional_repository


def get_profile(user_id):
    perfil = professional_repository.get_professional_profile(user_id)
    if not perfil:
        return {"success": False, "message": "Perfil no encontrado"}, 404
    if perfil.get("fechaRegistro"):
        perfil["fechaRegistro"] = perfil["fechaRegistro"].strftime("%d/%m/%Y")
    return {"success": True, "perfil": perfil}, 200


def update_profile(data):
    if not data.get("especialidad") and not data.get("licencia") and not data.get("experiencia"):
        return {"success": False, "message": "No se enviaron datos para actualizar"}, 400
    professional_repository.update_professional_profile(data)
    return {"success": True, "message": "Perfil actualizado"}, 200


def create_availability(professional_id, data):
    if not data.get("fecha") or not data.get("hora_inicio") or not data.get("hora_fin"):
        return {"success": False, "message": "Datos incompletos"}, 400
    professional_repository.create_availability(professional_id, data)
    return {"success": True, "message": "Disponibilidad agregada"}, 200


def get_availability(professional_id):
    datos = professional_repository.get_availability(professional_id)
    # Convierte tipos timedelta/time a string para serialización JSON
    for item in datos:
        if hasattr(item["hora_inicio"], "__str__"):
            item["hora_inicio"] = str(item["hora_inicio"])
        if hasattr(item["hora_fin"], "__str__"):
            item["hora_fin"] = str(item["hora_fin"])
        if hasattr(item["fecha"], "isoformat"):
            item["fecha"] = item["fecha"].isoformat()
    return {"success": True, "disponibilidad": datos}, 200


def get_dashboard(professional_id):
    data = professional_repository.get_dashboard_stats(professional_id)
    # Formatea fechas y horas para el dashboard
    for actividad in data["actividades"]:
        if actividad.get("fecha"):
            actividad["fecha"] = actividad["fecha"].strftime("%d/%m/%Y")
        if actividad.get("hora"):
            actividad["hora"] = str(actividad["hora"])
    for cita in data.get("proximas_citas", []):
        if cita.get("fecha"):
            cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y")
        if cita.get("hora"):
            cita["hora"] = str(cita["hora"])
    return {"success": True, **data}, 200


def list_patients(professional_id):
    return {"success": True, "pacientes": professional_repository.list_professional_patients(professional_id)}, 200


def save_diagnosis(professional_id, data):
    professional_repository.save_diagnosis(professional_id, data)
    return {"success": True, "message": "Diagnóstico guardado correctamente"}, 200


def diagnosis_history(professional_id):
    return {"success": True, "historial": professional_repository.get_diagnosis_history(professional_id)}, 200


def report_overview(professional_id):
    data = professional_repository.get_report_overview(professional_id)
    return {"success": True, **data}, 200


def create_report(professional_id, data):
    patient_id = data.get("idPaciente")
    if patient_id and not professional_repository.professional_has_patient(professional_id, patient_id):
        return {"success": False, "message": "No puedes generar reportes para este paciente"}, 403
    if patient_id and data.get("tipoReporte") == "diagnosticos":
        latest_diagnosis = professional_repository.get_latest_patient_diagnosis(professional_id, patient_id)
        if latest_diagnosis:
            data = {**data, **latest_diagnosis}  # Auto-completa con datos del diagnóstico más reciente
    professional_repository.create_report(professional_id, data)
    return {"success": True, "message": "Reporte generado correctamente"}, 200


def update_report(professional_id, data):
    professional_repository.update_report(professional_id, data)
    return {"success": True, "message": "Reporte actualizado correctamente"}, 200


def delete_report(professional_id, report_id):
    professional_repository.delete_report(professional_id, report_id)
    return {"success": True, "message": "Reporte eliminado correctamente"}, 200


def all_evolution(professional_id):
    from app.repositories import chat_repository

    historial = professional_repository.get_all_patient_evolution(professional_id)
    riesgo_bajo = chat_repository.get_low_risk_counts_for_professional(professional_id)
    return {
        "success": True,
        "historial": historial,
        "riesgo_bajo_chatbot": riesgo_bajo,
    }, 200


def get_deleted_reports(professional_id):
    return {"success": True, "reportes": professional_repository.get_deleted_reports(professional_id)}, 200


def list_patients_for_chat():
    return professional_repository.list_patients_for_chat()


def get_patient_chatbot_history(professional_id, patient_id):
    from app.repositories import chat_repository, professional_repository

    if not professional_repository.professional_has_patient(professional_id, patient_id):
        return {"success": False, "message": "No tienes acceso al historial de este paciente"}, 403

    return {"success": True, "historial": chat_repository.get_history(patient_id)}, 200
