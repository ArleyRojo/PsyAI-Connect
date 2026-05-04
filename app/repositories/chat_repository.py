from app.utils.db import db_cursor


def save_conversation(patient_id, mensaje_usuario, respuesta_bot, nivel_emocional, palabras_riesgo):
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


def get_history(patient_id, limit=50, today_only=False):
    date_filter = "AND DATE(fecha) = CURDATE()" if today_only else ""
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            f"""
            SELECT 
                mensajeUsuario,
                respuestaChatbot,
                DATE_FORMAT(fecha, '%%d/%%m/%%Y %%H:%%i') as fecha
            FROM conversacioneschatbot
            WHERE idPaciente = %s
            {date_filter}
            ORDER BY fecha DESC
            LIMIT %s
            """,
            (patient_id, limit),
        )
        rows = list(reversed(cursor.fetchall()))
        
        historial = []
        for row in rows:
            if row.get('mensajeUsuario'):
                historial.append({'tipo': 'usuario', 'mensaje': row['mensajeUsuario']})
            if row.get('respuestaChatbot'):
                historial.append({'tipo': 'bot', 'mensaje': row['respuestaChatbot']})
        
        return historial


def delete_history(patient_id):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "DELETE FROM conversacioneschatbot WHERE idPaciente = %s",
            (patient_id,)
        )
        conn.commit()
