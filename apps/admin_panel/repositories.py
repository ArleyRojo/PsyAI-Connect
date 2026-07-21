import logging

from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.db import connection

from apps.admin_panel.models import AuditoriaAccesos, Logs
from apps.authentication.models import Register

logger = logging.getLogger(__name__)


class AdminRepository:
    _logs_version = 0

    @staticmethod
    def increment_logs_version():
        AdminRepository._logs_version += 1

    @staticmethod
    def get_logs_version():
        return AdminRepository._logs_version

    def get_admin_name(self):
        return "Admin"

    def registrar_log(self, modulo, accion, detalle, rol_anterior=None, rol_nuevo=None, usuario_afectado=None, administrador="Admin"):
        try:
            Logs.objects.create(
                administrador=administrador,
                modulo=modulo,
                accion=accion,
                detalle=detalle,
                rol_anterior=rol_anterior,
                rol_nuevo=rol_nuevo,
                usuario_afectado=usuario_afectado,
            )
            AdminRepository.increment_logs_version()
        except Exception:
            pass

    def registrar_evento_seguridad(self, accion, detalle, administrador="Sistema"):
        self.registrar_log("seguridad", accion, detalle, administrador=administrador)

    def ensure_report_columns(self):
        pass

    def get_stats(self):
        total_usuarios = Register.objects.count()
        usuarios_activos = Register.objects.filter(
            activo=True, estadoCuenta="Activa",
        ).count()
        cuentas_suspendidas = Register.objects.filter(
            Q(activo=False) | Q(estadoCuenta="Suspendida"),
        ).count()

        from apps.scheduling.models import Citas, Notificaciones

        notificaciones = Notificaciones.objects.count()
        notificaciones_pendientes = Notificaciones.objects.filter(estado="pendiente").count()
        citas_pendientes = Citas.objects.filter(estado="Pendiente").count()

        from django.utils import timezone
        today = timezone.now().date()
        logs_hoy = Logs.objects.filter(fecha__date=today).count()

        yesterday = today - timezone.timedelta(days=1)
        fallos_login = Logs.objects.filter(
            modulo="seguridad", accion="Login fallido",
            fecha__gte=yesterday,
        ).count()
        actividad_sospechosa = Logs.objects.filter(
            modulo="seguridad", accion__startswith="Rate limit",
            fecha__gte=yesterday,
        ).count()

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(DISTINCT SUBSTRING_INDEX(detalle, 'IP: ', -1))
                FROM Logs WHERE modulo='seguridad' AND accion LIKE 'Rate limit%%'
                AND detalle LIKE '%%IP: %%' AND fecha >= NOW() - INTERVAL 1 DAY
            """)
            ips_bloqueadas = cursor.fetchone()[0] or 0

        tokens_invalidos = Logs.objects.filter(
            modulo="seguridad", accion="Token invalido",
            fecha__gte=yesterday,
        ).count()

        security_timeline_rows = Logs.objects.filter(
            modulo="seguridad",
        ).order_by("-fecha")[:10]

        security_timeline = []
        for log in security_timeline_rows:
            if log.accion and log.accion.startswith("Rate limit"):
                tipo = "error"
            elif log.accion == "Token invalido":
                tipo = "security"
            else:
                tipo = "warning"
            security_timeline.append({
                "titulo": log.accion,
                "detalle": log.detalle,
                "tipo": tipo,
                "tiempo": log.fecha.strftime("%d/%m/%Y %H:%M") if log.fecha else "",
            })

        actividad_rows = Logs.objects.order_by("-fecha")[:5]
        actividad = [
            {
                "accion": log.accion,
                "detalle": log.detalle,
                "fecha": log.fecha.strftime("%d/%m/%Y %H:%M") if log.fecha else "",
            }
            for log in actividad_rows
        ]

        return {
            "total_usuarios": total_usuarios,
            "usuarios_activos": usuarios_activos,
            "cuentas_suspendidas": cuentas_suspendidas,
            "notificaciones": notificaciones,
            "notificaciones_pendientes": notificaciones_pendientes,
            "citas_pendientes": citas_pendientes,
            "cola_tareas": notificaciones_pendientes + citas_pendientes,
            "logs_hoy": logs_hoy,
            "fallos_login": fallos_login,
            "actividad_sospechosa": actividad_sospechosa,
            "ips_bloqueadas": ips_bloqueadas,
            "tokens_invalidos": tokens_invalidos,
            "alertas_criticas": ips_bloqueadas + actividad_sospechosa,
            "alertas_warnings": fallos_login,
            "alertas_info": tokens_invalidos,
            "security_timeline": security_timeline,
            "actividad_reciente": actividad,
        }

    def list_users(self, page=1, limit=20):
        offset = (page - 1) * limit
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT r.idUsuario, r.nombre, r.email, r.rol,
                       COALESCE(r.activo, 1) as activo,
                       r.estadoCuenta,
                       DATE_FORMAT(r.fechaRegistro, '%%d/%%m/%%Y') as fechaRegistro,
                       (SELECT DATE_FORMAT(MAX(a.fecha),'%%d/%%m/%%Y %%H:%%i')
                        FROM AuditoriaAccesos a WHERE a.idUsuario = r.idUsuario) as ultimoAcceso
                FROM Register r
                ORDER BY
                    CASE r.rol
                        WHEN 'admin' THEN 1
                        WHEN 'profesional' THEN 2
                        WHEN 'paciente' THEN 3
                    END, r.fechaRegistro DESC
                LIMIT %s OFFSET %s
            """, [limit, offset])
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return rows

    def get_user(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT idUsuario, nombre, email, rol,
                       COALESCE(activo,1) as activo, estadoCuenta,
                       DATE_FORMAT(fechaRegistro,'%%d/%%m/%%Y') as fechaRegistro
                FROM Register WHERE idUsuario = %s
            """, [user_id])
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None

    def create_user(self, data):
        from django.contrib.auth.hashers import make_password

        password = data.get("contrasena")
        if not password:
            raise ValueError("La contraseña es requerida para crear un usuario")
        user = Register(
            nombre=data.get("nombre"),
            email=data.get("email"),
            contrasena=make_password(password),
            rol=data.get("rol", "paciente"),
        )
        user.save()
        if data.get("rol") == "paciente":
            from apps.patients.models import PerfilPaciente
            PerfilPaciente.objects.create(idPaciente=user.idUsuario)
        elif data.get("rol") == "profesional":
            from apps.professionals.models import PerfilProfesional
            PerfilProfesional.objects.create(idProfesional=user.idUsuario)
        self.registrar_log(
            "usuarios", "Crear usuario",
            f"Usuario creado: {data.get('nombre')} - Rol: {data.get('rol')}",
            administrador=self.get_admin_name(),
        )

    def update_user(self, data):
        try:
            user = Register.objects.get(idUsuario=data.get("idUsuario"))
            user.nombre = data.get("nombre")
            user.email = data.get("email")
            user.estadoCuenta = data.get("estado")
            user.save(update_fields=["nombre", "email", "estadoCuenta"])
            self.registrar_log(
                "usuarios", "Editar usuario",
                f"Usuario editado: {data.get('nombre')}",
                administrador=self.get_admin_name(),
            )
        except Register.DoesNotExist:
            pass

    def delete_user(self, user_id):
        try:
            user = Register.objects.get(idUsuario=user_id)
            nombre = user.nombre
            user.delete()
            self.registrar_log(
                "usuarios", "Eliminar usuario",
                f"Usuario eliminado: {nombre}",
                administrador=self.get_admin_name(),
            )
        except Register.DoesNotExist:
            pass

    def block_user(self, user_id, accion):
        activo = 0 if accion in ("bloquear", "suspender") else 1
        estado = "Suspendida" if activo == 0 else "Activa"
        try:
            user = Register.objects.get(idUsuario=user_id)
            user.activo = bool(activo)
            user.estadoCuenta = estado
            user.save(update_fields=["activo", "estadoCuenta"])
            accion_str = "Suspender usuario" if activo == 0 else "Reestablecer usuario"
            self.registrar_log(
                "usuarios", accion_str,
                f"{'Suspendido' if activo == 0 else 'Reestablecido'}: {user.nombre}",
                administrador=self.get_admin_name(),
            )
        except Register.DoesNotExist:
            pass
        return activo

    def list_role_users(self):
        users = Register.objects.exclude(rol="admin").order_by("nombre")
        return [
            {
                "idUsuario": u.idUsuario,
                "nombre": u.nombre,
                "email": u.email,
                "rol": u.rol,
                "activo": u.activo,
                "estadoCuenta": u.estadoCuenta,
                "fechaRegistro": u.fechaRegistro.strftime("%d/%m/%Y") if u.fechaRegistro else "",
            }
            for u in users
        ]

    def change_role(self, user_id, nuevo_rol):
        try:
            user = Register.objects.get(idUsuario=user_id)
            rol_anterior = user.rol
            user.rol = nuevo_rol
            user.save(update_fields=["rol"])
            self.registrar_log(
                "roles", "Cambio de rol",
                f"{user.nombre}: {rol_anterior} -> {nuevo_rol}",
                rol_anterior, nuevo_rol, user.nombre,
                administrador=self.get_admin_name(),
            )
        except Register.DoesNotExist:
            pass

    def get_role_history(self):
        logs = Logs.objects.filter(modulo="roles").order_by("-fecha")[:50]
        return [l.to_dict() for l in logs]

    def get_notifications_feed(self):
        with connection.cursor() as cursor:
            cursor.execute("""
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
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def create_notification(self, data):
        from apps.scheduling.models import Notificaciones

        estado = "enviado" if data.get("envio") == "inmediato" else "pendiente"
        Notificaciones.objects.create(
            titulo=data.get("titulo"),
            mensaje=data.get("mensaje"),
            tipo=data.get("tipo", "info"),
            destinatario=data.get("destinatario"),
            email_individual=data.get("email_individual"),
            enviado_por="Admin",
            estado=estado,
            fecha_programada=data.get("fecha_programada") or None,
        )
        self.registrar_log(
            "notificaciones", "Enviar notificacion",
            f"{data.get('titulo')} -> {data.get('destinatario')}",
            administrador=self.get_admin_name(),
        )

    def delete_notification(self, notification_id):
        from apps.scheduling.models import Notificaciones

        try:
            notif = Notificaciones.objects.get(idNotificacion=notification_id)
            notif.delete()
            self.registrar_log(
                "notificaciones", "Eliminar notificacion",
                f"ID: {notification_id}",
                administrador=self.get_admin_name(),
            )
        except Notificaciones.DoesNotExist:
            pass

    def get_users_by_ids(self, user_ids):
        if not user_ids:
            return []
        users = Register.objects.filter(idUsuario__in=user_ids)
        return [
            {
                "idUsuario": u.idUsuario,
                "nombre": u.nombre,
                "email": u.email,
                "rol": u.rol,
                "fotoPerfil": u.fotoPerfil,
            }
            for u in users
        ]

    def get_logs(self, limit=None):
        limit_val = limit or 200

        logs_admin = Logs.objects.order_by("-fecha")[:limit_val]
        logs_admin_list = [
            {
                "id": l.idLog,
                "administrador": l.administrador,
                "modulo": l.modulo,
                "accion": l.accion,
                "detalle": l.detalle,
                "fecha": l.fecha.strftime("%d/%m/%Y %H:%M") if l.fecha else "",
                "origen": "admin",
            }
            for l in logs_admin
        ]

        logs_auditoria = AuditoriaAccesos.objects.select_related("idUsuario").order_by("-fecha")[:limit_val]
        logs_auditoria_list = [
            {
                "id": a.idAuditoria,
                "administrador": a.idUsuario.nombre if a.idUsuario else f"Usuario #{a.idUsuario_id}",
                "modulo": "accesos",
                "accion": a.accion,
                "detalle": f"IP: {a.ip}",
                "fecha": a.fecha.strftime("%d/%m/%Y %H:%M") if a.fecha else "",
                "origen": "auditoria",
            }
            for a in logs_auditoria
        ]

        return logs_admin_list + logs_auditoria_list

    def get_chatbot_historial_rows(self, limit=200):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT nombre, idPaciente, mensajeUsuario, respuestaChatbot,
                       nivelEmocionalDetectado, fecha
                FROM vistahistorialchatbot
                ORDER BY nombre ASC, fecha ASC LIMIT %s
            """, [limit])
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_chatbot_historial_stats(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN nivelEmocionalDetectado = 'Alto' THEN 1 ELSE 0 END) as alto,
                       SUM(CASE WHEN nivelEmocionalDetectado = 'Medio' THEN 1 ELSE 0 END) as medio,
                       SUM(CASE WHEN nivelEmocionalDetectado = 'Bajo' THEN 1 ELSE 0 END) as bajo
                FROM vistahistorialchatbot
            """)
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else {"total": 0, "alto": 0, "medio": 0, "bajo": 0}
