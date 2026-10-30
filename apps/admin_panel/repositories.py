import logging

from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.db import connection, transaction

from apps.admin_panel.models import AuditoriaAccesos, Logs
from apps.authentication.models import Register
from apps.core.utils import fmt_bogota

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
        today = timezone.localdate()
        start = today
        end = start + timezone.timedelta(days=1)
        logs_hoy = Logs.objects.filter(fecha__gte=start, fecha__lt=end).count()

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
                "tiempo": fmt_bogota(log.fecha) if log.fecha else "",
            })

        actividad_rows = Logs.objects.order_by("-fecha")[:5]
        actividad = [
            {
                "accion": log.accion,
                "detalle": log.detalle,
                "fecha": fmt_bogota(log.fecha) if log.fecha else "",
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
                       r.fechaRegistro,
                       (SELECT MAX(a.fecha) FROM AuditoriaAccesos a WHERE a.idUsuario = r.idUsuario) as ultimoAcceso
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
        
        # Format dates using centralized utility
        for row in rows:
            row["fechaRegistro"] = fmt_bogota(row.get("fechaRegistro"))
            row["ultimoAcceso"] = fmt_bogota(row.get("ultimoAcceso"))
        
        return rows

    def get_user(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT idUsuario, nombre, email, rol,
                       COALESCE(activo,1) as activo, estadoCuenta,
                       fechaRegistro
                FROM Register WHERE idUsuario = %s
            """, [user_id])
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            if row:
                row = dict(zip(columns, row))
                row["fechaRegistro"] = fmt_bogota(row.get("fechaRegistro"))
                return row
            return None

    def create_user(self, data):
        from apps.authentication.security import SecurityHelper

        password = data.get("contrasena")
        if not password:
            raise ValueError("La contraseña es requerida para crear un usuario")
        email = data.get("email")
        if not email:
            raise ValueError("El email es requerido para crear un usuario")
        if Register.objects.filter(email=email).exists():
            raise ValueError(f"El email '{email}' ya está registrado")
        user = Register(
            nombre=data.get("nombre"),
            email=email,
            contrasena=SecurityHelper.hash_password(password),
            rol=data.get("rol", "paciente"),
        )
        with transaction.atomic():
            user.save()
            if data.get("rol") == "paciente":
                from apps.patients.models import PerfilPaciente
                PerfilPaciente.objects.create(idPaciente=user)
            elif data.get("rol") == "profesional":
                from apps.professionals.models import PerfilProfesional
                PerfilProfesional.objects.create(idProfesional=user)
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
        user_info = None
        try:
            user = Register.objects.get(idUsuario=user_id)
            user.activo = bool(activo)
            user.estadoCuenta = estado
            user.save(update_fields=["activo", "estadoCuenta"])
            user_info = {"nombre": user.nombre, "email": user.email}
            accion_str = "Suspender usuario" if activo == 0 else "Reestablecer usuario"
            self.registrar_log(
                "usuarios", accion_str,
                f"{'Suspendido' if activo == 0 else 'Reestablecido'}: {user.nombre}",
                administrador=self.get_admin_name(),
            )
        except Register.DoesNotExist:
            pass
        return activo, user_info

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
                (
                    SELECT
                        n.idNotificacion, n.titulo, n.mensaje, n.tipo,
                        COALESCE(n.destinatario, reg.nombre, reg.email) as destinatario,
                        n.email_individual, n.enviado_por, n.estado, n.leido,
                        n.fecha as fecha_raw,
                        n.fecha_programada, 'notificacion' as tipo_registro,
                        n.fecha as fecha_orden
                    FROM Notificaciones n
                    LEFT JOIN Register reg ON reg.idUsuario = n.idUsuario
                    ORDER BY n.fecha DESC LIMIT 100
                )
                UNION ALL
                (
                    SELECT NULL as idNotificacion,
                        CONCAT('Cita: ', c.tipoCita) as titulo,
                        CONCAT('Paciente: ', pa.nombre) as mensaje,
                        'profesional' as tipo,
                        CONCAT('profesional_', pr.idUsuario) as destinatario,
                        NULL as email_individual, pr.nombre as enviado_por,
                        'enviado' as estado, NULL as leido,
                        c.fecha as fecha_raw,
                        NULL as fecha_programada, 'profesional' as tipo_registro,
                        c.fecha as fecha_orden
                    FROM Citas c
                    JOIN Register pr ON c.idProfesional = pr.idUsuario
                    JOIN Register pa ON c.idPaciente = pa.idUsuario
                    WHERE c.fecha <= CURDATE()
                    ORDER BY c.fecha DESC LIMIT 50
                )
                UNION ALL
                (
                    SELECT NULL as idNotificacion,
                        CONCAT('Cita solicitada por: ', pa.nombre) as titulo,
                        CONCAT('Profesional: ', pr.nombre) as mensaje,
                        'paciente' as tipo,
                        CONCAT('paciente_', pa.idUsuario) as destinatario,
                        NULL as email_individual, pa.nombre as enviado_por,
                        'enviado' as estado, NULL as leido,
                        c.fecha as fecha_raw,
                        NULL as fecha_programada, 'paciente' as tipo_registro,
                        c.fecha as fecha_orden
                    FROM Citas c
                    JOIN Register pa ON c.idPaciente = pa.idUsuario
                    JOIN Register pr ON c.idProfesional = pr.idUsuario
                    WHERE c.fecha <= CURDATE()
                    ORDER BY c.fecha DESC LIMIT 50
                )
                ORDER BY fecha_orden DESC LIMIT 200
            """)
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Format dates in Python using centralized utility
        for row in rows:
            fecha_raw = row.pop("fecha_raw", None)
            row["fecha"] = fmt_bogota(fecha_raw)
            
            # Also format fecha_programada if present
            fecha_prog = row.get("fecha_programada")
            if fecha_prog:
                row["fecha_programada"] = fmt_bogota(fecha_prog)
        
        return rows

    def get_notification_stats(self):
        """Get real notification stats using COUNT queries on Notificaciones table only."""
        from django.utils import timezone
        from django.db import models
        from apps.scheduling.models import Notificaciones
        
        today = timezone.localdate()
        start_today = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        end_today = start_today + timezone.timedelta(days=1)
        
        # Total historial (notificaciones enviadas + fallidas, no pendientes)
        total_historial = Notificaciones.objects.exclude(estado='pendiente').count()
        
        # Enviadas hoy
        enviadas_hoy = Notificaciones.objects.filter(
            estado='enviado',
            fecha__gte=start_today,
            fecha__lt=end_today
        ).count()
        
        # Programadas (pendientes)
        programadas = Notificaciones.objects.filter(estado='pendiente').count()
        
        # Fallidas
        fallidas = Notificaciones.objects.filter(estado='fallido').count()
        
        # Tasa de entrega
        total_enviadas = Notificaciones.objects.filter(estado__in=['enviado', 'fallido']).count()
        tasa = f"{round((enviadas_hoy / total_enviadas) * 100)}%" if total_enviadas else "0%"
        
        # Alcanzados - notificaciones con destinatario/email_individual definidos
        alcanzados = Notificaciones.objects.exclude(estado='pendiente').filter(
            models.Q(destinatario__isnull=False) & ~models.Q(destinatario='') |
            models.Q(email_individual__isnull=False) & ~models.Q(email_individual='') |
            models.Q(mensaje__isnull=False) & ~models.Q(mensaje='')
        ).count()
        
        return {
            "total_historial": total_historial,
            "enviadas_hoy": enviadas_hoy,
            "programadas": programadas,
            "tasa": tasa,
            "alcanzados": alcanzados,
        }

    def create_notification(self, data):
        from apps.scheduling.models import Notificaciones
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings
        from django.template.loader import render_to_string
        from apps.core.utils import parse_bogota_datetime
        from apps.authentication.models import Register
        from apps.patients.models import PerfilPaciente
        import re

        # Validar campos obligatorios
        titulo = data.get("titulo", "").strip()
        mensaje = data.get("mensaje", "").strip()
        tipo = data.get("tipo", "info")
        destinatario = data.get("destinatario")
        envio = data.get("envio", "inmediato")
        email_individual = data.get("email_individual", "").strip() if data.get("email_individual") else None
        fecha_programada = parse_bogota_datetime(data.get("fecha_programada"))

        if not titulo or not mensaje or not destinatario:
            raise ValueError("Título, mensaje y destinatario son obligatorios")

        if destinatario == "individual":
            if not email_individual:
                raise ValueError("Email individual es obligatorio cuando destinatario es 'individual'")
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email_individual):
                raise ValueError("Email individual inválido")

        estado = "enviado" if envio == "inmediato" else "pendiente"
        
        notificacion = Notificaciones.objects.create(
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo,
            destinatario=destinatario,
            email_individual=email_individual,
            enviado_por="Admin",
            estado=estado,
            canal="email",
            fecha_programada=fecha_programada,
        )
        self.registrar_log(
            "notificaciones", "Enviar notificacion",
            f"{titulo} -> {destinatario}",
            administrador=self.get_admin_name(),
        )

        # Enviar correo si es inmediato
        if envio == "inmediato":
            try:
                enviados, fallidos, error_detalle = self._send_admin_notification_emails(
                    notificacion_id=notificacion.idNotificacion,
                    destinatario=destinatario,
                    email_individual=email_individual,
                    titulo=titulo,
                    mensaje=mensaje,
                    tipo=tipo,
                )
                
                # Actualizar estado de la notificación
                if enviados > 0:
                    notificacion.estado = "enviado"
                    notificacion.errorDetalle = None
                else:
                    notificacion.estado = "fallido"
                    notificacion.errorDetalle = error_detalle or "No se pudo enviar a ningún destinatario"
                notificacion.save(update_fields=["estado", "errorDetalle"])
                
            except Exception as e:
                logger.exception("Error enviando emails de notificación")
                notificacion.estado = "fallido"
                notificacion.errorDetalle = str(e)
                notificacion.save(update_fields=["estado", "errorDetalle"])
        
        return notificacion

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
                "fecha": fmt_bogota(l.fecha) if l.fecha else "",
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
                "fecha": fmt_bogota(a.fecha) if a.fecha else "",
                "origen": "auditoria",
            }
            for a in logs_auditoria
        ]

        return logs_admin_list + logs_auditoria_list

    def get_chatbot_historial_rows(self, limit=200):
        from apps.chatbot.models import ConversacionesChatbot
        rows = (
            ConversacionesChatbot.objects.all()
            .order_by("nombrePaciente", "fecha")
            [:limit]
        )
        return [
            {
                "nombre": r.nombrePaciente,
                "idPaciente": r.idPaciente_id,
                "mensajeUsuario": r.mensajeUsuario,
                "respuestaChatbot": r.respuestaChatbot,
                "nivelEmocionalDetectado": r.nivelEmocionalDetectado,
                "fecha": r.fecha,
            }
            for r in rows
        ]

    def get_chatbot_historial_stats(self):
        from apps.chatbot.models import ConversacionesChatbot
        from django.db.models import Count, Q
        qs = ConversacionesChatbot.objects.all()
        alto = qs.filter(nivelEmocionalDetectado="Alto").count()
        medio = qs.filter(nivelEmocionalDetectado="Medio").count()
        bajo = qs.filter(nivelEmocionalDetectado="Bajo").count()
        return {
            "total": qs.count(),
            "alto": alto,
            "medio": medio,
            "bajo": bajo,
        }

    def _get_tipo_style(self, tipo):
        """Retorna estilos visuales según el tipo de notificación"""
        styles = {
            "sistema": {
                "accent_gradient": "linear-gradient(135deg,#1565C0 0%,#1E88E5 50%,#42A5F5 100%)",
                "icon_bg": "linear-gradient(135deg,#E3F2FD 0%,#BBDEFB 100%)",
                "icon": "&#9881;",
                "tipo_bg": "#E3F2FD",
                "tipo_color": "#1565C0",
                "tipo_border": "#BBDEFB",
                "tipo_label": "Sistema",
            },
            "cita": {
                "accent_gradient": "linear-gradient(135deg,#2E7D32 0%,#388E3C 50%,#4CAF50 100%)",
                "icon_bg": "linear-gradient(135deg,#E8F5E9 0%,#C8E6C9 100%)",
                "icon": "&#128197;",
                "tipo_bg": "#E8F5E9",
                "tipo_color": "#2E7D32",
                "tipo_border": "#C8E6C9",
                "tipo_label": "Cita",
            },
            "recordatorio": {
                "accent_gradient": "linear-gradient(135deg,#EF6C00 0%,#F57C00 50%,#FF9800 100%)",
                "icon_bg": "linear-gradient(135deg,#FFF3E0 0%,#FFE0B2 100%)",
                "icon": "&#128276;",
                "tipo_bg": "#FFF3E0",
                "tipo_color": "#EF6C00",
                "tipo_border": "#FFE0B2",
                "tipo_label": "Recordatorio",
            },
            "alerta": {
                "accent_gradient": "linear-gradient(135deg,#C62828 0%,#D32F2F 50%,#EF5350 100%)",
                "icon_bg": "linear-gradient(135deg,#FBE9E7 0%,#FFCCBC 100%)",
                "icon": "&#9888;",
                "tipo_bg": "#FBE9E7",
                "tipo_color": "#C62828",
                "tipo_border": "#FFCCBC",
                "tipo_label": "Alerta",
            },
            "info": {
                "accent_gradient": "linear-gradient(135deg,#4F46E5 0%,#6366F1 50%,#818CF8 100%)",
                "icon_bg": "linear-gradient(135deg,#EEF2FF 0%,#E0E7FF 100%)",
                "icon": "&#129504;",
                "tipo_bg": "#EEF2FF",
                "tipo_color": "#4F46E5",
                "tipo_border": "#C7D2FE",
                "tipo_label": "Info",
            },
        }
        return styles.get(tipo, styles["info"])

    def _get_recipient_name(self, user, email):
        """Obtiene el nombre para el saludo: nombre real, o parte local del email, nunca vacío"""
        if user and user.nombre:
            return user.nombre
        # Fallback: parte local del email
        local_part = email.split("@")[0] if "@" in email else email
        # Limpiar y formatear
        name = local_part.replace(".", " ").replace("_", " ").replace("-", " ").title()
        return name if name else "Usuario"

    def _resolve_recipients(self, destinatario, email_individual=None):
        """Resuelve la lista de destinatarios según el tipo, aplicando filtros"""
        from apps.authentication.models import Register
        from apps.patients.models import PerfilPaciente
        
        if destinatario == "individual" and email_individual:
            try:
                user = Register.objects.get(email=email_individual)
                return [(user, email_individual)]
            except Register.DoesNotExist:
                # Usuario no registrado, usar solo el email
                return [(None, email_individual)]
        
        # Base query: usuarios activos con cuenta activa y email
        base_qs = Register.objects.filter(
            activo=True, 
            estadoCuenta="Activa"
        ).exclude(email__isnull=True).exclude(email="")
        
        if destinatario == "pacientes":
            qs = base_qs.filter(rol="paciente")
            # Excluir pacientes con notificaciones desactivadas
            pacientes_sin_notif = PerfilPaciente.objects.filter(
                prefNotificaciones="Desactivadas"
            ).values_list("idPaciente_id", flat=True)
            qs = qs.exclude(idUsuario__in=pacientes_sin_notif)
        elif destinatario == "profesionales":
            qs = base_qs.filter(rol="profesional")
        elif destinatario == "todos":
            qs = base_qs.exclude(rol="admin")  # Nunca incluir admins en "todos"
        else:
            return []
        
        return [(u, u.email) for u in qs]

    def _send_admin_notification_emails(self, notificacion_id, destinatario, email_individual, titulo, mensaje, tipo):
        """Envía emails de notificación admin a destinatarios resueltos.
        Retorna (enviados, fallidos, error_detalle)"""
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings
        from django.template.loader import render_to_string
        from apps.scheduling.models import Notificaciones
        from apps.core.utils import fmt_bogota
        from django.utils import timezone
        
        style = self._get_tipo_style(tipo)
        site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
        cta_link = f"{site_url}/aside-patient/mensajes.html"  # o panel de notificaciones
        
        # Convertir saltos de línea a <br> para HTML
        mensaje_html = mensaje.replace("\n", "<br>")
        
        recipients = self._resolve_recipients(destinatario, email_individual)
        
        if not recipients:
            return 0, 0, "No hay destinatarios válidos para esta notificación"
        
        enviados = 0
        fallidos = 0
        errores = []
        
        subject = f"PsyAI Connect \u2014 {titulo}"
        
        # Texto plano base
        text_template = """Hola {nombre},

{titulo}

{mensaje}

---
Este mensaje fue enviado por un administrador de PsyAI Connect.
Si no deseas recibir estas notificaciones, contacta con el administrador.
"""
        
        for user, email in recipients:
            try:
                nombre_destinatario = self._get_recipient_name(user, email)
                
                # Texto plano personalizado
                text_content = text_template.format(
                    nombre=nombre_destinatario,
                    titulo=titulo,
                    mensaje=mensaje
                )
                
                # HTML con template
                html_content = render_to_string('emails/notificacion_admin.html', {
                    'titulo': titulo,
                    'mensaje_html': mensaje_html,
                    'tipo': tipo,
                    'nombre_destinatario': nombre_destinatario,
                    'cta_link': cta_link,
                    **style,
                })
                
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=False)  # No silencioso para capturar errores
                enviados += 1
                
            except Exception as e:
                fallidos += 1
                errores.append(f"{email}: {str(e)}")
                logger.exception("Error enviando notificación admin a %s", email)
        
        error_detalle = "; ".join(errores) if errores else None
        return enviados, fallidos, error_detalle
