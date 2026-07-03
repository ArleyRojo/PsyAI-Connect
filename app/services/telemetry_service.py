import time
import psutil
from collections import Counter, deque

psutil.cpu_percent(interval=None)


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
        self.SYSTEM_CHECK_INTERVAL = 3
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

        if now - self._last_system_check >= self.SYSTEM_CHECK_INTERVAL:
            self._last_cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            self._last_ram = mem.percent
            self._last_disk = psutil.disk_usage('/')
            self._last_system_check = now
        cpu = self._last_cpu
        ram = self._last_ram
        disk = self._last_disk

        if self._latency_samples:
            latencia = round(sum(self._latency_samples) / len(self._latency_samples), 1)
        else:
            latencia = 0

        uptime_secs = now - self._start_time
        uptime_str = self._format_uptime(uptime_secs)

        if disk:
            disk_used_gb = round(disk.used / (1024 ** 3), 1)
            disk_total_gb = round(disk.total / (1024 ** 3), 1)
            disk_pct = disk.percent
        else:
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
