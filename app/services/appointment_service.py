from datetime import date, datetime, timedelta

from app.repositories import appointment_repository


def create_appointment(patient_id, data, *, created_by_professional=False):
    professional_id = data.get("idProfesional")
    fecha = data.get("fecha")
    hora = data.get("hora")
    tipo_cita = data.get("tipoCita")
    motivo = data.get("motivo")

    if not professional_id or not fecha or not hora:
        return {"success": False, "message": "Datos incompletos"}, 400

    if appointment_repository.appointment_exists(professional_id, fecha, hora):
        msg = "Ese horario ya está ocupado" if created_by_professional else "Horario no disponible"
        return {"success": False, "message": msg}, 409

    appointment_repository.create_appointment(
        data.get("idPaciente") if created_by_professional else patient_id,
        professional_id,
        fecha,
        hora,
        tipo_cita,
        motivo,
        created_by_professional if created_by_professional else False,
    )
    return {"success": True, "message": "Cita agendada correctamente"}, 200


def get_available_times(professional_id, fecha):
    if not professional_id or not fecha:
        return {"success": False, "message": "Datos incompletos"}, 400

    disponibilidades = appointment_repository.get_daily_availability(professional_id, fecha)
    if not disponibilidades:
        return {"success": True, "horarios": []}, 200

    ocupadas = appointment_repository.get_taken_times(professional_id, fecha)
    horarios_set = set()

    for disponibilidad in disponibilidades:
        inicio = disponibilidad["hora_inicio"]
        fin = disponibilidad["hora_fin"]
        if isinstance(inicio, timedelta):
            inicio = (datetime.min + inicio).time()
        if isinstance(fin, timedelta):
            fin = (datetime.min + fin).time()

        hora_actual = inicio
        while hora_actual < fin:
            h_str = hora_actual.strftime("%H:%M")
            if h_str not in ocupadas:
                horarios_set.add(h_str)
            hora_actual = (datetime.combine(date.today(), hora_actual) + timedelta(minutes=30)).time()

    horarios_ordenados = sorted(list(horarios_set))
    return {"success": True, "horarios": horarios_ordenados}, 200


def list_professional_appointments(professional_id, *, pending_only=False, page=1, limit=20):
    citas = appointment_repository.get_professional_appointments(
        professional_id,
        pending_only=pending_only,
        page=page,
        limit=limit,
    )
    for cita in citas:
        if cita.get("fecha"):
            cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y")
        if cita.get("hora"):
            cita["hora"] = str(cita["hora"])
        if cita.get("fotoPerfil"):
            cita["foto_perfil"] = cita["fotoPerfil"]
    return {"success": True, "citas": citas}, 200


def get_taken_slots(professional_id, fecha):
    if not professional_id or not fecha:
        return {"success": False, "message": "Datos incompletos"}, 400
    return {
        "success": True,
        "horarios_ocupados": appointment_repository.get_taken_times_by_professional(professional_id, fecha),
    }, 200


def get_next_patient_appointment(patient_id):
    cita = appointment_repository.get_next_patient_appointment(patient_id)
    if not cita:
        return {"success": True, "cita": None}, 200
    cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y")
    cita["hora"] = str(cita["hora"])
    return {"success": True, "cita": cita}, 200


def update_status(appointment_id, estado, acting_professional_id):
    if not appointment_id or not estado:
        return {"success": False, "message": "Datos incompletos"}, 400

    row = appointment_repository.get_appointment_owner(appointment_id)
    if not row:
        return {"success": False, "message": "Cita no encontrada"}, 404
    if row[0] != acting_professional_id:
        return {"success": False, "message": "No tienes permiso"}, 403

    appointment_repository.update_appointment_status(appointment_id, estado)
    return {"success": True, "message": f"Cita {estado}"}, 200


def list_patient_appointments(patient_id):
    citas = appointment_repository.get_patient_appointments(patient_id)
    for cita in citas:
        if cita.get("fecha"):
            cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y")
        if cita.get("hora"):
            cita["hora"] = str(cita["hora"])
    return {"success": True, "citas": citas}, 200


def cancel_appointment(appointment_id, patient_id, motivo_cancelacion):
    if not motivo_cancelacion or not motivo_cancelacion.strip():
        return {"success": False, "message": "Debes indicar el motivo de la cancelación"}, 400

    row = appointment_repository.get_appointment_owner(appointment_id)
    if not row:
        return {"success": False, "message": "Cita no encontrada"}, 404
    
    professional_id = row[0]

    rowcount = appointment_repository.cancel_patient_appointment(appointment_id, patient_id, motivo_cancelacion.strip())
    if rowcount == 0:
        return {"success": False, "message": "Cita no encontrada o ya cancelada"}, 404
        
    if professional_id:
        appointment_repository.create_notification(
            user_id=professional_id,
            rol='profesional',
            titulo="Cita cancelada por paciente",
            mensaje=f"El paciente ha cancelado su cita. Motivo: {motivo_cancelacion.strip()}",
            tipo="Alerta"
        )
        
    return {"success": True, "message": "Cita cancelada correctamente"}, 200


def cancel_professional_appointment(appointment_id, professional_id, motivo_cancelacion):
    if not motivo_cancelacion or not motivo_cancelacion.strip():
        return {"success": False, "message": "Debes indicar el motivo de la cancelación"}, 400

    row = appointment_repository.get_appointment_owner(appointment_id)
    if not row:
        return {"success": False, "message": "Cita no encontrada"}, 404
    if row[0] != professional_id:
        return {"success": False, "message": "No tienes permiso para cancelar esta cita"}, 403

    rowcount = appointment_repository.cancel_professional_appointment(
        appointment_id, professional_id, motivo_cancelacion.strip()
    )
    if rowcount == 0:
        return {"success": False, "message": "No se pudo cancelar la cita"}, 400

    patient_id = row[1] if len(row) > 1 else None
    if patient_id:
        appointment_repository.create_notification(
            user_id=patient_id,
            rol='paciente',
            titulo="Cita cancelada",
            mensaje=f"El profesional ha cancelado tu cita. Motivo: {motivo_cancelacion.strip()}",
            tipo="Alerta"
        )

    return {"success": True, "message": "Cita cancelada correctamente"}, 200


def get_available_dates(professional_id, anio, mes):
    if not professional_id or not anio or not mes:
        return {"success": False, "message": "Datos incompletos"}, 400

    disponibilidades = appointment_repository.get_month_availability(professional_id, anio, mes)
    if not disponibilidades:
        return {"success": True, "fechas": []}, 200

    slots_por_fecha = {}
    for disponibilidad in disponibilidades:
        fecha_str = disponibilidad["fecha"].strftime("%Y-%m-%d")
        inicio = disponibilidad["hora_inicio"]
        fin = disponibilidad["hora_fin"]
        if isinstance(inicio, timedelta):
            inicio = (datetime.min + inicio).time()
        if isinstance(fin, timedelta):
            fin = (datetime.min + fin).time()
        slots_por_fecha.setdefault(fecha_str, 0)
        hora_actual = inicio
        while hora_actual < fin:
            slots_por_fecha[fecha_str] += 1
            hora_actual = (datetime.combine(date.today(), hora_actual) + timedelta(minutes=30)).time()

    ocupadas_por_fecha = appointment_repository.get_month_taken_counts(professional_id, anio, mes)
    fechas = [
        fecha_key
        for fecha_key, total_slots in slots_por_fecha.items()
        if ocupadas_por_fecha.get(fecha_key, 0) < total_slots
    ]
    return {"success": True, "fechas": sorted(fechas)}, 200
