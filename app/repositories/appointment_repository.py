from datetime import timedelta
from app.utils.db import db_cursor


def _format_time(value):
    """Convierte timedelta/time/string a string 'HH:MM'."""
    if value is None:
        return None
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    elif hasattr(value, 'strftime'):
        return value.strftime("%H:%M")
    elif isinstance(value, str):
        return value[:5] if len(value) >= 5 else value
    else:
        return str(value)


def appointment_exists(professional_id, fecha, hora):
    with db_cursor() as (_, cursor):
        cursor.execute(
            """
            SELECT idCita FROM Citas
            WHERE idProfesional = %s AND fecha = %s AND hora = %s
            AND estado != 'Cancelada'
            """,
            (professional_id, fecha, hora),
        )
        return cursor.fetchone() is not None


def create_appointment(patient_id, professional_id, fecha, hora, tipo_cita, motivo, creado_por_profesional=False):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO Citas (idPaciente, idProfesional, fecha, hora, tipoCita, motivo, estado, creado_por_profesional)
            VALUES (%s, %s, %s, %s, %s, %s, 'Pendiente', %s)
            """,
            (patient_id, professional_id, fecha, hora, tipo_cita, motivo, creado_por_profesional),
        )
        conn.commit()


def get_daily_availability(professional_id, fecha):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT hora_inicio, hora_fin
            FROM Disponibilidad
            WHERE idProfesional = %s AND DATE(fecha) = %s AND estado = 'Disponible'
            """,
            (professional_id, fecha),
        )
        return cursor.fetchall()


def get_taken_times(professional_id, fecha):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT hora FROM Citas
            WHERE idProfesional = %s AND fecha = %s AND estado != 'Cancelada'
            """,
            (professional_id, fecha),
        )
        return [_format_time(row["hora"]) for row in cursor.fetchall()]


def get_professional_appointments(professional_id, *, pending_only=False, page=1, limit=20):
    ESTADO_PENDIENTE = "= 'Pendiente'"
    ESTADO_ACTIVAS = "!= 'Cancelada'"
    estado_clause = ESTADO_PENDIENTE if pending_only else ESTADO_ACTIVAS
    fecha_clause = "AND c.fecha >= CURDATE()" if not pending_only else ""
    offset = (page - 1) * limit

    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            f"""
            SELECT c.idCita, r.nombre as paciente, r.fotoPerfil, c.fecha, c.hora,
                   c.tipoCita, c.motivo, c.estado, c.creado_por_profesional
            FROM Citas c
            JOIN Register r ON c.idPaciente = r.idUsuario
            WHERE c.idProfesional = %s AND c.estado {estado_clause} {fecha_clause}
            ORDER BY c.fecha ASC, c.hora ASC
            LIMIT %s OFFSET %s
            """,
            (professional_id, limit, offset),
        )
        citas = cursor.fetchall()
        for cita in citas:
            if cita.get("hora"):
                cita["hora"] = _format_time(cita["hora"])
        return citas


def get_taken_times_by_professional(professional_id, fecha):
    with db_cursor() as (_, cursor):
        cursor.execute(
            """
            SELECT hora FROM Citas
            WHERE idProfesional = %s AND fecha = %s AND estado != 'Cancelada'
            """,
            (professional_id, fecha),
        )
        return [_format_time(row[0]) for row in cursor.fetchall()]


def get_next_patient_appointment(patient_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT c.fecha, c.hora, c.tipoCita, r.nombre as profesional
            FROM Citas c
            JOIN Register r ON c.idProfesional = r.idUsuario
            WHERE c.idPaciente = %s AND c.estado = 'Pendiente' AND c.fecha >= CURDATE()
            ORDER BY c.fecha ASC, c.hora ASC LIMIT 1
            """,
            (patient_id,),
        )
        cita = cursor.fetchone()
        if cita and cita.get("hora"):
            cita["hora"] = _format_time(cita["hora"])
        return cita


def get_appointment_owner(appointment_id):
    with db_cursor() as (_, cursor):
        cursor.execute("SELECT idProfesional, idPaciente FROM Citas WHERE idCita = %s", (appointment_id,))
        return cursor.fetchone()


def update_appointment_status(appointment_id, estado):
    with db_cursor() as (conn, cursor):
        cursor.execute("UPDATE Citas SET estado = %s WHERE idCita = %s", (estado, appointment_id))
        conn.commit()


def get_patient_appointments(patient_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT c.idCita, c.fecha, c.hora, c.tipoCita, c.motivo, c.estado,
                   c.motivoCancelacion, r.nombre as profesional, c.creado_por_profesional
            FROM Citas c
            JOIN Register r ON c.idProfesional = r.idUsuario
            WHERE c.idPaciente = %s
            ORDER BY c.fecha DESC, c.hora DESC
            """,
            (patient_id,),
        )
        citas = cursor.fetchall()
        for cita in citas:
            if cita.get("hora"):
                cita["hora"] = _format_time(cita["hora"])
        return citas


def cancel_patient_appointment(appointment_id, patient_id, motivo_cancelacion):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            UPDATE Citas SET estado = 'Cancelada', motivoCancelacion = %s
            WHERE idCita = %s AND idPaciente = %s
            """,
            (motivo_cancelacion, appointment_id, patient_id),
        )
        conn.commit()
        return cursor.rowcount


def cancel_professional_appointment(appointment_id, professional_id, motivo_cancelacion):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            UPDATE Citas SET estado = 'Cancelada', motivoCancelacion = %s
            WHERE idCita = %s AND idProfesional = %s
            """,
            (motivo_cancelacion, appointment_id, professional_id),
        )
        conn.commit()
        return cursor.rowcount


def create_notification(user_id, rol, titulo, mensaje, tipo="Cita"):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO Notificaciones (idUsuario, rol, titulo, mensaje, tipo, enviado_por, estado)
            VALUES (%s, %s, %s, %s, %s, 'Sistema', 'enviado')
            """,
            (user_id, rol, titulo, mensaje, tipo),
        )
        conn.commit()


def get_month_availability(professional_id, anio, mes):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT fecha, hora_inicio, hora_fin
            FROM Disponibilidad
            WHERE idProfesional = %s
              AND YEAR(fecha) = %s
              AND MONTH(fecha) = %s
              AND estado = 'Disponible'
            """,
            (professional_id, anio, mes),
        )
        return cursor.fetchall()


def get_month_taken_counts(professional_id, anio, mes):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT DATE_FORMAT(fecha, '%Y-%m-%d') as fecha, COUNT(*) as ocupadas
            FROM Citas
            WHERE idProfesional = %s
              AND YEAR(fecha) = %s
              AND MONTH(fecha) = %s
              AND estado != 'Cancelada'
            GROUP BY fecha
            """,
            (professional_id, anio, mes),
        )
        return {row["fecha"]: row["ocupadas"] for row in cursor.fetchall()}
