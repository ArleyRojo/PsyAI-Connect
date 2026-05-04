from app.utils.db import db_cursor


def get_professional_profile(user_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT r.nombre, r.email, r.fotoPerfil, r.fechaRegistro,
                   p.especialidad, p.licencia, p.experiencia, p.estado
            FROM Register r
            LEFT JOIN PerfilProfesional p ON r.idUsuario = p.idProfesional
            WHERE r.idUsuario = %s
            """,
            (user_id,),
        )
        return cursor.fetchone()


def update_professional_profile(data):
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
    with db_cursor(dictionary=True) as (_, cursor):
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

        cursor.execute(
            """
            SELECT r.nombre as paciente, c.fecha, c.hora, c.tipoCita, c.estado
            FROM Citas c
            JOIN Register r ON c.idPaciente = r.idUsuario
            WHERE c.idProfesional = %s AND c.estado != 'Cancelada'
            ORDER BY c.fecha DESC, c.hora DESC LIMIT 3
            """,
            (professional_id,),
        )
        actividades = cursor.fetchall()

    return {
        "pacientes_activos": stats["pacientes_activos"] or 0,
        "citas_hoy": stats["citas_hoy"] or 0,
        "citas_pendientes": stats["citas_pendientes"] or 0,
        "actividades": actividades,
    }


def list_professional_patients(professional_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT DISTINCT r.idUsuario, r.nombre, p.edad, p.genero,
                   COALESCE(p.numeroTelefonico, r.email) as contacto,
                   (SELECT diagnostico FROM Reportes
                    WHERE idPaciente = r.idUsuario
                    ORDER BY fechaInicio DESC LIMIT 1) as ultimoDiagnostico
            FROM Register r
            JOIN PerfilPaciente p ON r.idUsuario = p.idPaciente
            JOIN Citas c ON c.idPaciente = r.idUsuario
            WHERE c.idProfesional = %s AND r.rol = 'paciente'
            ORDER BY r.nombre
            """,
            (professional_id,),
        )
        return cursor.fetchall()


def save_diagnosis(professional_id, data):
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
            SELECT rep.idReporte, rep.tipoReporte, rep.estado,
                   DATE_FORMAT(rep.fechaInicio, '%d/%m/%Y') as fechaInicio,
                   DATE_FORMAT(rep.fechaFin, '%d/%m/%Y') as fechaFin,
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
            WHERE r.rol = 'paciente'
            ORDER BY r.nombre
            """
        )
        pacientes = cursor.fetchall()
        return {"stats": stats, "reportes": reportes, "pacientes": pacientes}


def create_report(professional_id, data):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO Reportes (idProfesional, idPaciente, tipoReporte, fechaInicio, fechaFin, estado)
            VALUES (%s, %s, %s, %s, %s, 'Completado')
            """,
            (
                professional_id,
                data.get("idPaciente") or None,
                data.get("tipoReporte"),
                data.get("fechaInicio") or None,
                data.get("fechaFin") or None,
            ),
        )
        conn.commit()


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
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT rep.idReporte, rep.tipoReporte, rep.estado,
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
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT DISTINCT e.estadoEmocional, e.nivelEnergia, e.notasPersonales,
                   DATE_FORMAT(e.fecha, '%d/%m/%Y') as fecha,
                   e.fecha as fechaRaw,
                   r.nombre as paciente
            FROM EvolucionPaciente e
            JOIN Register r ON e.idPaciente = r.idUsuario
            JOIN Citas c ON c.idPaciente = e.idPaciente AND c.idProfesional = %s
            WHERE c.idProfesional = %s
            ORDER BY e.fecha DESC
            """,
            (professional_id, professional_id),
        )
        return cursor.fetchall()