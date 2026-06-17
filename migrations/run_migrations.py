"""
Runner de migraciones SQL para PsyAI Connect.

Uso:
    python migrations/run_migrations.py

Lee y ejecuta los archivos .sql de este directorio en orden alfabético.
Lleva un registro de migraciones aplicadas en la tabla `_migrations`.
Usa las mismas variables de entorno que la app (.env):
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
"""

import os
import re
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("migrations")


def _get_db_config():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "root"),
        "database": os.getenv("DB_NAME", "psyai_connect"),
    }


def _connect():
    import mysql.connector

    cfg = _get_db_config()
    logger.info(
        "Conectando a %s:%s/%s como %s",
        cfg["host"], cfg["port"], cfg["database"], cfg["user"],
    )
    return mysql.connector.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        autocommit=True,
    )


def _ensure_tracking_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS _migrations (
            filename VARCHAR(255) PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            checksum VARCHAR(64) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def _file_checksum(path):
    import hashlib
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _get_applied(cursor):
    cursor.execute("SELECT filename, checksum FROM _migrations")
    return {row[0]: row[1] for row in cursor.fetchall()}


def _mark_applied(cursor, filename, checksum):
    cursor.execute(
        "INSERT INTO _migrations (filename, checksum) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE checksum = VALUES(checksum), applied_at = CURRENT_TIMESTAMP",
        (filename, checksum),
    )


def run_migrations():
    migrations_dir = Path(__file__).parent
    sql_files = sorted(migrations_dir.glob("*.sql"))

    if not sql_files:
        logger.info("No se encontraron archivos .sql en %s", migrations_dir)
        return

    conn = _connect()
    cursor = conn.cursor()
    _ensure_tracking_table(cursor)
    applied = _get_applied(cursor)

    ran_count = 0
    skip_count = 0
    error_count = 0

    for sql_file in sql_files:
        if sql_file.name == "_migrations.sql":
            continue

        chk = _file_checksum(sql_file)

        if sql_file.name in applied:
            if applied[sql_file.name] == chk:
                logger.info("[SKIP] %s — ya aplicada (checksum coincide)", sql_file.name)
                skip_count += 1
                continue
            else:
                logger.warning(
                    "[REAPLICAR] %s — checksum cambi\u00f3 (anterior: %s, nuevo: %s)",
                    sql_file.name, applied[sql_file.name][:12], chk[:12],
                )

        sql = sql_file.read_text(encoding="utf-8")

        statements = re.split(r";\s*$", sql, flags=re.MULTILINE)
        statements = [s.strip() for s in statements if s.strip()]

        try:
            for stmt in statements:
                if stmt.upper().startswith("--"):
                    continue
                cursor.execute(stmt)
            _mark_applied(cursor, sql_file.name, chk)
            logger.info("[OK] %s — ejecutada (%d sentencias)", sql_file.name, len(statements))
            ran_count += 1
        except Exception as e:
            logger.error("[FAIL] %s — %s", sql_file.name, e)
            error_count += 1

    cursor.close()
    conn.close()

    logger.info(
        "Resumen: %d ejecutadas, %d omitidas, %d errores",
        ran_count, skip_count, error_count,
    )
    if error_count:
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
