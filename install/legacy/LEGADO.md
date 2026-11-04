# Legacy — Dump MySQL original (`psyai_connect.sql`)

Este archivo es el dump original de **MySQL 8 / MariaDB** (phpMyAdmin) generado antes de la migración. **NO se usa en PostgreSQL.**

## Por qué no se aplica en PostgreSQL

- Contiene DDL específica de MySQL: `` `backticks` ``, `ENGINE=InnoDB`, `DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`, `AUTO_INCREMENT`, `ENUM(...)`, `TINYINT(1)` como booleano.
- Contiene procedimientos almacenados (`CREATE PROCEDURE ... DELIMITER $$`), triggers y vistas con `SQL SECURITY DEFINER`, que son propias de MySQL/MariaDB.
- Sus datos de prueba (usuarios `admin@psyai.com`, `profesional@psyai.com`, `paciente@psyai.com`) se gestionan ahora desde el entrypoint (dev) y desde los tests.

## Esquema actual

El esquema de PostgreSQL se genera exclusivamente con las migraciones de Django:

```bash
python manage.py makemigrations --check   # verifica que no haya modelos sin migrar
python manage.py migrate                  # crea el esquema sobre PostgreSQL vacío
```

Tras una carga masiva de datos (pgloader), resincronizar las secuencias:

```bash
python manage.py sqlsequencereset authentication patients professionals scheduling chatbot documents billing admin_panel core \
  | psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME
```

## Migración de datos (dump → PostgreSQL)

Para migrar los datos del dump MySQL a PostgreSQL se recomienda **pgloader** (ver `install/pgloader/psyai_connect.load`) o un script personalizado. Los hashes de contraseña (argon2 / bcrypt / pbkdf2) son cadenas portátiles y se conservan al cambiar de motor.
