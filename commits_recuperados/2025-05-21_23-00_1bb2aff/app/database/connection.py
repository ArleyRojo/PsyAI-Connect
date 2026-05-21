import os
import logging
from mysql.connector import pooling, Error

logger = logging.getLogger(__name__)

_pool = None


def init_pool(app):
    """Inicializa el pool de conexiones MySQL. Crea la BD si no existe."""
    global _pool
    if _pool is not None:
        return _pool

    cfg = app.config
    pool_cfg = dict(
        pool_name=os.getenv("DB_POOL_NAME", "psyai_pool"),
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        pool_reset_session=os.getenv("DB_POOL_RESET_SESSION", "true").lower() == "true",
        host=cfg.get("DB_HOST", "localhost"),
        port=cfg.get("DB_PORT", 3306),
        user=cfg.get("DB_USER", "root"),
        password=cfg.get("DB_PASSWORD") or None,
        database=cfg.get("DB_NAME", "psyai_connect"),
        autocommit=True,
        charset="utf8mb4",
        use_pure=True,   # ← CAMBIADO: usa implementación Python pura (sin extensión C)
    )

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
                f"Base de datos '{pool_cfg['database']}' no existe. Creándola..."
            )
            try:
                _create_database(pool_cfg)
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


def _create_database(pool_cfg):
    """Crea la base de datos conectando sin especificar database."""
    import mysql.connector

    tmp = mysql.connector.connect(
        host=pool_cfg["host"],
        port=pool_cfg["port"],
        user=pool_cfg["user"],
        password=pool_cfg["password"],
        autocommit=True,
        use_pure=True,   # ← CAMBIADO también aquí
    )
    cur = tmp.cursor()
    db = pool_cfg["database"].replace("`", "``")
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
        # Lazy-init (poco común, pero seguro)
        from flask import current_app
        init_pool(current_app._get_current_object())
    try:
        return _pool.get_connection()
    except Error as e:
        logger.error(f"Error obteniendo conexión del pool: {e}")
        raise