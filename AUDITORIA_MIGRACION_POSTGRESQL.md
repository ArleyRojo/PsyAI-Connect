# Auditoría de migración MySQL → PostgreSQL — PsyAI Connect

**Estado:** Fase 1 — solo auditoría, sin modificaciones de código.
**Objetivo:** listar cada uso de SQL crudo y sintaxis MySQL específica antes de iniciar la conversión.

---

## 1. Archivos revisados

- `config/settings/{base,dev,prod,test,_local_browser}.py`
- `requirements.txt`
- `.env.example` / `.env`
- `install/{Dockerfile,docker-compose.yml,docker-compose.prod.yml,entrypoint.sh,install.py}`
- `psyai_connect.sql` (dump phpMyAdmin / MySQL)
- `apps/*/repositories.py` (8 apps)
- `apps/authentication/{models,backends,adapters}.py`
- `apps/core/views.py`

---

## 2. Uso de SQL crudo (cursor.execute / connection.cursor)

| # | Archivo:línea | Función / contexto | Consulta (resumen) | Sintaxis MySQL a cambiar | Riesgo |
|---|---------------|--------------------|--------------------|--------------------------|--------|
| 1 | `apps/admin_panel/repositories.py:86` | `AdminRepository.get_stats()` | `SELECT COUNT(DISTINCT SUBSTRING_INDEX(detalle, 'IP: ', -1)) FROM Logs WHERE ... LIKE 'Rate limit%%' ... AND fecha >= NOW() - INTERVAL 1 DAY` | `SUBSTRING_INDEX(...)`, `LIKE 'Rate limit%%'` (escape de `%`), `NOW() - INTERVAL 1 DAY` (sin comillas en el intervalo) | Medio |
| 2 | `apps/admin_panel/repositories.py:150` | `AdminRepository.list_users()` | `SELECT ... COALESCE(r.activo,1) ... (subconsulta) ... CASE r.rol ... LIMIT %s OFFSET %s` | Ninguna crítica (COALESCE, LIMIT/OFFSET y CASE son estándar) | Bajo |
| 3 | `apps/admin_panel/repositories.py:177` | `AdminRepository.get_user()` | `SELECT ... COALESCE(activo,1) ... FROM Register WHERE idUsuario = %s` | Ninguna crítica | Bajo |
| 4 | `apps/admin_panel/repositories.py:308` | `AdminRepository.get_notifications_feed()` | 3 consultas con `UNION ALL`: `CONCAT(...)`, `COALESCE(...)`, `CURDATE()`, `LIMIT`, `ORDER BY` | `CURDATE()` (no existe en PostgreSQL; usar `CURRENT_DATE`) | Medio |
| 5 | `apps/core/views.py:77-78` | `HealthCheckView.get()` | `cursor.execute("SELECT 1")` | Ninguna (vendor-neutral) | Nulo |
| 6 | `apps/authentication/migrations/0005_map_password_to_contrasena.py:9,30` | Data migration `align_register_columns` | Introspección de tablas/columnas + `UPDATE ... SET contrasena = password` y `CHANGE COLUMN` / `RENAME COLUMN` | Ya tiene rama `if connection.vendor == "mysql"` + `else` (RENAME COLUMN). Revisar que el `else` funcione en Postgres. | Bajo (ya es consciente del vendor) |

**Total de consultas crudas a convertir:** 4 (todas en `apps/admin_panel/repositories.py`). La de `views.py` es portátil y la migración `0005` ya es bivalente.

> Nota: no se usa `Model.objects.raw()`, `.extra()`, ni placeholders `?` (todos usan `%s` con lista de parámetros, estilo Django, apto para PostgreSQL).

---

## 3. Sintaxis MySQL específica detectada

### En el dump `psyai_connect.sql` (legacy, NO se usará en PostgreSQL)
- Backticks: `` `tabla` ``, `` `columna` ``.
- `ENGINE=InnoDB`, `DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`.
- `AUTO_INCREMENT`, `enum(...)`, `tinyint(1)` como booleano.
- `DELIMITER $$`, procedimientos almacenados (`CREATE PROCEDURE`), triggers (`CREATE TRIGGER`), vistas con `CREATE ALGORITHM=UNDEFINED ... SQL SECURITY DEFINER VIEW`.
- `DATE_FORMAT(...)`, `CONCAT(...)`, `COALESCE(...)`, `NOW()`, `CURDATE()`.
- `LOCK TABLES ... WRITE` / `UNLOCK TABLES`, `/*!40101 ... */` comentarios condicionales.

### En código Python activo
- `NOW() - INTERVAL 1 DAY` (Phase 2/3) → Postgres: `now() - INTERVAL '1 day'`.
- `CURDATE()` → Postgres: `CURRENT_DATE`.
- `SUBSTRING_INDEX(str, delim, -1)` → Postgres: no existe; usar `split_part` / `regexp_replace`.
- `LIKE 'Rate limit%%'` → el `%%` es escape de `%` literal en MySQL; en Postgres `LIKE 'Rate limit%'` basta (o usar `__icontains`/`icontains` del ORM).
- Backticks: ausentes en Python (identificados sin comillas).

---

## 4. Comparaciones de texto case-insensitive (emails y búsquedas)

MySQL con collation `utf8mb4_unicode_ci` compara emails y texto sin distinguir mayúsculas/minúsculas. PostgreSQL distingue mayúsculas/minúsculas por defecto. Consultas sobre `Register.email` y `IntentosFallidos.email` que usan `email=X` son **case-sensitive** en Postgres y deben cambiarse a `__iexact` (o `ILIKE`):

| Archivo:línea | Consulta | Acción |
|---------------|----------|--------|
| `apps/authentication/backends.py:10` | `Register.objects.get(email=email)` (backend de login) | `__iexact` |
| `apps/authentication/adapters.py:20` | `Register.objects.get(email=email)` (adapter social Google) | `__iexact` |
| `apps/authentication/repositories.py:19` | `filter(email=email).exists()` | `__iexact` |
| `apps/authentication/repositories.py:33` | `filter(email=email, estadoCuenta="Activa")` | `__iexact` |
| `apps/authentication/repositories.py:47` | `filter(email=email).first()` | `__iexact` |
| `apps/admin_panel/repositories.py:201` | `filter(email=email).exists()` | `__iexact` |
| `apps/admin_panel/repositories.py:741` | `Register.objects.get(email=email_individual)` | `__iexact` |
| `apps/authentication/repositories.py:124..209` | `IntentosFallidos.objects.filter(email=email/key)` (6 usos) | `__iexact` para no fragmentar contadores por mayúsculas |

Búsquedas por nombre/profesional en facturación (`nombre__icontains`) ya usan `icontains`, que en Postgres es case-insensitive: OK.

---

## 5. Campos y tipos

| Campo / tipo | MySQL | PostgreSQL (Django backend) | Acción |
|--------------|-------|-----------------------------|--------|
| `AutoField` / `BigAutoField` (`idUsuario`, `idCita`, etc.) | `AUTO_INCREMENT` | `SERIAL` / `IDENTITY` | Ninguna (Django lo gestiona) |
| `BooleanField` (`activo`, `email_verificado`, `leido`, `revocado`, `consentimientoDatos`, `eliminado`) | `tinyint(1)` | `boolean` | Ninguna |
| `CharField`/`TextField` con `choices` (`enum`) | `enum('..','..')` | `varchar` + CHECK (Django) | Ninguna |
| `DateTimeField` | `datetime` / `timestamp` | `timestamp with time zone` (USE_TZ=True) | Revisar zona horaria (`America/Bogota`) |
| `JSONField` (socialaccount `extra_data`, `settings`) | `json` | `jsonb` | Django lo gestiona nativo |
| `DecimalField` (`monto`, `precioUnitario`) | `decimal(10,2)` | `numeric` | Ninguna |

---

## 6. Resumen y riesgo general

- **Consultas crudas a convertir:** 4 (medio riesgo: `get_stats`, `get_notifications_feed`; bajo: `list_users`, `get_user`).
- **Consultas ORM con email case-sensitive a ajustar:** ~14 (bajo riesgo, cambio mecánico a `__iexact`).
- **Sintaxis MySQL en dump SQL:** solo legacy; no se aplica en PostgreSQL (se genera esquema con `migrate`).
- **Riesgo general:** **Medio-Bajo**. No hay lógica de negocio en SQL crudo; la mayor parte del acceso a datos ya usa el ORM de Django, que es portable. Los únicos puntos críticos son las 4 consultas de `admin_panel/repositories.py` y la normalización case-insensitive de emails.

> Decisión pendiente (confirmar con el usuario si es necesario): las vistas (`VIEW`), procedimientos almacenados y triggers del dump `psyai_connect.sql` no se replican en PostgreSQL; su funcionalidad (notificaciones tras cita, auditoría de reactivación, etc.) ya está implementada en capa Services/Repositories de Django, por lo que no se considera necesario reimplementarlas en la BD.

---

## 7. Siguiente paso

Continuar con **FASE 2 – Infraestructura** (requirements, settings, docker-compose, entrypoint, .env.example).
