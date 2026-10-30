const API = '';
let _statsSSE = null;
let _logsSSE = null;
let _lastStats = {};

document.addEventListener('DOMContentLoaded', async () => {
    // verificarSesionAdmin primero: si no es admin redirige y el resto sobra
    await verificarSesionAdmin();
    // cargarStats y cargarActividadReciente son independientes → paralelo
    await Promise.all([cargarStats(), cargarActividadReciente()]);
    conectarSSE();
});

function conectarSSE() {
    _statsSSE = new SSEConnection('/api/admin/stats/stream', (data) => {
        if (data.success) {
            _lastStats = data.stats || {};
            aplicarStatsLive(data.stats);
        }
    }, () => verificarServidor());
    _statsSSE.connect();

    _logsSSE = new SSEConnection('/api/admin/logs/stream', (data) => {
        if (data.success && data.logs && data.logs.length > 0) {
            const lista = document.getElementById('listaActividad');
            if (lista) {
                const recientes = data.logs.slice(0, 8);
                lista.innerHTML = recientes.map(log => buildItem(log)).join('');
            }
        }
    });
    _logsSSE.connect();
}

async function verificarSesionAdmin() {
    try {
        const res  = await fetch(`${API}/api/session`, { credentials: 'include' });
        if (res.status === 401) { window.location.href = '../login.html'; return; }
        const data = await res.json();
        if (!data.success || data.usuario?.rol !== 'admin') {
            window.location.href = '../login.html';
        } else {
            const saludo = document.querySelector('.user-info .fw-semibold');
            if (saludo) saludo.textContent = `Hola, ${data.usuario.nombre}`;
        }
    } catch (e) {}
}

async function verificarServidor() {
    try {
        const res = await fetch('/healthz/', { credentials: 'include' });
        if (!res.ok) throw new Error('Sin respuesta');
        const data = await res.json();
        aplicarEstadoServidor('stable');
        setText('metricServerStatus', 'estable');
        if (data.version) setText('metricServerVersion', data.version);
        if (data.environment || data.entorno) setText('metricServerEnv', data.environment || data.entorno);
    } catch (e) {
        aplicarEstadoServidor('critical');
        setText('metricServerStatus', 'crítico');
    }
}

async function cargarStats() {
    try {
        const res  = await fetch(`${API}/api/admin/stats`, { credentials: 'include' });
        const data = await res.json();
        if (!data.success) return;
        _lastStats = data.stats || {};
        aplicarStatsIniciales(data.stats);
    } catch (e) {
        console.error('No se pudo cargar stats:', e);
    }
}

function aplicarStatsIniciales(stats) {
    quitarSkeletons();
    setText('statTotal', stats.total_usuarios);
    setText('statActivos', stats.usuarios_activos);
    setText('statNotifs', stats.notificaciones);
    setText('statSuspendidos', stats.cuentas_suspendidas ?? stats.cuentas_bloqueadas);
    setText('metricCpu', stats.cpu ?? '—');
    setText('metricRam', stats.ram ?? '—');
    setText('metricDisk', stats.disk_pct ?? '—');
    setText('metricUptime', stats.uptime ?? '—');
    setText('metricRequests', stats.requests_minuto ?? '—');
    setText('metricOnline', stats.usuarios_online ?? '—');
    setText('metricLatency', stats.latencia ?? '—');
    setText('metricPendientes', stats.citas_pendientes ?? '—');
    setText('metricLogsHoy', stats.logs_hoy ?? '—');

    document.querySelectorAll('.progress-fill').forEach(el => {
        const pct = parseInt(el.dataset.pct || '0', 10);
        el.style.width = `${pct}%`;
    });

    if (typeof initCharts === 'function') initCharts(stats);
    // verificarServidor y cargarUsuariosOnline son independientes → paralelo
    Promise.all([
        typeof verificarServidor === 'function' ? verificarServidor() : Promise.resolve(),
        cargarUsuariosOnline(),
    ]).catch(() => {});
}

async function cargarUsuariosOnline() {
    try {
        const res = await fetch('/api/admin/online', { credentials: 'include' });
        const data = await res.json();
        if (!data.success) return;
        const container = document.getElementById('onlineUsersList');
        const badge = document.getElementById('onlineUsersBadge');
        if (badge) badge.textContent = data.total || 0;
        if (!container) return;
        if (!data.usuarios || data.usuarios.length === 0) {
            container.innerHTML = '<div class="text-muted small py-2">No hay usuarios conectados.</div>';
            return;
        }
        container.innerHTML = data.usuarios.map(u => `
            <div class="d-flex align-items-center gap-2 py-1">
                <span class="server-dot stable" style="width:8px;height:8px;"></span>
                <span class="fw-semibold small">${escapeHtml(u.nombre)}</span>
                <small class="text-muted">${escapeHtml(u.rol)}</small>
            </div>
        `).join('');
    } catch (e) {
        console.error('Error cargando usuarios online:', e);
    }
}

function aplicarStatsLive(stats) {
    setText('statTotal', stats.total_usuarios);
    setText('statActivos', stats.usuarios_activos);
    setText('statNotifs', stats.notificaciones);
    setText('statSuspendidos', stats.cuentas_suspendidas ?? stats.cuentas_bloqueadas);
    setText('metricCpu', stats.cpu ?? '—');
    setText('metricRam', stats.ram ?? '—');
    setText('metricDisk', stats.disk_pct ?? '—');
    setText('metricUptime', stats.uptime ?? '—');
    setText('metricRequests', stats.requests_minuto ?? '—');
    setText('metricOnline', stats.usuarios_online ?? '—');
    setText('metricLatency', stats.latencia ?? '—');
    setText('metricPendientes', stats.citas_pendientes ?? '—');
    setText('metricLogsHoy', stats.logs_hoy ?? '—');
    setText('metricServerTime', new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }));

    document.querySelectorAll('.progress-fill[data-pct]').forEach(el => {
        const pct = parseInt(el.dataset.pct || '0', 10);
        el.style.width = `${pct}%`;
        toggleClass(el, 'warning', pct >= 66 && pct < 82);
        toggleClass(el, 'critical', pct >= 82);
    });

    if (typeof updateCharts === 'function') updateCharts(stats);
}

function quitarSkeletons() {
    document.querySelectorAll('.skeleton').forEach(el => el.classList.remove('skeleton'));
}

async function cargarActividadReciente() {
    const lista = document.getElementById('listaActividad');
    if (!lista) return;
    try {
        const res  = await fetch(`${API}/api/admin/logs`, { credentials: 'include' });
        const data = await res.json();
        if (!data.success || !data.logs || data.logs.length === 0) {
            lista.innerHTML = '<li class="text-muted">No hay actividad reciente.</li>';
            return;
        }
        const recientes = data.logs.slice(0, 8);
        lista.innerHTML = recientes.map(log => buildItem(log)).join('');
    } catch (e) {
        console.error('Error cargando actividad:', e);
        lista.innerHTML = '<li class="text-danger"><i class="fas fa-exclamation-circle me-2"></i>Error al cargar actividad.</li>';
    }
}

function filterActivity() {
    const query = document.getElementById('activityFilter')?.value?.toLowerCase() || '';
    const items = document.querySelectorAll('#listaActividad li');
    items.forEach(li => {
        const text = li.textContent.toLowerCase();
        li.style.display = text.includes(query) ? '' : 'none';
    });
}

function exportStatsCSV() {
    const s = _lastStats || {};
    exportCSV('admin-stats.csv',
        ['Metrica', 'Valor'],
        Object.entries(s).filter(([k]) => !['security_timeline', 'top_endpoints', 'actividad_reciente'].includes(k) && typeof s[k] !== 'object')
            .map(([k, v]) => [k, String(v ?? '')])
    );
}

function exportActivityCSV() {
    const items = document.querySelectorAll('#listaActividad li');
    const rows = Array.from(items).map(li => {
        const text = li.textContent.trim();
        return [csvCell(text)];
    });
    exportCSV('admin-actividad.csv', ['Actividad'], rows);
}

function buildItem(log) {
    const { icono, color } = getIconoOrigen(log.origen, log.accion);
    const accionFormateada  = formatearAccion(log.accion);
    const detalle           = log.detalle ? `<span class="text-muted ms-1">— ${escapeHtml(log.detalle)}</span>` : '';
    const autor             = log.administrador ? `<small class="text-muted">${escapeHtml(log.administrador)}</small>` : '';
    return `<li class="d-flex align-items-start gap-3 py-2 border-bottom border-light">
        <div class="actividad-icono rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
             style="width:36px;height:36px;background:${color}15;">
            <i class="fas ${icono}" style="color:${color};font-size:.85rem;"></i>
        </div>
        <div class="flex-grow-1 lh-sm">
            <div class="fw-semibold" style="font-size:.875rem;">${accionFormateada}${detalle}</div>
            <div class="d-flex gap-2 align-items-center mt-1">
                ${autor}
                <span class="badge rounded-pill" style="background:${color}18;color:${color};font-size:.68rem;">${etiquetaOrigen(log.origen)}</span>
                <small class="text-muted ms-auto">${escapeHtml(log.fecha)}</small>
            </div>
        </div>
    </li>`;
}

function getIconoOrigen(origen, accion) {
    const a = (accion || '').toLowerCase();
    if (a.includes('login'))    return { icono: 'fa-sign-in-alt',  color: '#2196F3' };
    if (a.includes('eliminar') || a.includes('borrar'))
                                return { icono: 'fa-trash',         color: '#f44336' };
    if (a.includes('bloquear') || a.includes('suspend'))
                                return { icono: 'fa-ban',           color: '#FF5722' };
    if (a.includes('crear') || a.includes('nuevo') || a.includes('registro'))
                                return { icono: 'fa-plus-circle',   color: '#4CAF50' };
    if (a.includes('editar') || a.includes('actualiz') || a.includes('modif'))
                                return { icono: 'fa-edit',          color: '#FF9800' };
    if (a.includes('rol'))      return { icono: 'fa-user-shield',   color: '#9C27B0' };
    if (a.includes('notif') || a.includes('envi'))
                                return { icono: 'fa-bell',          color: '#00BCD4' };
    if (a.includes('cita'))     return { icono: 'fa-calendar-check',color: '#3F51B5' };
    if (a.includes('diagnos'))  return { icono: 'fa-file-medical',  color: '#009688' };
    const map = {
        admin:        { icono: 'fa-user-shield',    color: '#1565c0' },
        auditoria:    { icono: 'fa-sign-in-alt',    color: '#607D8B' },
        notificacion: { icono: 'fa-bell',           color: '#607D8B' },
        profesional:  { icono: 'fa-user-md',        color: '#1565c0' },
        paciente:     { icono: 'fa-user',           color: '#1565c0' },
        sistema:      { icono: 'fa-cog',            color: '#607D8B' },
    };
    return map[origen] || { icono: 'fa-circle', color: '#9E9E9E' };
}

function etiquetaOrigen(origen) {
    const map = {
        admin:        'Admin',
        auditoria:    'Acceso',
        notificacion: 'Notificación',
        profesional:  'Profesional',
        paciente:     'Paciente',
        sistema:      'Sistema',
    };
    return map[origen] || capitalizar(origen || '');
}

function formatearAccion(accion) {
    if (!accion) return '—';
    const s = capitalizar(accion);
    return s.length > 60 ? s.slice(0, 57) + '…' : s;
}

function capitalizar(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

function aplicarEstadoServidor(estado) {
    const dot = document.getElementById('metricServerDot');
    toggleClass('metricServerDot', 'stable', estado === 'stable');
    toggleClass('metricServerDot', 'warning', estado === 'warning');
    toggleClass('metricServerDot', 'critical', estado === 'critical');
    if (dot) {
        if (estado === 'stable') dot.style.background = '#4caf50';
        else if (estado === 'warning') dot.style.background = '#ff9800';
        else dot.style.background = '#f44336';
    }
}