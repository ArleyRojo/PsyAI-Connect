# ============================================================
# ARCHIVO: database/connection.py
# ============================================================

# Importaciones para acceder a variables de entorno y al conector MySQL con pool de conexiones
import os
import logging
from mysql.connector import pooling, Error

logger = logging.getLogger(__name__)

_pool = None  # Variable global que almacena la única instancia del pool de conexiones


def init_pool(app):
    """Inicializa el pool de conexiones MySQL. Crea la BD si no existe."""
    global _pool
    if _pool is not None:
        return _pool  # Si ya está inicializado, retorna el pool existente (singleton)

    cfg = app.config

    use_pure = os.getenv("DB_USE_PURE", "true").lower() == "true"

    # Construye el diccionario de configuración para el pool de MySQL
    pool_cfg = dict(
        pool_name=os.getenv("DB_POOL_NAME", "psyai_pool"),
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        pool_reset_session=os.getenv("DB_POOL_RESET_SESSION", "true").lower() == "true",
        host=cfg.get("DB_HOST", "localhost"),
        port=cfg.get("DB_PORT", 3306),
        user=cfg.get("DB_USER", "root"),
        password=cfg.get("DB_PASSWORD") or None,
        database=cfg.get("DB_NAME", "psyai_connect"),
        autocommit=False,
        charset="utf8mb4",
        use_pure=use_pure,
    )

    # Si el pool es muy pequeño, advierte porque el SSE consume conexiones adicionales
    if pool_cfg["pool_size"] < 8:
        logger.warning(
            "DB_POOL_SIZE=%d es bajo para una app con SSE. "
            "Considera DB_POOL_SIZE=10 o m\u00e1s en producci\u00f3n.",
            pool_cfg["pool_size"],
        )

    if use_pure:
        logger.info("Pool MySQL usando driver Python puro (use_pure=True).")
    else:
        logger.info("Pool MySQL usando driver C nativo (use_pure=False, m\u00e1s r\u00e1pido).")

    try:
        _pool = pooling.MySQLConnectionPool(**pool_cfg)
        logger.info(
            f"Pool MySQL inicializado: {pool_cfg['host']}:{pool_cfg['port']}/{pool_cfg['database']} "
            f"(user={pool_cfg['user']}, pool_size={pool_cfg['pool_size']})"
        )
        return _pool
    except Error as e:
        # Caso: la base de datos no existe — intentar crearla
        if e.errno == 1049:
            logger.warning(
                f"Base de datos '{pool_cfg['database']}' no existe. Cre\u00e1ndola..."
            )
            try:
                _create_database(pool_cfg, use_pure)
                _pool = pooling.MySQLConnectionPool(**pool_cfg)
                logger.info(
                    f"Pool MySQL inicializado: {pool_cfg['host']}:{pool_cfg['port']}/{pool_cfg['database']}"
                )
                return _pool
            except Exception as ce:
                logger.error(f"Error creando base de datos: {ce}")
                raise
        # Otro error de conexión/autenticación
        logger.error(
            f"Error inicializando pool MySQL (errno={e.errno}): {e.msg}. "
            f"Verifica en .env: DB_HOST={pool_cfg['host']}, DB_PORT={pool_cfg['port']}, "
            f"DB_USER={pool_cfg['user']}, DB_NAME={pool_cfg['database']}"
        )
        raise


def _sanitize_db_name(name):
    """Permite solo caracteres seguros para nombres de BD: alfanuméricos y guión bajo."""
    import re
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "", name)
    if not sanitized:
        raise ValueError(f"El nombre de base de datos '{name}' no es v\u00e1lido despu\u00e9s de sanitizar.")
    return sanitized


def _create_database(pool_cfg, use_pure=True):
    """Crea la base de datos conectando sin especificar database."""
    import mysql.connector

    # Conecta al servidor MySQL sin seleccionar BD para poder ejecutar CREATE DATABASE
    tmp = mysql.connector.connect(
        host=pool_cfg["host"],
        port=pool_cfg["port"],
        user=pool_cfg["user"],
        password=pool_cfg["password"],
        autocommit=True,
        use_pure=use_pure,
    )
    cur = tmp.cursor()
    db = _sanitize_db_name(pool_cfg["database"])
    # Crea la BD con charset utf8mb4 para soporte completo de Unicode (emojis, caracteres especiales)
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.close()
    tmp.close()
    logger.info(f"Base de datos '{pool_cfg['database']}' creada o ya existente.")


def get_connection():
    """Retorna una conexión del pool (la crea si es necesario)."""
    global _pool
    if _pool is None:
        # Lazy-init (poco común, pero seguro): si nunca se llamó a init_pool, lo hace automáticamente
        from flask import current_app
        init_pool(current_app._get_current_object())
    try:
        conn = _pool.get_connection()
        try:
            # Verifica que la conexión esté activa; si no, intenta reconectar automáticamente
            conn.ping(reconnect=True, attempts=3, delay=1)
        except Error as pe:
            logger.warning(f"Conexi\u00f3n del pool inactiva o ca\u00edda ({pe}). Intentando obtener una nueva conexi\u00f3n...")
            try:
                conn.close()
            except Exception:
                pass
            conn = _pool.get_connection()
            conn.ping(reconnect=True, attempts=3, delay=1)
        return conn
    except Error as e:
        logger.error(f"Error obteniendo conexi\u00f3n del pool: {e}")
        raise
