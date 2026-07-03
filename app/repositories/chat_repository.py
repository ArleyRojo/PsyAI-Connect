# ============================================================
# ARCHIVO: repositories/chat_repository.py
# ============================================================

from app.utils.db import db_cursor


def save_conversation(patient_id, mensaje_usuario, respuesta_bot, nivel_emocional, palabras_riesgo):
    # Guarda una interacción del chatbot en la base de datos
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO conversacioneschatbot
              (idPaciente, mensajeUsuario, respuestaChatbot, nivelEmocionalDetectado, palabrasRiesgoDetectadas)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (patient_id, mensaje_usuario, respuesta_bot, nivel_emocional, palabras_riesgo)
        )
        conn.commit()


def get_history(patient_id, limit=40, today_only=False):
    date_filter = "AND DATE(fecha) = CURDATE()" if today_only else ""
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            f"""
            SELECT 
                mensajeUsuario,
                respuestaChatbot,
                DATE_FORMAT(fecha, '%%d/%%m/%%Y %%H:%%i') as fecha_formateada
            FROM conversacioneschatbot
            WHERE idPaciente = %s
            {date_filter}
            -- Cambio: ordenar por el campo datetime real, no por el alias formateado.
            ORDER BY conversacioneschatbot.fecha DESC
            LIMIT %s
            """,
            (patient_id, limit),
        )
        # Invierte el orden para tenerlos cronológicamente ascendentes
        rows = list(reversed(cursor.fetchall()))
        
        # Convierte las filas a una lista plana de mensajes alternados usuario/bot
        historial = []
        for row in rows:
            if row.get('mensajeUsuario'):
                historial.append({'tipo': 'usuario', 'mensaje': row['mensajeUsuario']})
            if row.get('respuestaChatbot'):
                historial.append({'tipo': 'bot', 'mensaje': row['respuestaChatbot']})
        
        return historial


def delete_history(patient_id):
    # Elimina todo el historial de conversaciones del chatbot de un paciente
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "DELETE FROM conversacioneschatbot WHERE idPaciente = %s",
            (patient_id,)
        )
        conn.commit()


def count_today_messages(patient_id):
    """Retorna el numero de mensajes enviados por el paciente hoy."""
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT COUNT(*) as total
            FROM conversacioneschatbot
            WHERE idPaciente = %s AND DATE(fecha) = CURDATE()
            """,
            (patient_id,),
        )
        row = cursor.fetchone()
        return row["total"] if row else 0


def get_assigned_professionals(patient_id):
    """Retorna lista de idProfesional asignados a un paciente."""
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT idProfesional FROM PacientesProfesional WHERE idPaciente = %s",
            (patient_id,),
        )
        return [row["idProfesional"] for row in cursor.fetchall() if row.get("idProfesional")]


def get_all_professional_ids():
    """Retorna todos los idUsuario con rol profesional."""
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute("SELECT idUsuario FROM Register WHERE rol = 'profesional'")
        return [row["idUsuario"] for row in cursor.fetchall()]


def get_patient_name(patient_id):
    """Retorna el nombre de un paciente por su id."""
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT nombre FROM Register WHERE idUsuario = %s",
            (patient_id,),
        )
        row = cursor.fetchone()
        return row["nombre"] if row else None


def notificacion_reciente_existe(patient_name, tipo, horas=12):
    """True si ya existe una notificación de ese tipo sobre ese paciente en las últimas N horas."""
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT 1 FROM Notificaciones
            WHERE tipo = %s
              AND mensaje LIKE %s
              AND fecha >= NOW() - INTERVAL %s HOUR
            LIMIT 1
            """,
            (tipo, f"%{patient_name}%", horas),
        )
        return cursor.fetchone() is not None


def get_low_risk_counts_for_professional(professional_id, days=7):
    """Cuenta mensajes de riesgo bajo del chatbot por paciente en los últimos N días."""
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT c.idPaciente, COUNT(*) as total
            FROM conversacioneschatbot c
            JOIN Register r ON r.idUsuario = c.idPaciente AND r.rol = 'paciente'
            LEFT JOIN PacientesProfesional pp ON pp.idPaciente = c.idPaciente AND pp.idProfesional = %s
            LEFT JOIN Citas cit ON cit.idPaciente = c.idPaciente AND cit.idProfesional = %s
            WHERE c.nivelEmocionalDetectado = 'Bajo'
              AND c.fecha >= DATE_SUB(NOW(), INTERVAL %s DAY)
              AND (
                pp.idRegistro IS NOT NULL
                OR (cit.idCita IS NOT NULL AND LOWER(COALESCE(cit.estado, '')) != 'cancelada')
              )
            GROUP BY c.idPaciente
            """,
            (professional_id, professional_id, days),
        )
        return {str(row["idPaciente"]): row["total"] for row in cursor.fetchall()}
