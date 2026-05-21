import time
import psutil
from collections import Counter, deque

# ── Inicializar CPU (la primera llamada siempre devuelve 0) ──
psutil.cpu_percent(interval=None)

# ── Almacenamiento en memoria ──
_start_time = time.time()
_requests_total = 0
_visitas_hoy = set()
_visitas_fecha = time.strftime("%Y-%m-%d")
_endpoints = Counter()
_requests_history = deque()
_active_clients = {}
_latency_samples = deque(maxlen=100)
_active_sse = {}  # ip -> {"count": int, "ts": float}
_version = 0  # Se incrementa con cada cambio para SSE

# ── Caché de psutil para no llamarlo en cada get_live_stats ──
_last_system_check = 0
_last_cpu = 0
_last_ram = 0
_last_disk = None
SYSTEM_CHECK_INTERVAL = 3  # segundos

# Seguridad
_security = {
    "fallos_login": 0,
    "actividad_sospechosa": 0,
    "ips_bloqueadas": 0,
    "tokens_invalidos": 0,
}

# Timeline de eventos de seguridad (últimos 10)
_security_events = deque(maxlen=10)


def _normalize_ip(ip):
    if not ip:
        return '127.0.0.1'
    ip = ip.strip().lower()
    if ip == '::1' or ip == '0.0.0.0' or ip == 'localhost':
        return '127.0.0.1'
    return ip

def track_request(ip, endpoint):
    global _requests_total, _version, _visitas_fecha
    ip = _normalize_ip(ip)
    today = time.strftime("%Y-%m-%d")
    if today != _visitas_fecha:
        _visitas_hoy.clear()
        _visitas_fecha = today
    _requests_total += 1
    _version += 1

    parts = endpoint.split('/')
    if len(parts) > 3 and parts[-1].isdigit():
        parts[-1] = '*'
        endpoint = '/'.join(parts)

    _endpoints[endpoint] += 1
    _visitas_hoy.add(ip)

    now = time.time()
    _requests_history.append(now)
    _active_clients[ip] = now

    # Limpiar historial mayor a 1 hora
    while _requests_history and _requests_history[0] < now - 3600:
        _requests_history.popleft()


def sse_connected(ip):
    ip = _normalize_ip(ip)
    now = time.time()
    if ip in _active_sse:
        _active_sse[ip]["count"] += 1
        _active_sse[ip]["ts"] = now
    else:
        _active_sse[ip] = {"count": 1, "ts": now}

def sse_disconnected(ip):
    ip = _normalize_ip(ip)
    entry = _active_sse.get(ip)
    if entry:
        entry["count"] -= 1
        if entry["count"] <= 0:
            del _active_sse[ip]

def sse_heartbeat(ip):
    ip = _normalize_ip(ip)
    entry = _active_sse.get(ip)
    if entry:
        entry["ts"] = time.time()

def track_latency(duration_ms):
    global _version
    _latency_samples.append(duration_ms)
    _version += 1


def track_security_event(event_type, detail=None):
    global _version
    if event_type in _security:
        _security[event_type] += 1
    _version += 1

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

    _security_events.appendleft({
        "titulo": label_map.get(event_type, event_type),
        "detalle": detail or "",
        "tipo": dot_map.get(event_type, "warning"),
        "timestamp": time.time(),
    })


def _format_uptime(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    mins = int((seconds % 3600) // 60)
    if days > 0:
        return f"{days}d {hours}h {mins}m"
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def _format_time_ago(ts):
    diff = int(time.time() - ts)
    if diff < 60:
        return f"{diff} seg atrás"
    if diff < 3600:
        return f"{diff // 60} min atrás"
    return f"{diff // 3600}h atrás"


def get_live_stats():
    global _last_system_check, _last_cpu, _last_ram, _last_disk
    now = time.time()

    # ── Sistema (con caché para evitar psutil en cada llamada) ──
    if now - _last_system_check >= SYSTEM_CHECK_INTERVAL:
        _last_cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        _last_ram = mem.percent
        _last_disk = psutil.disk_usage('/')
        _last_system_check = now
    cpu = _last_cpu
    ram = _last_ram
    disk = _last_disk

    # Latencia promedio real (ms)
    if _latency_samples:
        latencia = round(sum(_latency_samples) / len(_latency_samples), 1)
    else:
        latencia = 0

    # Uptime
    uptime_secs = now - _start_time
    uptime_str = _format_uptime(uptime_secs)

    # Almacenamiento (usar valores cacheados)
    if disk:
        disk_used_gb = round(disk.used / (1024 ** 3), 1)
        disk_total_gb = round(disk.total / (1024 ** 3), 1)
        disk_pct = disk.percent
    else:
        disk_used_gb = disk_total_gb = disk_pct = 0

    # ── Tráfico (limpiar solo cada ~10s desde la última limpieza) ──
    stale = [ip for ip, data in _active_sse.items() if data["ts"] < now - 30]
    for ip in stale:
        del _active_sse[ip]
    stale_clients = [ip for ip, ts in _active_clients.items() if ts < now - 300]
    for ip in stale_clients:
        del _active_clients[ip]
    online = len(set(_active_sse.keys()) | set(_active_clients.keys()))
    actividad_hora = len(_requests_history)
    requests_minuto = sum(1 for ts in _requests_history if ts >= now - 60)

    # Top endpoints (solo recalcular si hay cambios)
    top = _endpoints.most_common(4)
    top_endpoints = []
    for url, count in top:
        pct = int((count / _requests_total) * 100) if _requests_total > 0 else 0
        top_endpoints.append({"url": url, "count": count, "porcentaje": pct})

    # ── Seguridad - conteos por severidad ──
    criticas = _security["ips_bloqueadas"] + _security["actividad_sospechosa"]
    warnings = _security["fallos_login"]
    info_count = _security["tokens_invalidos"]

    # Timeline
    timeline = []
    for evt in _security_events:
        timeline.append({
            "titulo": evt["titulo"],
            "detalle": evt["detalle"],
            "tipo": evt["tipo"],
            "tiempo": _format_time_ago(evt["timestamp"]),
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
        "requests_total": _requests_total,
        "requests_minuto": requests_minuto,
        "visitas_hoy": len(_visitas_hoy),
        "actividad_hora": actividad_hora,
        "usuarios_online": online,
        "top_endpoints": top_endpoints,
        "fallos_login": _security["fallos_login"],
        "actividad_sospechosa": _security["actividad_sospechosa"],
        "ips_bloqueadas": _security["ips_bloqueadas"],
        "tokens_invalidos": _security["tokens_invalidos"],
        "alertas_criticas": criticas,
        "alertas_warnings": warnings,
        "alertas_info": info_count,
        "security_timeline": timeline,
    }
