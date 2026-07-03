# ============================================================
# ARCHIVO: repositories/professional_repository.py
# ============================================================

from app.utils.db import db_cursor


def get_professional_profile(user_id):
    # Obtiene el perfil completo de un profesional combinando Register y PerfilProfesional
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT r.nombre, r.email, r.fotoPerfil, r.fechaRegistro,
                   p.especialidad, p.licencia, p.experiencia, p.estado,
                   p.edad, p.genero
            FROM Register r
            LEFT JOIN PerfilProfesional p ON r.idUsuario = p.idProfesional
            WHERE r.idUsuario = %s
            """,
            (user_id,),
        )
        return cursor.fetchone()


def update_professional_profile(data):
    # Actualiza los datos del perfil profesional (especialidad, licencia, experiencia)
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            UPDATE PerfilProfesional
            SET especialidad = %s, licencia = %s, experiencia = %s
            WHERE idProfesional = %s
            """,
            (data.get("especialidad"), data.get("licencia"), data.get("experiencia"), data.get("idUsuario")),
        )
        conn.commit()


def create_availability(professional_id, data):
    # Crea un bloque de disponibilidad en la agenda del profesional
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO Disponibilidad (idProfesional, fecha, hora_inicio, hora_fin, estado)
            VALUES (%s, %s, %s, %s, 'Disponible')
            """,
            (professional_id, data.get("fecha"), data.get("hora_inicio"), data.get("hora_fin")),
        )
        conn.commit()


def get_availability(professional_id):
    # Obtiene todos los bloques de disponibilidad activos de un profesional
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT fecha, hora_inicio, hora_fin, estado
            FROM Disponibilidad
            WHERE idProfesional = %s AND estado = 'Disponible'
            """,
            (professional_id,),
        )
        return cursor.fetchall()


def get_dashboard_stats(professional_id):
    # Recolecta todas las estadísticas del dashboard del profesional en múltiples consultas
    with db_cursor(dictionary=True) as (_, cursor):
        # Estadísticas principales: pacientes activos, citas hoy, citas pendientes
        cursor.execute(
            """
            SELECT 
                COUNT(DISTINCT CASE WHEN estado != 'Cancelada' THEN idPaciente END) as pacientes_activos,
                COUNT(CASE WHEN fecha = CURDATE() AND estado != 'Cancelada' THEN 1 END) as citas_hoy,
                COUNT(CASE WHEN estado = 'Pendiente' THEN 1 END) as citas_pendientes
            FROM Citas
            WHERE idProfesional = %s
            """,
            (professional_id,),
        )
        stats = cursor.fetchone()

        # Últimas 3 actividades registradas
        cursor.execute(
            """
            SELECT r.nombre as paciente, c.fecha, c.hora, c.tipoCita, c.estado, c.idCita
            FROM Citas c
            JOIN Register r ON c.idPaciente = r.idUsuario
            WHERE c.idProfesional = %s AND c.estado != 'Cancelada'
            ORDER BY c.fecha DESC, c.hora DESC LIMIT 3
            """,
            (professional_id,),
        )
        actividades = cursor.fetchall()

        # Próximas 10 citas en los siguientes 7 días
        cursor.execute(
            """
            SELECT c.idCita, r.nombre as paciente, r.idUsuario as idPaciente, r.fotoPerfil,
                   c.fecha, c.hora, c.tipoCita, c.estado
            FROM Citas c
            JOIN Register r ON c.idPaciente = r.idUsuario
            WHERE c.idProfesional = %s 
              AND c.estado IN ('Pendiente', 'Confirmada')
              AND c.fecha >= CURDATE()
              AND c.fecha <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
            ORDER BY c.fecha ASC, c.hora ASC LIMIT 10
            """,
            (professional_id,),
        )
        proximas_citas = cursor.fetchall()

        # Estadísticas de reportes del profesional
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_reportes,
                SUM(estado = 'Completado') as completados,
                SUM(estado = 'Pendiente') as pendientes
            FROM Reportes 
            WHERE idProfesional = %s AND COALESCE(eliminado, 0) = 0
            """,
            (professional_id,),
        )
        reportes_stats = cursor.fetchone()

        # Estadísticas de evolución de pacientes (con citas en los últimos 30 días)
        cursor.execute(
            """
            SELECT 
                COUNT(DISTINCT c.idPaciente) as pacientes_con_citas,
                COUNT(DISTINCT CASE WHEN e.fecha >= DATE_SUB(CURDATE(), INTERVAL 14 DAY) THEN e.idPaciente END) as pacientes_con_evolucion_reciente
            FROM Citas c
            LEFT JOIN EvolucionPaciente e ON e.idPaciente = c.idPaciente
            WHERE c.idProfesional = %s 
              AND c.estado != 'Cancelada'
              AND c.fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """,
            (professional_id,),
        )
        evolucion_stats = cursor.fetchone()

        # Promedios de estado emocional y nivel de energía de los pacientes
        cursor.execute(
            """
            SELECT 
                AVG(e.estadoEmocional) as estado_emocional_promedio,
                AVG(e.nivelEnergia) as nivel_energia_promedio,
                COUNT(e.idEvolucion) as total_registros
            FROM EvolucionPaciente e
            JOIN Citas c ON c.idPaciente = e.idPaciente
            WHERE c.idProfesional = %s 
              AND c.estado != 'Cancelada'
              AND e.fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """,
            (professional_id,),
        )
        emocion_stats = cursor.fetchone()

        # Alertas de citas por confirmar (hoy y próximos 3 días)
        cursor.execute(
            """
            SELECT 
                COUNT(CASE WHEN c.estado = 'Pendiente' AND c.fecha = CURDATE() THEN 1 END) as citas_por_confirmar_hoy,
                COUNT(CASE WHEN c.estado = 'Pendiente' AND c.fecha > CURDATE() AND c.fecha <= DATE_ADD(CURDATE(), INTERVAL 3 DAY) THEN 1 END) as citas_por_confirmar_proximas
            FROM Citas c
            WHERE c.idProfesional = %s
            """,
            (professional_id,),
        )
        alertas_citas = cursor.fetchone()

        # Alertas de reportes pendientes
        cursor.execute(
            """
            SELECT COUNT(*) as reportes_pendientes
            FROM Reportes
            WHERE idProfesional = %s AND estado = 'Pendiente' AND COALESCE(eliminado, 0) = 0
            """,
            (professional_id,),
        )
        alertas_reportes = cursor.fetchone()

    # Calcula pacientes con citas pero sin evolución reciente (más de 14 días)
    pacientes_sin_evolucion = 0
    if evolucion_stats and evolucion_stats["pacientes_con_citas"]:
        pacientes_sin_evolucion = (evolucion_stats["pacientes_con_citas"] or 0) - (evolucion_stats["pacientes_con_evolucion_reciente"] or 0)

    # Construye lista de alertas con tipo, icono y acción sugerida
    alertas = []
    if alertas_citas and alertas_citas["citas_por_confirmar_hoy"]:
        alertas.append({
            "tipo": "warning",
            "icono": "fa-clock",
            "titulo": "Citas por confirmar hoy",
            "mensaje": f"{alertas_citas['citas_por_confirmar_hoy']} cita(s) pendiente(s) de confirmación",
            "accion": "ver_agenda"
        })
    if alertas_citas and alertas_citas["citas_por_confirmar_proximas"]:
        alertas.append({
            "tipo": "info",
            "icono": "fa-calendar-day",
            "titulo": "Citas por confirmar (próx. 3 días)",
            "mensaje": f"{alertas_citas['citas_por_confirmar_proximas']} cita(s) pendiente(s)",
            "accion": "ver_agenda"
        })
    if alertas_reportes and alertas_reportes["reportes_pendientes"]:
        alertas.append({
            "tipo": "warning",
            "icono": "fa-file-text",
            "titulo": "Reportes pendientes",
            "mensaje": f"{alertas_reportes['reportes_pendientes']} reporte(s) por completar",
            "accion": "ver_reportes"
        })
    if pacientes_sin_evolucion > 0:
        alertas.append({
            "tipo": "info",
            "icono": "fa-heart-pulse",
            "titulo": "Pacientes sin evolución reciente",
            "mensaje": f"{pacientes_sin_evolucion} paciente(s) sin registro en 14 días",
            "accion": "ver_pacientes"
        })

    return {
        "pacientes_activos": stats["pacientes_activos"] or 0,
        "citas_hoy": stats["citas_hoy"] or 0,
        "citas_pendientes": stats["citas_pendientes"] or 0,
        "actividades": actividades,
        "proximas_citas": proximas_citas,
        "reportes": {
            "total": reportes_stats["total_reportes"] or 0,
            "completados": reportes_stats["completados"] or 0,
            "pendientes": reportes_stats["pendientes"] or 0,
        },
        "evolucion": {
            "pacientes_con_citas": evolucion_stats["pacientes_con_citas"] or 0,
            "pacientes_con_evolucion_reciente": evolucion_stats["pacientes_con_evolucion_reciente"] or 0,
            "pacientes_sin_evolucion": pacientes_sin_evolucion,
            "estado_emocional_promedio": round(emocion_stats["estado_emocional_promedio"], 1) if emocion_stats and emocion_stats["estado_emocional_promedio"] else None,
            "nivel_energia_promedio": round(emocion_stats["nivel_energia_promedio"], 1) if emocion_stats and emocion_stats["nivel_energia_promedio"] else None,
            "total_registros": emocion_stats["total_registros"] or 0,
        },
        "alertas": alertas,
    }


def list_professional_patients(professional_id):
    # Lista todos los pacientes (con su último diagnóstico de este profesional)
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT DISTINCT r.idUsuario, r.nombre, r.fotoPerfil, p.edad, p.genero,
                   COALESCE(p.numeroTelefonico, r.email) as contacto,
                   (SELECT diagnostico FROM PacientesProfesional
                    WHERE idPaciente = r.idUsuario AND idProfesional = %s
                    ORDER BY fechaDiagnostico DESC LIMIT 1) as ultimoDiagnostico
            FROM Register r
            JOIN PerfilPaciente p ON r.idUsuario = p.idPaciente
            WHERE r.rol = 'paciente'
            ORDER BY r.nombre
            """,
            (professional_id,),
        )
        return cursor.fetchall()


def list_patients_for_chat():
    """Pacientes registrados disponibles para mensajeria directa."""
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT r.idUsuario, r.nombre, r.fotoPerfil, p.edad, p.genero,
                   COALESCE(p.numeroTelefonico, r.email) as contacto
            FROM Register r
            LEFT JOIN PerfilPaciente p ON r.idUsuario = p.idPaciente
            WHERE r.rol = 'paciente'
            ORDER BY r.nombre
            """
        )
        return cursor.fetchall()


def save_diagnosis(professional_id, data):
    # Guarda o actualiza el diagnóstico de un paciente (con UPSERT para evitar duplicados)
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO PacientesProfesional (idProfesional, idPaciente, sintomas, diagnostico, tratamiento, fechaDiagnostico)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                sintomas = VALUES(sintomas),
                diagnostico = VALUES(diagnostico),
                tratamiento = VALUES(tratamiento),
                fechaDiagnostico = VALUES(fechaDiagnostico)
            """,
            (
                professional_id,
                data.get("idPaciente"),
                data.get("sintomas"),
                data.get("diagnostico"),
                data.get("tratamiento"),
                data.get("fecha_diagnostico"),
            ),
        )
        conn.commit()


def get_diagnosis_history(professional_id):
    # Obtiene el historial de diagnósticos realizados por un profesional
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT r.nombre as paciente,
                   pp.fechaDiagnostico as fechaRaw,
                   pp.sintomas,
                   pp.diagnostico,
                   pp.tratamiento
            FROM PacientesProfesional pp
            JOIN Register r ON pp.idPaciente = r.idUsuario
            WHERE pp.idProfesional = %s AND pp.diagnostico IS NOT NULL AND pp.diagnostico != ''
            ORDER BY pp.fechaDiagnostico DESC
            """,
            (professional_id,),
        )
        return cursor.fetchall()


def get_report_overview(professional_id):
    # Obtiene un resumen de reportes del profesional: estadísticas + lista + pacientes disponibles
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT COUNT(*) as total,
                   SUM(estado = 'Completado') as completados,
                   SUM(estado = 'Pendiente') as pendientes
            FROM Reportes WHERE idProfesional = %s AND COALESCE(eliminado, 0) = 0
            """,
            (professional_id,),
        )
        stats = cursor.fetchone()
        cursor.execute(
            """
            SELECT rep.idReporte, rep.idPaciente, rep.tipoReporte, rep.estado,
                   DATE_FORMAT(rep.fechaInicio, '%d/%m/%Y') as fechaInicio,
                   DATE_FORMAT(rep.fechaFin, '%d/%m/%Y') as fechaFin,
                   rep.sintomas, rep.diagnostico, rep.tratamiento,
                   COALESCE(r.nombre, 'General') as paciente
            FROM Reportes rep
            LEFT JOIN Register r ON rep.idPaciente = r.idUsuario
            WHERE rep.idProfesional = %s AND COALESCE(eliminado, 0) = 0
            ORDER BY rep.fechaInicio DESC
            """,
            (professional_id,),
        )
        reportes = cursor.fetchall()
        cursor.execute(
            """
            SELECT DISTINCT r.idUsuario, r.nombre
            FROM Register r
            JOIN Citas c ON c.idPaciente = r.idUsuario
            WHERE c.idProfesional = %s
              AND r.rol = 'paciente'
              AND LOWER(COALESCE(c.estado, '')) != 'cancelada'
            ORDER BY r.nombre
            """,
            (professional_id,),
        )
        pacientes = cursor.fetchall()
        return {"stats": stats, "reportes": reportes, "pacientes": pacientes}


def create_report(professional_id, data):
    # Crea un nuevo reporte clínico con estado "Completado" por defecto
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO Reportes (
                idProfesional, idPaciente, tipoReporte, fechaInicio, fechaFin,
                sintomas, diagnostico, tratamiento, estado
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Completado')
            """,
            (
                professional_id,
                data.get("idPaciente") or None,
                data.get("tipoReporte"),
                data.get("fechaInicio") or None,
                data.get("fechaFin") or None,
                data.get("sintomas"),
                data.get("diagnostico"),
                data.get("tratamiento"),
            ),
        )
        conn.commit()


def get_latest_patient_diagnosis(professional_id, patient_id):
    # Obtiene el diagnóstico más reciente de un paciente por parte de un profesional
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT sintomas, diagnostico, tratamiento
            FROM PacientesProfesional
            WHERE idProfesional = %s
              AND idPaciente = %s
            ORDER BY fechaDiagnostico DESC
            LIMIT 1
            """,
            (professional_id, patient_id),
        )
        return cursor.fetchone()


def update_report(professional_id, data):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            UPDATE Reportes SET tipoReporte = %s, estado = %s
            WHERE idReporte = %s AND idProfesional = %s
            """,
            (data.get("tipoReporte"), data.get("estado"), data.get("idReporte"), professional_id),
        )
        conn.commit()


def delete_report(professional_id, report_id):
    # Eliminación lógica de un reporte
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            UPDATE Reportes SET eliminado = 1
            WHERE idReporte = %s AND idProfesional = %s
            """,
            (report_id, professional_id),
        )
        conn.commit()


def get_deleted_reports(professional_id):
    # Obtiene los reportes eliminados (para posible recuperación)
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT rep.idReporte, rep.idPaciente, rep.tipoReporte, rep.estado,
                   DATE_FORMAT(rep.fechaInicio, '%d/%m/%Y') as fechaInicio,
                   DATE_FORMAT(rep.fechaFin, '%d/%m/%Y') as fechaFin,
                   COALESCE(r.nombre, 'General') as paciente
            FROM Reportes rep
            LEFT JOIN Register r ON rep.idPaciente = r.idUsuario
            WHERE rep.idProfesional = %s AND rep.eliminado = 1
            ORDER BY rep.fechaInicio DESC
            """,
            (professional_id,),
        )
        return cursor.fetchall()


def get_all_patient_evolution(professional_id):
    # Obtiene todas las evoluciones de pacientes (sin filtrar por profesional - todos los pacientes)
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT e.idEvolucion,
                   e.idPaciente,
                   e.estadoEmocional,
                   e.nivelEnergia,
                   e.notasPersonales,
                   DATE_FORMAT(e.fecha, '%d/%m/%Y') as fecha,
                   e.fecha as fechaRaw,
                   r.nombre as paciente
            FROM EvolucionPaciente e
            JOIN Register r ON e.idPaciente = r.idUsuario
            WHERE r.rol = 'paciente'
            ORDER BY e.fecha DESC
            """,
        )
        return cursor.fetchall()


def professional_has_patient(professional_id, patient_id):
    """Verifica si un profesional tiene una relación activa con un paciente vía Citas."""
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute(
            """
            SELECT COUNT(1)
            FROM Citas
            WHERE idProfesional = %s AND idPaciente = %s AND LOWER(COALESCE(estado, '')) != 'cancelada'
            LIMIT 1
            """,
            (professional_id, patient_id),
        )
        row = cursor.fetchone()
        return row and row[0] > 0
