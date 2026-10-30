import secrets
import time
import logging

import psutil
from collections import Counter, deque
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError
from django.template.loader import render_to_string

from apps.admin_panel.repositories import AdminRepository

logger = logging.getLogger(__name__)

try:
    psutil.cpu_percent(interval=None)
except Exception:
    pass

STATS_CACHE_KEY = "admin_panel:stats"
STATS_CACHE_TTL = 10


class AdminService:
    def __init__(self):
        self.repo = AdminRepository()

    def init_db(self):
        try:
            self.repo.ensure_report_columns()
        except Exception as exc:
            logger.error("Error initializing DB: %s", exc)

    def create_report_columns(self):
        self.repo.ensure_report_columns()
        return {"success": True, "message": "Columnas creadas correctamente"}, 200

    def get_stats(self, force=False):
        # Cache only DB stats; live stats (CPU, RAM, requests) must be fresh every call
        if not force:
            cached = cache.get(STATS_CACHE_KEY)
            if cached is not None:
                # Handle both old format (tuple) and new format (dict)
                if isinstance(cached, tuple) and len(cached) == 2:
                    db_stats = cached[0].get("stats", {})
                elif isinstance(cached, dict):
                    db_stats = cached
                else:
                    db_stats = self.repo.get_stats()
            else:
                db_stats = self.repo.get_stats()
                cache.set(STATS_CACHE_KEY, db_stats, STATS_CACHE_TTL)
        else:
            db_stats = self.repo.get_stats()
            cache.set(STATS_CACHE_KEY, db_stats, STATS_CACHE_TTL)

        live_stats = telemetry_service.get_live_stats()
        merged = {**live_stats, **db_stats}
        return {"success": True, "stats": merged}, 200

    def list_users(self, page=1, limit=20):
        return {"success": True, "usuarios": self.repo.list_users(page, limit)}, 200

    def get_user(self, user_id):
        usuario = self.repo.get_user(user_id)
        if not usuario:
            return {"success": False, "message": "Usuario no encontrado"}, 404
        return {"success": True, "usuario": usuario}, 200

    def create_user(self, data):
        temp_password = None
        if not data.get("contrasena"):
            temp_password = secrets.token_urlsafe(10)
            data["contrasena"] = temp_password
        try:
            self.repo.create_user(data)
        except ValueError as e:
            return {"success": False, "message": str(e)}, 400
        except IntegrityError:
            return {"success": False, "message": f"El email '{data.get('email')}' ya está registrado"}, 400
        if temp_password:
            return {"success": True, "message": "Usuario creado correctamente", "contrasena_temporal": temp_password}, 200
        return {"success": True, "message": "Usuario creado correctamente"}, 200

    def update_user(self, data):
        self.repo.update_user(data)
        return {"success": True, "message": "Usuario actualizado"}, 200

    def delete_user(self, user_id):
        self.repo.delete_user(user_id)
        return {"success": True, "message": "Usuario eliminado"}, 200

    def block_user(self, data):
        target_id = data.get("idUsuario")
        accion = data.get("accion")
        # Prevent admin from blocking themselves
        admin_id = data.get("admin_id")  # will be set by view
        if admin_id and int(admin_id) == int(target_id):
            return {"success": False, "message": "No puedes bloquearte a ti mismo"}, 400

        activo, user_info = self.repo.block_user(target_id, accion)

        # Invalidate sessions of the affected user (only when suspending)
        if activo == 0:
            # Intento rápido: filtrar sesiones cuyo session_data contenga el user_id
            try:
                candidates = Session.objects.filter(
                    session_data__contains=f'"_auth_user_id": "{target_id}"'
                )
                for session in candidates:
                    try:
                        decoded = session.get_decoded()
                        if str(decoded.get("_auth_user_id")) == str(target_id):
                            session.delete()
                    except Exception:
                        continue
            except Exception:
                pass
            # Fallback: recorrer todas las sesiones si el filtro no encontró nada
            try:
                for session in Session.objects.all():
                    try:
                        decoded = session.get_decoded()
                        if str(decoded.get("_auth_user_id") or decoded.get("idUsuario")) == str(target_id):
                            session.delete()
                    except Exception:
                        continue
            except RuntimeError:
                pass

            if user_info and user_info.get("email"):
                self._send_suspension_email(user_info["email"], user_info["nombre"], data.get("motivo", ""))

        return {"success": True, "message": f"Usuario {'suspendido' if activo == 0 else 'reestablecido'}"}, 200

    def _send_suspension_email(self, email, nombre, motivo=""):
        site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
        asunto = "PsyAI Connect — Tu cuenta ha sido suspendida"
        ctx = {"nombre": nombre, "motivo": motivo or None, "site_url": site_url}
        html = render_to_string("emails/cuenta_bloqueada.html", ctx)
        msg = EmailMultiAlternatives(asunto, f"Hola {nombre}, tu cuenta en PsyAI Connect ha sido suspendida.", to=[email])
        msg.attach_alternative(html, "text/html")
        try:
            msg.send(fail_silently=True)
        except Exception:
            logger.exception("Error enviando correo de suspensión a %s", email)

    def list_role_users(self):
        return {"success": True, "usuarios": self.repo.list_role_users()}, 200

    def change_role(self, data):
        self.repo.change_role(data.get("idUsuario"), data.get("nuevoRol"))
        return {"success": True, "message": "Rol actualizado"}, 200

    def role_history(self):
        historial = self.repo.get_role_history()
        for item in historial:
            if item.get("fecha"):
                item["fecha"] = item["fecha"].strftime("%d/%m/%Y %H:%M") if hasattr(item["fecha"], "strftime") else item["fecha"]
            item["usuario"] = item.pop("usuario_afectado", None)
            item["rolAnterior"] = item.pop("rol_anterior", None)
            item["rolNuevo"] = item.pop("rol_nuevo", None)
        return {"success": True, "historial": historial}, 200

    def notifications_feed(self):
        from datetime import datetime
        actividades = self.repo.get_notifications_feed()
        # Sort by fecha_orden (real datetime) instead of fecha (string dd/mm/YYYY)
        actividades.sort(key=lambda x: x.get("fecha_orden") or datetime.min, reverse=True)
        # Remove fecha_orden from returned items
        for item in actividades:
            item.pop("fecha_orden", None)
        
        # Get real stats from COUNT queries
        stats = self.repo.get_notification_stats()
        
        # For backward compatibility, also include the old keys
        stats["enviadas"] = stats["enviadas_hoy"]
        stats["total_historial"] = stats["total_historial"]
        
        return {
            "success": True,
            "notificaciones": actividades[:100],
            "stats": stats,
        }, 200

    def _notification_stats(self, actividades):
        total = len(actividades)
        enviadas = sum(1 for item in actividades if item.get("estado") != "pendiente")
        programadas = sum(1 for item in actividades if item.get("estado") == "pendiente")
        alcanzados = sum(
            1 for item in actividades
            if item.get("estado") != "pendiente"
            and (item.get("destinatario") or item.get("email_individual") or item.get("mensaje"))
        )
        return {
            "enviadas": enviadas,
            "programadas": programadas,
            "tasa": f"{round((enviadas / total) * 100)}%" if total else "0%",
            "alcanzados": alcanzados,
        }

    def create_notification(self, data):
        try:
            notificacion = self.repo.create_notification(data)
            # Determinar respuesta según estado
            if notificacion.estado == "enviado":
                return {"success": True, "message": "Notificación enviada correctamente", "idNotificacion": notificacion.idNotificacion}, 200
            elif notificacion.estado == "fallido":
                return {"success": False, "message": notificacion.errorDetalle or "Error enviando notificación", "idNotificacion": notificacion.idNotificacion}, 502
            else:  # pendiente
                return {"success": True, "message": "Notificación programada correctamente", "idNotificacion": notificacion.idNotificacion}, 200
        except ValueError as e:
            return {"success": False, "message": str(e)}, 400
        except Exception as e:
            logger.exception("Error creando notificación")
            return {"success": False, "message": "Error interno del servidor"}, 500

    def delete_notification(self, notification_id):
        self.repo.delete_notification(notification_id)
        return {"success": True, "message": "Notificacion eliminada"}, 200

    def get_logs(self, limit=None):
        logs = self.repo.get_logs(limit=limit)
        logs.sort(key=lambda x: x.get("fecha", ""), reverse=True)
        return {"success": True, "logs": logs}, 200

    def get_chatbot_historial(self, nivel="", search=""):
        def _serialize_fecha(valor):
            if valor is None:
                return None
            if hasattr(valor, "isoformat"):
                return valor.isoformat()
            return str(valor)

        try:
            rows = self.repo.get_chatbot_historial_rows()
            stats = self.repo.get_chatbot_historial_stats()
        except Exception as e:
            estr = str(e)
            if "1146" in estr or "doesn't exist" in estr:
                return {
                    "success": False,
                    "message": "La vista vistahistorialchatbot no existe en la BD. "
                               "Corre las migraciones: python manage.py migrate",
                    "pacientes": [],
                    "stats": {"total": 0, "alto": 0, "medio": 0, "bajo": 0},
                }, 200
            return {"success": False, "message": "Error al cargar historial del chatbot"}, 500

        pacientes_map = {}
        for row in rows:
            key = row.get("idPaciente") or row["nombre"]
            if key not in pacientes_map:
                pacientes_map[key] = {
                    "nombre": row["nombre"] or "Paciente",
                    "idPaciente": row.get("idPaciente"),
                    "total_mensajes": 0,
                    "ultimo_mensaje": None,
                    "nivel_max": "Bajo",
                    "mensajes": [],
                }
            p = pacientes_map[key]
            p["total_mensajes"] += 1
            rnivel = row.get("nivelEmocionalDetectado", "")
            if rnivel == "Alto":
                p["nivel_max"] = "Alto"
            elif rnivel == "Medio" and p["nivel_max"] != "Alto":
                p["nivel_max"] = "Medio"
            p["mensajes"].append({
                "mensajeUsuario": row.get("mensajeUsuario"),
                "respuestaChatbot": row.get("respuestaChatbot"),
                "nivelEmocionalDetectado": rnivel,
                "fecha": _serialize_fecha(row.get("fecha")),
            })
            fecha = row.get("fecha")
            if fecha:
                fecha_str = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)
                if p["ultimo_mensaje"] is None or fecha_str > p["ultimo_mensaje"]:
                    p["ultimo_mensaje"] = fecha_str

        pacientes = list(pacientes_map.values())
        if nivel:
            pacientes = [p for p in pacientes if p["nivel_max"] == nivel]
        if search:
            s = search.lower()
            pacientes = [p for p in pacientes if s in p["nombre"].lower()]

        return {"success": True, "pacientes": pacientes, "stats": stats}, 200


class TelemetryService:
    def __init__(self):
        self._start_time = time.time()
        self._requests_total = 0
        self._visitas_hoy = set()
        self._visitas_fecha = time.strftime("%Y-%m-%d")
        self._endpoints = Counter()
        self._requests_history = deque(maxlen=3600)
        self._active_clients = {}
        self._active_users = {}
        self._latency_samples = deque(maxlen=100)
        self._active_sse = {}
        self._version = 0
        self._trim_counter = 0
        self._last_system_check = 0
        self._last_cpu = 0
        self._last_ram = 0
        self._last_disk = None
        self.SYSTEM_CHECK_INTERVAL = 2
        self._security = {
            "fallos_login": 0,
            "actividad_sospechosa": 0,
            "ips_bloqueadas": 0,
            "tokens_invalidos": 0,
        }
        self._security_events = deque(maxlen=10)

    def _trim_endpoints(self, max_entries=20):
        if len(self._endpoints) > max_entries:
            self._endpoints = Counter(dict(self._endpoints.most_common(max_entries)))

    def _normalize_ip(self, ip):
        if not ip:
            return '127.0.0.1'
        ip = ip.strip().lower()
        if ip in ('::1', '0.0.0.0', 'localhost'):
            return '127.0.0.1'
        return ip

    def track_request(self, ip, endpoint, user_id=None):
        self._trim_counter += 1
        ip = self._normalize_ip(ip)
        today = time.strftime("%Y-%m-%d")
        if today != self._visitas_fecha:
            self._visitas_hoy.clear()
            self._visitas_fecha = today
        self._requests_total += 1
        self._version += 1

        parts = endpoint.split('/')
        if len(parts) > 3 and parts[-1].isdigit():
            parts[-1] = '*'
            endpoint = '/'.join(parts)

        self._endpoints[endpoint] += 1
        self._visitas_hoy.add(ip)

        now = time.time()
        self._requests_history.append(now)
        self._active_clients[ip] = now

        if user_id:
            self._active_users[user_id] = now

        if self._trim_counter >= 1000:
            self._trim_counter = 0
            self._trim_endpoints()

    def sse_connected(self, ip):
        ip = self._normalize_ip(ip)
        now = time.time()
        if ip in self._active_sse:
            self._active_sse[ip]["count"] += 1
            self._active_sse[ip]["ts"] = now
        else:
            self._active_sse[ip] = {"count": 1, "ts": now}

    def sse_disconnected(self, ip):
        ip = self._normalize_ip(ip)
        entry = self._active_sse.get(ip)
        if entry:
            entry["count"] -= 1
            if entry["count"] <= 0:
                del self._active_sse[ip]

    def sse_heartbeat(self, ip):
        ip = self._normalize_ip(ip)
        entry = self._active_sse.get(ip)
        if entry:
            entry["ts"] = time.time()

    def remove_user(self, user_id):
        self._active_users.pop(user_id, None)
        self._version += 1

    def get_active_user_ids(self):
        now = time.time()
        stale = [uid for uid, ts in self._active_users.items() if ts < now - 300]
        for uid in stale:
            del self._active_users[uid]
        return list(self._active_users.keys())

    def track_latency(self, duration_ms):
        self._latency_samples.append(duration_ms)
        self._version += 1

    def track_security_event(self, event_type, detail=None):
        if event_type in self._security:
            self._security[event_type] += 1
        self._version += 1

        label_map = {
            "fallos_login": "Intento de login fallido",
            "actividad_sospechosa": "Actividad sospechosa detectada",
            "ips_bloqueadas": "IP bloqueada por rate limit",
            "tokens_invalidos": "Token inválido detectado",
        }
        dot_map = {
            "fallos_login": "warning",
            "actividad_sospechosa": "error",
            "ips_bloqueadas": "security",
            "tokens_invalidos": "security",
        }

        self._security_events.appendleft({
            "titulo": label_map.get(event_type, event_type),
            "detalle": detail or "",
            "tipo": dot_map.get(event_type, "warning"),
            "timestamp": time.time(),
        })

    def _format_uptime(self, seconds):
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        mins = int((seconds % 3600) // 60)
        if days > 0:
            return f"{days}d {hours}h {mins}m"
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    def _format_time_ago(self, ts):
        diff = int(time.time() - ts)
        if diff < 60:
            return f"{diff} seg atrás"
        if diff < 3600:
            return f"{diff // 60} min atrás"
        return f"{diff // 3600}h atrás"

    def get_live_stats(self):
        now = time.time()
        cpu = 0
        ram = 0
        disk = None
        disk_pct = 0

        try:
            if now - self._last_system_check >= self.SYSTEM_CHECK_INTERVAL:
                self._last_cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                self._last_ram = mem.percent
                self._last_disk = psutil.disk_usage('/')
                self._last_system_check = now
        except Exception:
            pass

        cpu = self._last_cpu
        ram = self._last_ram
        disk = self._last_disk

        if self._latency_samples:
            latencia = round(sum(self._latency_samples) / len(self._latency_samples), 1)
        else:
            latencia = 0

        uptime_secs = now - self._start_time
        uptime_str = self._format_uptime(uptime_secs)

        try:
            if disk:
                disk_used_gb = round(disk.used / (1024 ** 3), 1)
                disk_total_gb = round(disk.total / (1024 ** 3), 1)
                disk_pct = disk.percent
            else:
                disk_used_gb = disk_total_gb = disk_pct = 0
        except Exception:
            disk_used_gb = disk_total_gb = disk_pct = 0

        stale = [ip for ip, data in self._active_sse.items() if data["ts"] < now - 30]
        for ip in stale:
            del self._active_sse[ip]
        stale_clients = [ip for ip, ts in self._active_clients.items() if ts < now - 300]
        for ip in stale_clients:
            del self._active_clients[ip]
        online = len(set(self._active_sse.keys()) | set(self._active_clients.keys()))
        stale_users = [uid for uid, ts in self._active_users.items() if ts < now - 300]
        for uid in stale_users:
            del self._active_users[uid]
        actividad_hora = len(self._requests_history)
        requests_minuto = sum(1 for ts in self._requests_history if ts >= now - 60)

        top = self._endpoints.most_common(4)
        top_endpoints = []
        for url, count in top:
            pct = int((count / self._requests_total) * 100) if self._requests_total > 0 else 0
            top_endpoints.append({"url": url, "count": count, "porcentaje": pct})

        criticas = self._security["ips_bloqueadas"] + self._security["actividad_sospechosa"]
        warnings = self._security["fallos_login"]
        info_count = self._security["tokens_invalidos"]

        timeline = []
        for evt in self._security_events:
            timeline.append({
                "titulo": evt["titulo"],
                "detalle": evt["detalle"],
                "tipo": evt["tipo"],
                "tiempo": self._format_time_ago(evt["timestamp"]),
            })

        return {
            "cpu": cpu,
            "ram": ram,
            "latencia": latencia,
            "uptime": uptime_str,
            "uptime_secs": int(uptime_secs),
            "disk_used_gb": disk_used_gb,
            "disk_total_gb": disk_total_gb,
            "disk_pct": disk_pct,
            "requests_total": self._requests_total,
            "requests_minuto": requests_minuto,
            "visitas_hoy": len(self._visitas_hoy),
            "actividad_hora": actividad_hora,
            "usuarios_online": online,
            "top_endpoints": top_endpoints,
            "fallos_login": self._security["fallos_login"],
            "actividad_sospechosa": self._security["actividad_sospechosa"],
            "ips_bloqueadas": self._security["ips_bloqueadas"],
            "tokens_invalidos": self._security["tokens_invalidos"],
            "alertas_criticas": criticas,
            "alertas_warnings": warnings,
            "alertas_info": info_count,
            "security_timeline": timeline,
            "active_user_ids": list(self._active_users.keys()),
        }


telemetry_service = TelemetryService()

track_request = telemetry_service.track_request
track_latency = telemetry_service.track_latency
track_security_event = telemetry_service.track_security_event
get_active_user_ids = telemetry_service.get_active_user_ids
remove_user = telemetry_service.remove_user
sse_connected = telemetry_service.sse_connected
sse_disconnected = telemetry_service.sse_disconnected
sse_heartbeat = telemetry_service.sse_heartbeat
_normalize_ip = telemetry_service._normalize_ip
