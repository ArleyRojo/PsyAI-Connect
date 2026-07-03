from sqlalchemy import select, func, text
from flask import session
from app.database.session import db_session
from app.models.register import Register
from app.models.logs import Logs
from app.models.notificaciones import Notificaciones
from app.models.citas import Citas
from app.models.auditoria_accesos import AuditoriaAccesos
from app.models.perfil_paciente import PerfilPaciente
from app.models.perfil_profesional import PerfilProfesional
from app.utils.security import SecurityHelper

class AdminRepository:
    _logs_version = 0

    @staticmethod
    def increment_logs_version():
        AdminRepository._logs_version += 1

    @staticmethod
    def get_logs_version():
        return AdminRepository._logs_version

    def get_admin_name(self):
        return session.get("nombre", "Admin")

    def registrar_log(self, sess, modulo, accion, detalle, rol_anterior=None, rol_nuevo=None, usuario_afectado=None, administrador="Admin"):
        try:
            sess.add(Logs(
                administrador=administrador,
                modulo=modulo,
                accion=accion,
                detalle=detalle,
                rol_anterior=rol_anterior,
                rol_nuevo=rol_nuevo,
                usuario_afectado=usuario_afectado,
            ))
            AdminRepository.increment_logs_version()
        except Exception:
            pass

    def registrar_evento_seguridad(self, accion, detalle, administrador="Sistema"):
        with db_session() as s:
            self.registrar_log(s, "seguridad", accion, detalle, administrador=administrador)

    def ensure_report_columns(self):
        pass

    def get_stats(self):
        with db_session() as session:
            total_usuarios = session.execute(select(func.count()).select_from(Register).where(Register.rol != "admin")).scalar()
            usuarios_activos = session.execute(
                select(func.count()).select_from(Register).where(
                    Register.rol != "admin", Register.activo == True, Register.estadoCuenta == "Activa"
                )
            ).scalar()
            cuentas_suspendidas = session.execute(
                select(func.count()).select_from(Register).where(
                    Register.rol != "admin", (Register.activo == False) | (Register.estadoCuenta == "Suspendida")
                )
            ).scalar()
            notificaciones = session.execute(select(func.count()).select_from(Notificaciones)).scalar()
            notificaciones_pendientes = session.execute(
                select(func.count()).select_from(Notificaciones).where(Notificaciones.estado == "pendiente")
            ).scalar()
            citas_pendientes = session.execute(
                select(func.count()).select_from(Citas).where(Citas.estado == "Pendiente")
            ).scalar()
            logs_hoy = session.execute(
                select(func.count()).select_from(Logs).where(func.date(Logs.fecha) == func.curdate())
            ).scalar()
            fallos_login = session.execute(
                select(func.count()).select_from(Logs).where(
                    Logs.modulo == "seguridad", Logs.accion == "Login fallido",
                    Logs.fecha >= text("NOW() - INTERVAL 1 DAY")
                )
            ).scalar()
            actividad_sospechosa = session.execute(
                select(func.count()).select_from(Logs).where(
                    Logs.modulo == "seguridad", Logs.accion.like("Rate limit%"),
                    Logs.fecha >= text("NOW() - INTERVAL 1 DAY")
                )
            ).scalar()
            ips_bloqueadas = session.execute(
                text("""
                    SELECT COUNT(DISTINCT SUBSTRING_INDEX(detalle, 'IP: ', -1))
                    FROM Logs WHERE modulo='seguridad' AND accion LIKE 'Rate limit%%'
                    AND detalle LIKE '%%IP: %%' AND fecha >= NOW() - INTERVAL 1 DAY
                """)
            ).scalar() or 0
            tokens_invalidos = session.execute(
                select(func.count()).select_from(Logs).where(
                    Logs.modulo == "seguridad", Logs.accion == "Token invalido",
                    Logs.fecha >= text("NOW() - INTERVAL 1 DAY")
                )
            ).scalar()
            security_timeline_rows = session.execute(
                text("""
                    SELECT accion as titulo, detalle,
                        CASE
                            WHEN accion LIKE 'Rate limit%%' THEN 'error'
                            WHEN accion = 'Token invalido' THEN 'security'
                            ELSE 'warning'
                        END as tipo,
                        DATE_FORMAT(fecha,'%d/%m/%Y %H:%i') as tiempo
                    FROM Logs WHERE modulo = 'seguridad'
                    ORDER BY fecha DESC LIMIT 10
                """)
            ).mappings().all()
            security_timeline = [dict(r) for r in security_timeline_rows]
            actividad_rows = session.execute(
                text("SELECT accion, detalle, DATE_FORMAT(fecha,'%d/%m/%Y %H:%i') as fecha FROM Logs ORDER BY fecha DESC LIMIT 5")
            ).mappings().all()
            actividad = [dict(r) for r in actividad_rows]
            return {
                "total_usuarios": total_usuarios or 0,
                "usuarios_activos": usuarios_activos or 0,
                "cuentas_suspendidas": cuentas_suspendidas or 0,
                "notificaciones": notificaciones or 0,
                "notificaciones_pendientes": notificaciones_pendientes or 0,
                "citas_pendientes": citas_pendientes or 0,
                "cola_tareas": (notificaciones_pendientes or 0) + (citas_pendientes or 0),
                "logs_hoy": logs_hoy or 0,
                "fallos_login": fallos_login or 0,
                "actividad_sospechosa": actividad_sospechosa or 0,
                "ips_bloqueadas": ips_bloqueadas,
                "tokens_invalidos": tokens_invalidos or 0,
                "alertas_criticas": (ips_bloqueadas or 0) + (actividad_sospechosa or 0),
                "alertas_warnings": fallos_login or 0,
                "alertas_info": tokens_invalidos or 0,
                "security_timeline": security_timeline,
                "actividad_reciente": actividad,
            }

    def list_users(self, page=1, limit=20):
        offset = (page - 1) * limit
        with db_session() as session:
            rows = session.execute(
                text("""
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
                    LIMIT :lim OFFSET :off
                """),
                {"lim": limit, "off": offset}
            ).mappings().all()
            return [dict(r) for r in rows]

    def get_user(self, user_id):
        with db_session() as session:
            row = session.execute(
                text("""
                    SELECT idUsuario, nombre, email, rol,
                           COALESCE(activo,1) as activo, estadoCuenta,
                           DATE_FORMAT(fechaRegistro,'%d/%m/%Y') as fechaRegistro
                    FROM Register WHERE idUsuario = :uid
                """),
                {"uid": user_id}
            ).mappings().one_or_none()
            return dict(row) if row else None

    def create_user(self, data):
        password = data.get("contrasena") or "1234"
        with db_session() as s:
            reg = Register(
                nombre=data.get("nombre"),
                email=data.get("email"),
                contrasena=SecurityHelper.hash_password(password),
                rol=data.get("rol", "paciente"),
            )
            s.add(reg)
            s.flush()
            if data.get("rol") == "paciente":
                s.add(PerfilPaciente(idPaciente=reg.idUsuario))
            elif data.get("rol") == "profesional":
                s.add(PerfilProfesional(idProfesional=reg.idUsuario))
            self.registrar_log(s, "usuarios", "Crear usuario",
                               f"Usuario creado: {data.get('nombre')} - Rol: {data.get('rol')}",
                               administrador=self.get_admin_name())

    def update_user(self, data):
        with db_session() as s:
            user = s.get(Register, data.get("idUsuario"))
            if user:
                user.nombre = data.get("nombre")
                user.email = data.get("email")
                user.estadoCuenta = data.get("estado")
                self.registrar_log(s, "usuarios", "Editar usuario",
                                   f"Usuario editado: {data.get('nombre')}",
                                   administrador=self.get_admin_name())

    def delete_user(self, user_id):
        with db_session() as s:
            user = s.get(Register, user_id)
            nombre = user.nombre if user else str(user_id)
            if user:
                s.delete(user)
            self.registrar_log(s, "usuarios", "Eliminar usuario",
                               f"Usuario eliminado: {nombre}",
                               administrador=self.get_admin_name())

    def block_user(self, user_id, accion):
        activo = 0 if accion in ("bloquear", "suspender") else 1
        estado = "Suspendida" if activo == 0 else "Activa"
        with db_session() as s:
            user = s.get(Register, user_id)
            if user:
                user.activo = bool(activo)
                user.estadoCuenta = estado
                accion_str = "Suspender usuario" if activo == 0 else "Reestablecer usuario"
                self.registrar_log(s, "usuarios", accion_str,
                                   f"{'Suspendido' if activo == 0 else 'Reestablecido'}: {user.nombre}",
                                   administrador=self.get_admin_name())
        return activo

    def list_role_users(self):
        with db_session() as session:
            rows = session.execute(
                text("""
                    SELECT idUsuario, nombre, email, rol,
                           COALESCE(activo,1) as activo,
                           DATE_FORMAT(fechaRegistro,'%d/%m/%Y') as fechaRegistro
                    FROM Register WHERE rol != 'admin' ORDER BY nombre
                """)
            ).mappings().all()
            return [dict(r) for r in rows]

    def change_role(self, user_id, nuevo_rol):
        with db_session() as s:
            user = s.get(Register, user_id)
            if user:
                rol_anterior = user.rol
                user.rol = nuevo_rol
                self.registrar_log(s, "roles", "Cambio de rol",
                                   f"{user.nombre}: {rol_anterior} -> {nuevo_rol}",
                                   rol_anterior, nuevo_rol, user.nombre,
                                   administrador=self.get_admin_name())

    def get_role_history(self):
        with db_session() as session:
            rows = session.execute(
                text("SELECT * FROM Logs WHERE modulo = 'roles' ORDER BY fecha DESC LIMIT 50")
            ).mappings().all()
            return [dict(r) for r in rows]

    def get_notifications_feed(self):
        with db_session() as session:
            rows = session.execute(
                text("""
                    SELECT
                        n.idNotificacion, n.titulo, n.mensaje, n.tipo,
                        COALESCE(n.destinatario, reg.nombre, reg.email) as destinatario,
                        n.email_individual, n.enviado_por, n.estado, n.leido,
                        DATE_FORMAT(n.fecha, '%d/%m/%Y %H:%i') as fecha,
                        n.fecha_programada, 'notificacion' as tipo_registro,
                        n.fecha as fecha_orden
                    FROM notificaciones n
                    LEFT JOIN Register reg ON reg.idUsuario = n.idUsuario
                    UNION ALL
                    SELECT NULL as idNotificacion,
                        CONCAT('Cita: ', c.tipoCita) as titulo,
                        CONCAT('Paciente: ', pa.nombre) as mensaje,
                        'profesional' as tipo,
                        CONCAT('profesional_', pr.idUsuario) as destinatario,
                        NULL as email_individual, pr.nombre as enviado_por,
                        'enviado' as estado, NULL as leido,
                        DATE_FORMAT(c.fecha, '%d/%m/%Y %H:%i') as fecha,
                        NULL as fecha_programada, 'profesional' as tipo_registro,
                        c.fecha as fecha_orden
                    FROM Citas c
                    JOIN Register pr ON c.idProfesional = pr.idUsuario
                    JOIN Register pa ON c.idPaciente = pa.idUsuario
                    UNION ALL
                    SELECT NULL as idNotificacion,
                        CONCAT('Cita solicitada por: ', pa.nombre) as titulo,
                        CONCAT('Profesional: ', pr.nombre) as mensaje,
                        'paciente' as tipo,
                        CONCAT('paciente_', pa.idUsuario) as destinatario,
                        NULL as email_individual, pa.nombre as enviado_por,
                        'enviado' as estado, NULL as leido,
                        DATE_FORMAT(c.fecha, '%d/%m/%Y %H:%i') as fecha,
                        NULL as fecha_programada, 'paciente' as tipo_registro,
                        c.fecha as fecha_orden
                    FROM Citas c
                    JOIN Register pa ON c.idPaciente = pa.idUsuario
                    JOIN Register pr ON c.idProfesional = pr.idUsuario
                    ORDER BY fecha_orden DESC LIMIT 200
                """)
            ).mappings().all()
            return [dict(r) for r in rows]

    def create_notification(self, data):
        estado = "enviado" if data.get("envio") == "inmediato" else "pendiente"
        with db_session() as s:
            s.add(Notificaciones(
                titulo=data.get("titulo"),
                mensaje=data.get("mensaje"),
                tipo=data.get("tipo", "info"),
                destinatario=data.get("destinatario"),
                email_individual=data.get("email_individual"),
                enviado_por="Admin",
                estado=estado,
                fecha_programada=data.get("fecha_programada") or None,
            ))
            self.registrar_log(s, "notificaciones", "Enviar notificacion",
                               f"{data.get('titulo')} -> {data.get('destinatario')}",
                               administrador=self.get_admin_name())

    def delete_notification(self, notification_id):
        with db_session() as s:
            notif = s.get(Notificaciones, notification_id)
            if notif:
                s.delete(notif)
                self.registrar_log(s, "notificaciones", "Eliminar notificacion",
                                   f"ID: {notification_id}",
                                   administrador=self.get_admin_name())

    def get_users_by_ids(self, user_ids):
        if not user_ids:
            return []
        with db_session() as session:
            stmt = select(
                Register.idUsuario, Register.nombre, Register.email,
                Register.rol, Register.fotoPerfil
            ).where(Register.idUsuario.in_(user_ids))
            rows = session.execute(stmt).all()
            return [
                {"idUsuario": r[0], "nombre": r[1], "email": r[2], "rol": r[3], "fotoPerfil": r[4]}
                for r in rows
            ]

    def get_logs(self, limit=None):
        limit_clause = f"LIMIT {limit}" if limit else "LIMIT 200"
        with db_session() as session:
            rows = session.execute(
                text(f"""
                    SELECT idLog as id, administrador, modulo, accion, detalle,
                           DATE_FORMAT(fecha,'%d/%m/%Y %H:%i') as fecha, 'admin' as origen
                    FROM logs ORDER BY fecha DESC {limit_clause}
                """)
            ).mappings().all()
            logs_admin = [dict(r) for r in rows]
            rows = session.execute(
                text(f"""
                    SELECT a.idAuditoria as id,
                           COALESCE(r.nombre, CONCAT('Usuario #', a.idUsuario)) as administrador,
                           'accesos' as modulo, a.accion, CONCAT('IP: ', a.ip) as detalle,
                           DATE_FORMAT(a.fecha,'%d/%m/%Y %H:%i') as fecha, 'auditoria' as origen
                    FROM auditoriaaccesos a
                    LEFT JOIN register r ON a.idUsuario = r.idUsuario
                    ORDER BY a.fecha DESC {limit_clause}
                """)
            ).mappings().all()
            logs_auditoria = [dict(r) for r in rows]
            rows = session.execute(
                text(f"""
                    SELECT idNotificacion as id, enviado_por as administrador,
                           'notificaciones' as modulo, CONCAT('Notificación: ', titulo) as accion,
                           CONCAT(destinatario, ' - ', mensaje) as detalle,
                           DATE_FORMAT(fecha,'%d/%m/%Y %H:%i') as fecha, 'notificacion' as origen
                    FROM notificaciones ORDER BY fecha DESC {limit_clause}
                """)
            ).mappings().all()
            logs_notificaciones = [dict(r) for r in rows]
            rows = session.execute(
                text(f"""
                    SELECT c.idCita as id, pr.nombre as administrador,
                           'notificaciones' as modulo, CONCAT('Cita profesional: ', c.tipoCita) as accion,
                           CONCAT('Paciente: ', pa.nombre, ' - Fecha: ', DATE_FORMAT(c.fecha,'%d/%m/%Y')) as detalle,
                           DATE_FORMAT(c.fecha,'%d/%m/%Y %H:%i') as fecha, 'profesional' as origen
                    FROM Citas c
                    JOIN Register pr ON c.idProfesional = pr.idUsuario
                    JOIN Register pa ON c.idPaciente = pa.idUsuario
                    ORDER BY c.fecha DESC {limit_clause}
                """)
            ).mappings().all()
            logs_profesionales = [dict(r) for r in rows]
            rows = session.execute(
                text(f"""
                    SELECT c.idCita as id, pa.nombre as administrador,
                           'notificaciones' as modulo, CONCAT('Cita paciente: ', c.tipoCita) as accion,
                           CONCAT('Profesional: ', pr.nombre, ' - Fecha: ', DATE_FORMAT(c.fecha,'%d/%m/%Y')) as detalle,
                           DATE_FORMAT(c.fecha,'%d/%m/%Y %H:%i') as fecha, 'paciente' as origen
                    FROM Citas c
                    JOIN Register pa ON c.idPaciente = pa.idUsuario
                    JOIN Register pr ON c.idProfesional = pr.idUsuario
                    ORDER BY c.fecha DESC {limit_clause}
                """)
            ).mappings().all()
            logs_pacientes = [dict(r) for r in rows]
            return logs_admin + logs_auditoria + logs_notificaciones + logs_profesionales + logs_pacientes

    def get_chatbot_historial_rows(self, limit=200):
        with db_session() as session:
            rows = session.execute(
                text("""
                    SELECT nombre, idPaciente, mensajeUsuario, respuestaChatbot,
                           nivelEmocionalDetectado, fecha
                    FROM vistahistorialchatbot
                    ORDER BY nombre ASC, fecha ASC LIMIT :lim
                """),
                {"lim": limit}
            ).mappings().all()
            return [dict(r) for r in rows]

    def get_chatbot_historial_stats(self):
        with db_session() as session:
            row = session.execute(
                text("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN nivelEmocionalDetectado = 'Alto' THEN 1 ELSE 0 END) as alto,
                           SUM(CASE WHEN nivelEmocionalDetectado = 'Medio' THEN 1 ELSE 0 END) as medio,
                           SUM(CASE WHEN nivelEmocionalDetectado = 'Bajo' THEN 1 ELSE 0 END) as bajo
                    FROM vistahistorialchatbot
                """)
            ).mappings().one_or_none()
            return dict(row) if row else {"total": 0, "alto": 0, "medio": 0, "bajo": 0}
