window.rendimientoCargado = false;
let _sseSource = null;
// Se pausa el stream cuando la pestaña está oculta: Chrome permite solo 6 conexiones por sitio.
let _rendimientoPausado = false;
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        if (_sseSource) {
            _sseSource.close();
            _sseSource = null;
            _rendimientoPausado = true;
        }
    } else if (_rendimientoPausado && window.rendimientoCargado) {
        _rendimientoPausado = false;
        iniciarSSEConTimeout();
    }
});
window.addEventListener('pagehide', () => {
    if (_sseSource) { _sseSource.close(); _sseSource = null; }
});
const sparklineHistory = {
    Cpu: [], Ram: [], Requests: [], Online: [], Latency: [], Queue: [],
    Server: [], Capacity: []
};
const SPARKLINE_MAX = 12;
const _sparkHashes = {};

async function cargarRendimiento() {
    window.rendimientoCargado = true;
    // verificarServidor y cargarStatsIniciales son independientes → paralelo
    await Promise.all([verificarServidor(), cargarStatsIniciales()]);
    await iniciarSSEConTimeout();
}

// Reintento con backoff exponencial (3s, 6s, 12s, 24s, tope 30s)
async function reintentar(fn, intentos = 0, maxIntentos = 5) {
    const espera = Math.min(3000 * Math.pow(2, intentos), 30000);
    await new Promise(r => setTimeout(r, espera));
    try {
        await fn();
    } catch {
        if (intentos < maxIntentos) return reintentar(fn, intentos + 1, maxIntentos);
    }
}

async function cargarStatsIniciales() {
    try {
        const res = await fetch('/api/admin/stats', { credentials: 'include' });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        if (data.success) aplicarStats(data.stats || {});
        else throw new Error(data.message || 'Sin datos');
    } catch (e) {
        console.error('Error cargando stats iniciales:', e);
        aplicarEstadoServidor('critical');
        ['rendimientoVersion','rendimientoDB','rendimientoEntorno'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = 'Error de conexión';
        });
    }
}

// Race entre primer mensaje SSE y timeout de seguridad (10s)
async function iniciarSSEConTimeout(ms = 10000) {
    if (_sseSource) return;
    // Con la pestaña oculta no se abre: se reanuda en visibilitychange.
    if (document.hidden) {
        _rendimientoPausado = true;
        return;
    }

    let timeoutId = null;

    const promesaSSE = new Promise((resolve, reject) => {
        _sseSource = new EventSource('/api/admin/stats/stream');

        _sseSource.onmessage = function(event) {
            if (timeoutId) { clearTimeout(timeoutId); timeoutId = null; }
            resolve();
            try {
                const data = JSON.parse(event.data);
                if (data.success) aplicarStats(data.stats || {});
            } catch (e) {
                console.error('Error procesando SSE:', e);
            }
        };

        _sseSource.onerror = function() {
            if (timeoutId) { clearTimeout(timeoutId); timeoutId = null; }
            _sseSource.close();
            _sseSource = null;
            reject(new Error('SSE connection error'));
        };
    });

    const promesaTimeout = new Promise((_, reject) => {
        timeoutId = setTimeout(() => {
            timeoutId = null;
            reject(new Error('SSE timeout'));
        }, ms);
    });

    try {
        await Promise.race([promesaSSE, promesaTimeout]);
    } catch (e) {
        if (_sseSource) { _sseSource.close(); _sseSource = null; }
        console.warn('SSE no disponible:', e.message);
        aplicarEstadoServidor('critical');
    }

    // Reconexión con backoff exponencial en caso de error
    if (!_sseSource && window.rendimientoCargado) {
        reintentar(async () => {
            if (!window.rendimientoCargado) return;
            await verificarServidor();
            await iniciarSSEConTimeout(ms);
        });
    }
}

async function verificarServidor() {
    const dot = document.getElementById('rendimientoServerDot');
    const estado = document.getElementById('rendimientoEstadoServidor');
    const version = document.getElementById('rendimientoVersion');
    const db = document.getElementById('rendimientoDB');
    const entorno = document.getElementById('rendimientoEntorno');
    try {
        const res = await fetch('/healthz/', { credentials: 'include' });
        if (!res.ok) throw new Error('Servidor sin respuesta');
        const data = await res.json();
        aplicarEstadoServidor('stable');
        if (dot) dot.style.background = '#4caf50';
        if (estado) estado.textContent = 'estable';
        if (version && version.textContent !== data.version) version.textContent = data.version || '--';
        if (db) {
            const dbText = data.db || data.database || (data.db_connected ? 'Conectada' : 'Sin conexion');
            if (db.textContent !== dbText) db.textContent = dbText;
        }
        if (entorno) {
            const entText = data.environment || data.entorno || 'Produccion';
            if (entorno.textContent !== entText) entorno.textContent = entText;
        }
    } catch (e) {
        aplicarEstadoServidor('critical');
        if (dot) dot.style.background = '#f44336';
        if (estado) estado.textContent = 'crítico';
        if (version) version.textContent = 'Sin conexion';
        if (db) db.textContent = 'Sin conexion';
        if (entorno) entorno.textContent = 'Sin conexion';
    }
}

function _updateText(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    const str = String(value ?? 0);
    if (el.textContent !== str) el.textContent = str;
}

function _updateClass(id, cls, add) {
    const el = document.getElementById(id);
    if (!el) return;
    if (add) { if (!el.classList.contains(cls)) el.classList.add(cls); }
    else { if (el.classList.contains(cls)) el.classList.remove(cls); }
}

function aplicarStats(stats) {
    aplicarEstadoServidor('stable');

    _updateText('rendimientoActivos', stats.usuarios_activos);
    _updateText('rendimientoSuspendidos', stats.cuentas_suspendidas);
    _updateText('rendimientoLogsHoy', stats.logs_hoy);
    _updateText('rendimientoNotificaciones', stats.notificaciones);

    _updateText('securityFailedLogins', stats.fallos_login);
    _updateText('securitySuspicious', stats.actividad_sospechosa);
    _updateText('securityBlockedIPs', stats.ips_bloqueadas);
    _updateText('securityInvalidTokens', stats.tokens_invalidos);

    _updateText('secAlertCriticas', stats.alertas_criticas);
    _updateText('secAlertWarnings', stats.alertas_warnings);
    _updateText('secAlertInfo', stats.alertas_info);
    actualizarEstadoSeguridad(stats);

    const timelineContainer = document.getElementById('securityTimelineList');
    if (timelineContainer) {
        const timelineHash = (stats.security_timeline || []).map(e => e.titulo + e.tiempo).join('|');
        if (timelineContainer._lastHash !== timelineHash) {
            timelineContainer._lastHash = timelineHash;
            if (stats.security_timeline && stats.security_timeline.length > 0) {
                timelineContainer.innerHTML = stats.security_timeline.map(evt => `
                    <div class="timeline-item premium-glow-hover">
                        <span class="timeline-dot ${escapeHtml(evt.tipo)}"></span>
                        <div>
                            <strong>${escapeHtml(evt.titulo)}</strong>
                            <div class="timeline-sub">${escapeHtml(evt.detalle || '')} \u2022 ${escapeHtml(evt.tiempo)}</div>
                        </div>
                    </div>
                `).join('');
            } else {
                timelineContainer.innerHTML = `
                    <div class="timeline-item premium-glow-hover">
                        <span class="timeline-dot stable"></span>
                        <div>
                            <strong>Sin eventos registrados</strong>
                            <div class="timeline-sub">El sistema está limpio</div>
                        </div>
                    </div>`;
            }
        }
    }

    _updateText('trafficDailyVisits', stats.visitas_hoy);
    _updateText('trafficRequestsTotal', stats.requests_total);
    _updateText('trafficHourlyActivity', stats.actividad_hora);
    _updateText('trafficUsersOnline', stats.usuarios_online);

    const topEndpointEl = document.getElementById('trafficTopEndpoint');
    if (topEndpointEl) {
        const topVal = stats.top_endpoints && stats.top_endpoints.length > 0 ? stats.top_endpoints[0].url : 'Sin datos';
        if (topEndpointEl.textContent !== topVal) topEndpointEl.textContent = topVal;
    }
    const endpointsHash = stats.top_endpoints ? stats.top_endpoints.map(e => e.url + e.porcentaje).join('|') : '';
    const endpointsList = document.getElementById('topEndpointsList');
    if (endpointsList && endpointsList._lastHash !== endpointsHash) {
        endpointsList._lastHash = endpointsHash;
        if (stats.top_endpoints && stats.top_endpoints.length > 0) {
            endpointsList.innerHTML = stats.top_endpoints.map(ep =>
                `<div class="top-endpoint"><span title="${escapeHtml(ep.url)}">${escapeHtml(ep.url)}</span><strong>${ep.porcentaje}%</strong></div>`
            ).join('');
        } else {
            endpointsList.innerHTML = '<div class="top-endpoint premium-glow-hover"><span>Sin datos aun</span><strong>-</strong></div>';
        }
    }

    const cpu = Math.round(stats.cpu ?? 0);
    const ram = Math.round(stats.ram ?? 0);
    const requests = stats.requests_minuto ?? 0;
    const online = stats.usuarios_online ?? 0;
    const latency = Math.round(stats.latencia ?? 0);
    const queue = stats.cola_tareas ?? 0;

    pushHistory('Cpu', cpu);
    pushHistory('Ram', ram);
    pushHistory('Requests', requests);
    pushHistory('Online', online);
    pushHistory('Latency', latency);
    pushHistory('Queue', queue);

    pintarMetrica('Cpu', cpu, 100, cpu);
    pintarMetrica('Ram', ram, 100, ram);
    pintarMetrica('Requests', requests, 1000, Math.min(100, requests / 10));
    pintarMetrica('Online', online, 100, online);
    pintarMetrica('Latency', latency, 1000, Math.min(100, latency / 10));
    pintarMetricaSimple('Queue', queue, 50, queue);
    _updateText('metricUpdated', new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }));

    const capacidad = Math.max(cpu, ram);
    pushHistory('Capacity', capacidad);
    aplicarEstadoElemento('metricCapacityStatus', estadoPorValor(capacidad), etiquetaEstado(capacidad));
    pintarSparkline('sparkCapacity', sparklineHistory.Capacity);
    pintarBarrasTrafico(stats);

    const diskPct = Math.round(stats.disk_pct ?? 0);
    const diskUsed = stats.disk_used_gb ?? 0;
    const diskTotal = stats.disk_total_gb ?? 0;

    const storageBar = document.getElementById('metricStorageBar');
    if (storageBar) {
        if (storageBar._lastPct !== diskPct) {
            storageBar._lastPct = diskPct;
            storageBar.style.width = `${diskPct}%`;
            _updateClass('metricStorageBar', 'stable', diskPct < 66);
            _updateClass('metricStorageBar', 'warning', diskPct >= 66 && diskPct < 82);
            _updateClass('metricStorageBar', 'critical', diskPct >= 82);
        }
    }
    const storageBadge = document.getElementById('storageStatusBadge');
    if (storageBadge) {
        const badgeText = `${diskPct}% usado`;
        if (storageBadge._lastBadge !== diskPct) {
            storageBadge._lastBadge = diskPct;
            storageBadge.textContent = badgeText;
            _updateClass('storageStatusBadge', 'stable', diskPct < 66);
            _updateClass('storageStatusBadge', 'warning', diskPct >= 66 && diskPct < 82);
            _updateClass('storageStatusBadge', 'critical', diskPct >= 82);
        }
    }
    _updateText('storageDetail', `${diskUsed} GB usados de ${diskTotal} GB totales`);
    _updateText('metricUptimeValue', stats.uptime);
    _updateText('metricUptime', stats.uptime);
}



function pintarMetrica(nombre, valor, maximo, estadoBase) {
    const id = `metric${nombre}`;
    const bar = document.getElementById(`${id}Bar`);
    const status = document.getElementById(`${id}Status`);
    const porcentaje = Math.min(100, Math.round((valor / maximo) * 100));
    const estado = estadoPorValor(porcentaje);

    _updateText(id, valor);
    if (bar && bar._lastPct !== porcentaje) {
        bar._lastPct = porcentaje;
        bar.style.width = `${porcentaje}%`;
        _updateClass(`${id}Bar`, 'stable', porcentaje < 66);
        _updateClass(`${id}Bar`, 'warning', porcentaje >= 66 && porcentaje < 82);
        _updateClass(`${id}Bar`, 'critical', porcentaje >= 82);
    }
    aplicarEstadoElemento(`${id}Status`, estado, etiquetaEstado(porcentaje));
    pintarSparkline(`spark${nombre}`, sparklineHistory[nombre] || [], estado);
    if (status) status.setAttribute('aria-label', `Estado ${etiquetaEstado(estadoBase)}`);
}

function pintarMetricaSimple(nombre, valor, maximo) {
    const bar = document.getElementById(`metric${nombre}Bar`);
    const porcentaje = Math.min(100, Math.round((valor / maximo) * 100));
    const estado = estadoPorValor(porcentaje);
    _updateText(`metric${nombre}`, valor);
    if (bar && bar._lastPct !== porcentaje) {
        bar._lastPct = porcentaje;
        bar.style.width = `${porcentaje}%`;
        _updateClass(`metric${nombre}Bar`, 'stable', porcentaje < 66);
        _updateClass(`metric${nombre}Bar`, 'warning', porcentaje >= 66 && porcentaje < 82);
        _updateClass(`metric${nombre}Bar`, 'critical', porcentaje >= 82);
    }
}

function pushHistory(key, value) {
    const arr = sparklineHistory[key];
    if (!arr) return;
    arr.push(value);
    if (arr.length > SPARKLINE_MAX) arr.shift();
}

function pintarSparkline(id, valores, estado = 'stable') {
    const el = document.getElementById(id);
    if (!el || !valores || valores.length === 0) return;
    const hash = valores.join(',');
    if (el._lastHash === hash && el._lastEstado === estado) return;
    el._lastHash = hash;
    el._lastEstado = estado;
    const max = Math.max(...valores, 1);
    el.innerHTML = valores.map(v => {
        const alto = Math.round((v / max) * 100);
        return `<span class="${estado}" style="height:${Math.max(alto, 4)}%"></span>`;
    }).join('');
}

function pintarBarrasTrafico(stats) {
    const chart = document.getElementById('trafficChart');
    if (!chart) return;
    const labels = ['Actividad/h', 'Requests', 'Visitas', 'Online', 'Top%'];
    const colores = ['#42a5f5','#7c4dff','#26c6da','#66bb6a','#ffa726'];
    const valores = [
        stats.actividad_hora ?? 0,
        stats.requests_total ?? 0,
        stats.visitas_hoy ?? 0,
        stats.usuarios_online ?? 0,
        stats.top_endpoints?.[0]?.porcentaje ?? 0
    ];
    const hash = valores.join(',');
    if (chart._lastHash === hash) return;
    chart._lastHash = hash;
    const max = Math.max(...valores, 1);
    chart.innerHTML = valores.map((v, i) => {
        const pct = Math.round((v / max) * 100);
        return `
            <div class="chart-bar">
                <div class="chart-bar-value">${v}</div>
                <div class="chart-bar-track">
                    <div class="chart-bar-fill" style="height:${pct}%;background:${colores[i]}"></div>
                </div>
                <div class="chart-bar-label">${labels[i]}</div>
            </div>
        `;
    }).join('');
}

function aplicarEstadoElemento(id, estado, texto) {
    const el = document.getElementById(id);
    if (!el) return;
    if (el.textContent !== texto) el.textContent = texto;
    _updateClass(id, 'stable', estado === 'stable');
    _updateClass(id, 'warning', estado === 'warning');
    _updateClass(id, 'critical', estado === 'critical');
}

function aplicarEstadoServidor(estado) {
    const texto = estado === 'critical' ? 'crítico' : estado === 'warning' ? 'advertencia' : 'estable';
    aplicarEstadoElemento('metricServerStatus', estado, texto);
    aplicarEstadoElemento('rendimientoEstadoServidor', estado, texto);

    const dot = document.getElementById('rendimientoServerDot');
    if (dot) {
        _updateClass('rendimientoServerDot', 'stable', estado === 'stable');
        _updateClass('rendimientoServerDot', 'warning', estado === 'warning');
        _updateClass('rendimientoServerDot', 'critical', estado === 'critical');
    }

    const serverVal = estado === 'critical' ? 'Offline' : 'Online';
    _updateText('metricServer', serverVal);

    const serverIcon = document.getElementById('metricServerIcon');
    if (serverIcon) {
        _updateClass('metricServerIcon', 'green', estado === 'stable');
        _updateClass('metricServerIcon', 'orange', estado === 'warning');
        _updateClass('metricServerIcon', 'red', estado === 'critical');
    }

    const numericMap = { stable: 5, warning: 50, critical: 95 };
    pushHistory('Server', numericMap[estado] ?? 5);
    const bar = document.getElementById('metricServerBar');
    if (bar) {
        const widthVal = estado === 'critical' ? '18%' : '100%';
        if (bar._lastServerWidth !== widthVal) {
            bar._lastServerWidth = widthVal;
            bar.style.width = widthVal;
        }
        _updateClass('metricServerBar', 'stable', estado === 'stable');
        _updateClass('metricServerBar', 'warning', estado === 'warning');
        _updateClass('metricServerBar', 'critical', estado === 'critical');
    }
    pintarSparkline('sparkServer', sparklineHistory.Server, estado);
}

function actualizarEstadoSeguridad(stats) {
    const badge = document.getElementById('securityStatusBadge');
    if (!badge) return;
    const criticas = Number(stats.alertas_criticas ?? 0);
    const warnings = Number(stats.alertas_warnings ?? 0);
    const newText = criticas > 0 ? 'Riesgo alto' : warnings > 0 ? 'Revisar accesos' : 'Sin alertas';
    const newCls = criticas > 0 ? 'error' : warnings > 0 ? 'warning' : 'security';
    if (badge.textContent === newText && badge._lastSecCls === newCls) return;
    badge.textContent = newText;
    badge._lastSecCls = newCls;
    badge.classList.remove('security', 'warning', 'error', 'info');
    badge.classList.add(newCls);
}

function estadoPorValor(valor) {
    if (valor >= 82) return 'critical';
    if (valor >= 66) return 'warning';
    return 'stable';
}

function etiquetaEstado(valor) {
    const estado = typeof valor === 'string' ? valor : estadoPorValor(valor);
    if (estado === 'critical') return 'crítico';
    if (estado === 'warning') return 'advertencia';
    return 'estable';
}

function fechaLog(valor) {
    if (!valor) return 0;
    const directa = Date.parse(valor);
    if (!Number.isNaN(directa)) return directa;
    const match = String(valor).match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?/);
    if (!match) return 0;
    const [, dia, mes, anio, hora = '00', minuto = '00'] = match;
    return new Date(Number(anio), Number(mes) - 1, Number(dia), Number(hora), Number(minuto)).getTime();
}

// Functions now delegate to shared utils module (admin.dashboard.utils.js)
// escapeHtml, csvCell, fechaLog, estadoPorValor, etiquetaEstado, setText, toggleClass are shared.
// Fallback definitions in case utils module didn't load:
if (typeof escapeHtml === 'undefined') {
    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    function csvCell(value) { return `"${String(value ?? '').replace(/"/g, '""')}"`; }
    function fechaLog(valor) {
        if (!valor) return 0;
        const directa = Date.parse(valor);
        if (!Number.isNaN(directa)) return directa;
        const match = String(valor).match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?/);
        if (!match) return 0;
        const [, dia, mes, anio, hora = '00', minuto = '00'] = match;
        return new Date(Number(anio), Number(mes) - 1, Number(dia), Number(hora), Number(minuto)).getTime();
    }
    function estadoPorValor(valor) {
        if (valor >= 82) return 'critical';
        if (valor >= 66) return 'warning';
        return 'stable';
    }
    function etiquetaEstado(valor) {
        const estado = typeof valor === 'string' ? valor : estadoPorValor(valor);
        if (estado === 'critical') return 'crítico';
        if (estado === 'warning') return 'advertencia';
        return 'estable';
    }
    function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val ?? '—'; }
    function toggleClass(id, cls, add) { const el = document.getElementById(id); if (!el) return; el.classList.toggle(cls, add); }
}
