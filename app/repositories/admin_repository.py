from flask import session
from app.utils.db import db_cursor
from app.utils.security import hash_password


def get_admin_name():
    return session.get("nombre", "Admin")


def registrar_log(cursor, modulo, accion, detalle, rol_anterior=None, rol_nuevo=None, usuario_afectado=None, administrador='Admin'):
    try:
        cursor.execute(
            """
            INSERT INTO Logs (administrador, modulo, accion, detalle, rol_anterior, rol_nuevo, usuario_afectado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (administrador, modulo, accion, detalle, rol_anterior, rol_nuevo, usuario_afectado),
        )
    except Exception:
        pass


def ensure_report_columns():
    with db_cursor() as (conn, cursor):
        for field in ("sintomas", "diagnostico", "tratamiento"):
            cursor.execute(f"SHOW COLUMNS FROM Reportes LIKE '{field}'")
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE Reportes ADD COLUMN {field} TEXT")
        try:
            cursor.execute("ALTER TABLE Logs ADD COLUMN rol_anterior VARCHAR(20) DEFAULT NULL")
            cursor.execute("ALTER TABLE Logs ADD COLUMN rol_nuevo VARCHAR(20) DEFAULT NULL")
            cursor.execute("ALTER TABLE Logs ADD COLUMN usuario_afectado VARCHAR(100) DEFAULT NULL")
        except Exception:
            pass
        try:
            cursor.execute("SHOW COLUMNS FROM Reportes LIKE 'eliminado'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE Reportes ADD COLUMN eliminado TINYINT(1) DEFAULT 0")
        except Exception:
            pass
        conn.commit()


def get_stats():
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute("SELECT COUNT(*) as total FROM Register WHERE rol != 'admin'")
        total = cursor.fetchone()["total"]
        cursor.execute(
            "SELECT COUNT(*) as activos FROM Register WHERE rol != 'admin' AND COALESCE(activo,1) = 1 AND estadoCuenta = 'Activa'"
        )
        activos = cursor.fetchone()["activos"]
        cursor.execute(
            "SELECT COUNT(*) as bloqueados FROM Register WHERE rol != 'admin' AND (activo = 0 OR estadoCuenta = 'Suspendida')"
        )
        bloqueados = cursor.fetchone()["bloqueados"]
        cursor.execute("SELECT COUNT(*) as notifs FROM Notificaciones")
        notifs = cursor.fetchone()["notifs"]
        cursor.execute("SELECT COUNT(*) as logs_hoy FROM Logs WHERE DATE(fecha) = CURDATE()")
        logs_hoy = cursor.fetchone()["logs_hoy"]
        cursor.execute(
            "SELECT accion, detalle, DATE_FORMAT(fecha,'%d/%m/%Y %H:%i') as fecha FROM Logs ORDER BY fecha DESC LIMIT 5"
        )
        actividad = cursor.fetchall()
    return {
        "total_usuarios": total,
        "usuarios_activos": activos,
        "cuentas_suspendidas": bloqueados,
        "notificaciones": notifs,
        "logs_hoy": logs_hoy,
        "actividad_reciente": actividad,
    }


def list_users(page=1, limit=20):
    offset = (page - 1) * limit
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT r.idUsuario, r.nombre, r.email, r.rol,
                   COALESCE(r.activo, 1) as activo,
                   r.estadoCuenta,
                   DATE_FORMAT(r.fechaRegistro, '%d/%m/%Y') as fechaRegistro,
                   (SELECT DATE_FORMAT(MAX(a.fecha),'%d/%m/%Y %H:%i')
                    FROM AuditoriaAccesos a WHERE a.idUsuario = r.idUsuario) as ultimoAcceso
            FROM Register r
            ORDER BY 
                CASE r.rol 
                    WHEN 'admin' THEN 1 
                    WHEN 'profesional' THEN 2 
                    WHEN 'paciente' THEN 3 
                END, r.fechaRegistro DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        return cursor.fetchall()


def get_user(user_id):
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT idUsuario, nombre, email, rol,
                   COALESCE(activo,1) as activo, estadoCuenta,
                   DATE_FORMAT(fechaRegistro,'%d/%m/%Y') as fechaRegistro
            FROM Register WHERE idUsuario = %s
            """,
            (user_id,),
        )
        return cursor.fetchone()


def create_user(data):
    password = data.get("contrasena") or "1234"
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO Register (nombre, email, contrasena, rol)
            VALUES (%s, %s, %s, %s)
            """,
            (data.get("nombre"), data.get("email"), hash_password(password), data.get("rol", "paciente")),
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
        if data.get("rol") == "paciente":
            cursor.execute("INSERT INTO PerfilPaciente (idPaciente) VALUES (%s)", (nuevo_id,))
        elif data.get("rol") == "profesional":
            cursor.execute("INSERT INTO PerfilProfesional (idProfesional) VALUES (%s)", (nuevo_id,))
        registrar_log(cursor, "usuarios", "Crear usuario", f"Usuario creado: {data.get('nombre')} - Rol: {data.get('rol')}", administrador=get_admin_name())
        conn.commit()


def update_user(data):
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            UPDATE Register SET nombre = %s, email = %s, estadoCuenta = %s
            WHERE idUsuario = %s
            """,
            (data.get("nombre"), data.get("email"), data.get("estado"), data.get("idUsuario")),
        )
        registrar_log(cursor, "usuarios", "Editar usuario", f"Usuario editado: {data.get('nombre')}", administrador=get_admin_name())
        conn.commit()


def delete_user(user_id):
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT nombre FROM Register WHERE idUsuario = %s", (user_id,))
        user = cursor.fetchone()
        cursor.execute("DELETE FROM Register WHERE idUsuario = %s", (user_id,))
        registrar_log(cursor, "usuarios", "Eliminar usuario", f"Usuario eliminado: {user[0] if user else user_id}", administrador=get_admin_name())
        conn.commit()


def block_user(user_id, accion):
    activo = 0 if accion in ("bloquear", "suspender") else 1
    estado = "Suspendida" if activo == 0 else "Activa"
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT nombre FROM Register WHERE idUsuario = %s", (user_id,))
        user = cursor.fetchone()
        cursor.execute(
            "UPDATE Register SET activo = %s, estadoCuenta = %s WHERE idUsuario = %s",
            (activo, estado, user_id),
        )
        accion_str = "Suspender usuario" if activo == 0 else "Reestablecer usuario"
        registrar_log(cursor, "usuarios", accion_str, f"{'Suspendido' if activo == 0 else 'Reestablecido'}: {user[0] if user else ''}", administrador=get_admin_name())
        conn.commit()
    return activo


def list_role_users():
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT idUsuario, nombre, email, rol,
                   COALESCE(activo,1) as activo,
                   DATE_FORMAT(fechaRegistro,'%d/%m/%Y') as fechaRegistro
            FROM Register WHERE rol != 'admin' ORDER BY nombre
            """
        )
        return cursor.fetchall()


def change_role(user_id, nuevo_rol):
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT nombre, rol FROM Register WHERE idUsuario = %s", (user_id,))
        user = cursor.fetchone()
        rol_anterior = user[1] if user else "-"
        cursor.execute("UPDATE Register SET rol = %s WHERE idUsuario = %s", (nuevo_rol, user_id))
        registrar_log(
            cursor,
            "roles",
            "Cambio de rol",
            f"{user[0] if user else ''}: {rol_anterior} -> {nuevo_rol}",
            rol_anterior,
            nuevo_rol,
            user[0] if user else None,
            administrador=get_admin_name(),
        )
        conn.commit()


def get_role_history():
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute("SELECT * FROM Logs WHERE modulo = 'roles' ORDER BY fecha DESC LIMIT 50")
        return cursor.fetchall()


def get_notifications_feed():
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT 
                idNotificacion as id,
                titulo,
                mensaje,
                tipo,
                destinatario,
                email_individual,
                enviado_por,
                estado,
                leido,
                DATE_FORMAT(fecha, '%d/%m/%Y %H:%i') as fecha,
                fecha_programada,
                'notificacion' as tipo_registro
            FROM notificaciones
            UNION ALL
            SELECT 
                NULL as id,
                CONCAT('Cita: ', c.tipoCita) as titulo,
                CONCAT('Paciente: ', r.nombre) as mensaje,
                'profesional' as tipo,
                NULL as destinatario,
                NULL as email_individual,
                r.nombre as enviado_por,
                'enviado' as estado,
                NULL as leido,
                DATE_FORMAT(c.fecha, '%d/%m/%Y %H:%i') as fecha,
                NULL as fecha_programada,
                'profesional' as tipo_registro
            FROM Citas c
            JOIN Register r ON c.idProfesional = r.idUsuario
            UNION ALL
            SELECT 
                NULL as id,
                CONCAT('Cita solicitada por: ', r.nombre) as titulo,
                CONCAT('Profesional: ', p.nombre) as mensaje,
                'paciente' as tipo,
                NULL as destinatario,
                NULL as email_individual,
                r.nombre as enviado_por,
                'enviado' as estado,
                NULL as leido,
                DATE_FORMAT(c.fecha, '%d/%m/%Y %H:%i') as fecha,
                NULL as fecha_programada,
                'paciente' as tipo_registro
            FROM Citas c
            JOIN Register r ON c.idPaciente = r.idUsuario
            JOIN Register p ON c.idProfesional = p.idUsuario
            ORDER BY fecha DESC
            LIMIT 200
            """
        )
        return cursor.fetchall()


def create_notification(data):
    estado = "enviado" if data.get("envio") == "inmediato" else "pendiente"
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO Notificaciones
                (titulo, mensaje, tipo, destinatario, email_individual, enviado_por, estado, fecha_programada)
            VALUES (%s, %s, %s, %s, %s, 'Admin', %s, %s)
            """,
            (
                data.get("titulo"),
                data.get("mensaje"),
                data.get("tipo", "info"),
                data.get("destinatario"),
                data.get("email_individual"),
                estado,
                data.get("fecha_programada") or None,
            ),
        )
        registrar_log(cursor, "notificaciones", "Enviar notificacion", f"{data.get('titulo')} -> {data.get('destinatario')}", administrador=get_admin_name())
        conn.commit()


def delete_notification(notification_id):
    with db_cursor() as (conn, cursor):
        cursor.execute("DELETE FROM Notificaciones WHERE idNotificacion = %s", (notification_id,))
        registrar_log(cursor, "notificaciones", "Eliminar notificacion", f"ID: {notification_id}", administrador=get_admin_name())
        conn.commit()


def get_logs():
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT idLog as id, administrador, modulo, accion, detalle,
                   DATE_FORMAT(fecha,'%d/%m/%Y %H:%i') as fecha,
                   'admin' as origen
            FROM logs ORDER BY fecha DESC LIMIT 200
            """
        )
        logs_admin = cursor.fetchall()
        cursor.execute(
            """
            SELECT a.idAuditoria as id,
                   COALESCE(r.nombre, CONCAT('Usuario #', a.idUsuario)) as administrador,
                   'accesos' as modulo,
                   a.accion,
                   CONCAT('IP: ', a.ip) as detalle,
                   DATE_FORMAT(a.fecha,'%d/%m/%Y %H:%i') as fecha,
                   'auditoria' as origen
            FROM auditoriaaccesos a
            LEFT JOIN register r ON a.idUsuario = r.idUsuario
            ORDER BY a.fecha DESC LIMIT 200
            """
        )
        logs_auditoria = cursor.fetchall()
        cursor.execute(
            """
            SELECT idNotificacion as id,
                   enviado_por as administrador,
                   'notificaciones' as modulo,
                   CONCAT('Notificación: ', titulo) as accion,
                   CONCAT(destinatario, ' - ', mensaje) as detalle,
                   DATE_FORMAT(fecha,'%d/%m/%Y %H:%i') as fecha,
                   'notificacion' as origen
            FROM notificaciones
            ORDER BY fecha DESC LIMIT 100
            """
        )
        logs_notificaciones = cursor.fetchall()
        cursor.execute(
            """
            SELECT c.idCita as id, pr.nombre as administrador,
                   'notificaciones' as modulo,
                   CONCAT('Cita profesional: ', c.tipoCita) as accion,
                   CONCAT('Paciente: ', pa.nombre, ' - Fecha: ', DATE_FORMAT(c.fecha,'%d/%m/%Y')) as detalle,
                   DATE_FORMAT(c.fecha,'%d/%m/%Y %H:%i') as fecha,
                   'profesional' as origen
            FROM Citas c
            JOIN Register pr ON c.idProfesional = pr.idUsuario
            JOIN Register pa ON c.idPaciente = pa.idUsuario
            ORDER BY c.fecha DESC LIMIT 100
            """
        )
        logs_profesionales = cursor.fetchall()
        cursor.execute(
            """
            SELECT c.idCita as id, pa.nombre as administrador,
                   'notificaciones' as modulo,
                   CONCAT('Cita paciente: ', c.tipoCita) as accion,
                   CONCAT('Profesional: ', pr.nombre, ' - Fecha: ', DATE_FORMAT(c.fecha,'%d/%m/%Y')) as detalle,
                   DATE_FORMAT(c.fecha,'%d/%m/%Y %H:%i') as fecha,
                   'paciente' as origen
            FROM Citas c
            JOIN Register pa ON c.idPaciente = pa.idUsuario
            JOIN Register pr ON c.idProfesional = pr.idUsuario
            ORDER BY c.fecha DESC LIMIT 100
            """
        )
        logs_pacientes = cursor.fetchall()
    return logs_admin + logs_auditoria + logs_notificaciones + logs_profesionales + logs_pacientes
