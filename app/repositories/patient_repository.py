from app.utils.db import db_cursor


def update_profile_photo(filename, user_id):
    with db_cursor() as (conn, cursor):
        cursor.execute("UPDATE Register SET fotoPerfil = %s WHERE idUsuario = %s", (filename, user_id))
        conn.commit()


def save_chatbot_survey(user_id, data):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO EncuestaChatbot (idPaciente, utilidad, claridad, recomendaria, comentario)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                user_id,
                data.get("utilidad"),
                data.get("claridad"),
                data.get("recomendaria"),
                data.get("comentario"),
            ),
        )
        conn.commit()


def get_patient_profile(user_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT r.nombre, r.email, r.fotoPerfil, r.fechaRegistro,
                   p.edad, p.genero, p.numeroTelefonico, p.consentimiento_chatbot
            FROM Register r
            LEFT JOIN PerfilPaciente p ON r.idUsuario = p.idPaciente
            WHERE r.idUsuario = %s
            """,
            (user_id,),
        )
        return cursor.fetchone()


def update_patient_profile(data):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            UPDATE PerfilPaciente
            SET edad = %s, genero = %s, numeroTelefonico = %s
            WHERE idPaciente = %s
            """,
            (data.get("edad"), data.get("genero"), data.get("numeroTelefonico"), data.get("idUsuario")),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO PerfilPaciente (idPaciente, edad, genero, numeroTelefonico, consentimiento_chatbot) VALUES (%s, %s, %s, %s, 0)",
                (data.get("idUsuario"), data.get("edad"), data.get("genero"), data.get("numeroTelefonico")),
            )
        conn.commit()


def get_chatbot_consent(user_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT consentimiento_chatbot FROM PerfilPaciente WHERE idPaciente = %s",
            (user_id,),
        )
        row = cursor.fetchone()
        return bool(row["consentimiento_chatbot"]) if row else False


def update_chatbot_consent(user_id, consent):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE PerfilPaciente SET consentimiento_chatbot = %s WHERE idPaciente = %s",
            (1 if consent else 0, user_id),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO PerfilPaciente (idPaciente, consentimiento_chatbot) VALUES (%s, %s)",
                (user_id, 1 if consent else 0),
            )
        conn.commit()


def create_patient_evolution(user_id, data):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO EvolucionPaciente (idPaciente, estadoEmocional, nivelEnergia, notasPersonales)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, data.get("estadoEmocional"), data.get("nivelEnergia"), data.get("notasPersonales")),
        )
        conn.commit()


def get_patient_evolution_history(user_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT estadoEmocional, nivelEnergia, notasPersonales,
                   DATE_FORMAT(fecha, '%d/%m/%Y') as fecha,
                   fecha as fechaRaw
            FROM EvolucionPaciente
            WHERE idPaciente = %s
            ORDER BY fecha DESC
            """,
            (user_id,),
        )
        return cursor.fetchall()


def list_patients(page=1, limit=20):
    offset = (page - 1) * limit
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT idUsuario, nombre, email, fotoPerfil FROM Register
            WHERE rol = 'paciente'
            ORDER BY nombre
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        return cursor.fetchall()


def list_professionals():
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT idUsuario, nombre FROM Register
            WHERE rol = 'profesional'
            ORDER BY nombre
            """
        )
        return cursor.fetchall()
