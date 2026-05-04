from app.utils.db import db_cursor


CONFIG_COLUMNS = {
    "system_prompt": "system_prompt",
    "tone": "tone",
    "interaction_rules": "interaction_rules",
    "risk_terms": "risk_terms",
    "crisis_response": "crisis_response",
    "medium_terms": "medium_terms",
    "medium_response": "medium_response",
    "fallback_response": "fallback_response",
    "temperature": "temperature",
    "top_p": "top_p",
    "max_tokens": "max_tokens",
    "actualizado_por": "actualizado_por",
}


def _get_existing_columns(cursor):
    cursor.execute("SHOW COLUMNS FROM ChatbotConfig")
    columns = set()
    for row in cursor.fetchall():
        if isinstance(row, dict):
            columns.add(row.get("Field"))
        else:
            columns.add(row[0])
    return {column for column in columns if column}


def get_config():
    with db_cursor(dictionary=True) as (_, cursor):
        existing_columns = _get_existing_columns(cursor)
        select_columns = [
            column for column in (
                "id",
                "system_prompt",
                "tone",
                "interaction_rules",
                "risk_terms",
                "crisis_response",
                "medium_terms",
                "medium_response",
                "fallback_response",
                "temperature",
                "top_p",
                "max_tokens",
                "actualizado_por",
                "fecha_actualizacion",
            )
            if column in existing_columns
        ]

        if not select_columns:
            return None

        cursor.execute(
            f"""
            SELECT {', '.join(select_columns)}
            FROM ChatbotConfig
            WHERE id = 1
            """
        )
        return cursor.fetchone()


def save_config(data, admin_id):
    with db_cursor() as (conn, cursor):
        existing_columns = _get_existing_columns(cursor)
        columns = ["id"]
        values = [1]

        for data_key, column in CONFIG_COLUMNS.items():
            if column not in existing_columns:
                continue

            columns.append(column)
            values.append(admin_id if data_key == "actualizado_por" else data.get(data_key))

        if "fecha_actualizacion" in existing_columns:
            columns.append("fecha_actualizacion")

        placeholders = ["%s"] * len(values)
        if "fecha_actualizacion" in existing_columns:
            placeholders.append("NOW()")

        update_columns = [column for column in columns if column != "id"]
        update_assignments = [
            f"{column} = VALUES({column})"
            for column in update_columns
        ]

        if not update_assignments:
            update_assignments = ["id = VALUES(id)"]

        cursor.execute(
            f"""
            INSERT INTO ChatbotConfig ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON DUPLICATE KEY UPDATE
                {', '.join(update_assignments)}
            """,
            tuple(values),
        )
        conn.commit()
        return cursor.rowcount
