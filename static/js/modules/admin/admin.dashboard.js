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
                const recientes = data.logs.slice(0, 5);
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
    pintarDashboard(stats);
    if (typeof initCharts === 'function') initCharts(stats);
    // verificarServidor y cargarUsuariosOnline son independientes → paralelo
    Promise.all([
        typeof verificarServidor === 'function' ? verificarServidor() : Promise.resolve(),
        cargarUsuariosOnline(),
    ]).catch(() => {});
}

function aplicarStatsLive(stats) {
    pintarDashboard(stats);
    setText('metricServerTime', new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }));
    if (typeof updateCharts === 'function') updateCharts(stats);
}

// ── Rediseño del dashboard (propuesta A "Resumen claro") ───────────────────
const UMBRAL_AVISO = 75;
const UMBRAL_CRITICO = 90;
const ZONA = 'America/Bogota';

function numero(v) {
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
}

function suma(lista) {
    return (lista || []).reduce((a, b) => a + numero(b), 0);
}

function plural(n, uno, varios) {
    return `${n} ${n === 1 ? uno : varios}`;
}

function horaActualColombia() {
    return Number(new Intl.DateTimeFormat('en-US', { hour: 'numeric', hourCycle: 'h23', timeZone: ZONA }).format(new Date()));
}

function nombreHora(h) {
    if (h === 0) return '12 a. m.';
    if (h < 12) return `${h} a. m.`;
    if (h === 12) return '12 m.';
    return `${h - 12} p. m.`;
}

function pintarChip(id, texto, tono) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = texto;
    el.className = `adm-chip adm-chip--${tono}`;
}

function pintarDelta(id, texto, tono) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = texto;
    el.classList.toggle('adm-kpi__delta--aviso', tono === 'aviso');
}

function pintarSparkline(id, serie) {
    const el = document.getElementById(id);
    if (!el) return;
    const datos = (serie || []).map(numero);
    if (datos.length < 2) { el.innerHTML = ''; return; }
    const max = Math.max(...datos), min = Math.min(...datos);
    const puntos = datos.map((v, i) => {
        const x = (i * 120 / (datos.length - 1)).toFixed(1);
        const y = (max === min ? 31 : 32 - (v - min) / (max - min) * 26).toFixed(1);
        return `${x},${y}`;
    }).join(' ');
    el.innerHTML = `<svg viewBox="0 0 120 36" preserveAspectRatio="none" focusable="false">
        <polyline class="adm-spark__area" points="0,36 ${puntos} 120,36"></polyline>
        <polyline class="adm-spark__linea" points="${puntos}"></polyline></svg>`;
    el.title = datos.join(' · ');
}

function pintarHoras(horas) {
    const cont = document.getElementById('barrasHoras');
    if (!cont) return;
    const datos = Array.from({ length: 24 }, (_, i) => numero((horas || [])[i]));
    if (cont.children.length !== 24) {
        cont.innerHTML = datos.map(() => '<div class="adm-barra"></div>').join('');
    }
    const ahora = horaActualColombia();
    const max = Math.max(1, ...datos);
    datos.forEach((v, i) => {
        const barra = cont.children[i];
        const futura = i > ahora;
        barra.style.height = futura ? '0px' : `${v ? Math.max(4, Math.round(v / max * 170)) : 2}px`;
        barra.classList.toggle('adm-barra--ahora', i === ahora);
        barra.classList.toggle('adm-barra--futura', futura);
        barra.title = futura ? `${nombreHora(i)} · aún no` : `${nombreHora(i)} · ${plural(v, 'acción', 'acciones')}`;
    });
    const total = suma(datos);
    const pico = datos.indexOf(Math.max(...datos));
    const resumen = total
        ? `${plural(total, 'acción registrada', 'acciones registradas')} hoy · pico a las ${nombreHora(pico)} (${datos[pico]})`
        : 'Aún no hay acciones registradas hoy';
    setText('resumenHoras', resumen);
    cont.setAttribute('aria-label', `Acciones registradas por hora hoy. ${resumen}.`);
}

function pintarMedidor(sufijo, valor, nota) {
    const v = Math.max(0, Math.min(100, numero(valor)));
    const tono = v >= UMBRAL_CRITICO ? 'critico' : v >= UMBRAL_AVISO ? 'aviso' : 'normal';
    setText(`metric${sufijo}`, valor == null ? '—' : `${Math.round(v)} %`);
    const barra = document.getElementById(`metric${sufijo}Bar`);
    if (barra) {
        barra.style.width = `${v}%`;
        barra.dataset.tono = tono;
    }
    const valorEl = document.getElementById(`metric${sufijo}`);
    if (valorEl) valorEl.dataset.tono = tono;
    const estado = tono === 'critico' ? 'Crítico' : tono === 'aviso' ? 'Atención' : 'Normal';
    setText(`nota${sufijo}`, `${estado} · ${nota}`);
}

function pintarEndpoints(lista) {
    const cont = document.getElementById('listaEndpoints');
    if (!cont) return;
    const items = (lista || []).filter(e => e && e.url);
    if (!items.length) {
        cont.innerHTML = '<p class="adm-vacio">Aún no hay peticiones registradas.</p>';
        return;
    }
    const max = Math.max(1, ...items.map(e => numero(e.count)));
    cont.innerHTML = items.map(e => `
        <div class="adm-endpoint">
            <div class="adm-endpoint__fila"><code title="${escapeHtml(e.url)}">${escapeHtml(e.url)}</code><strong>${numero(e.count).toLocaleString('es-CO')}</strong></div>
            <div class="adm-endpoint__pista"><div class="adm-endpoint__barra" style="width:${Math.round(numero(e.count) / max * 100)}%"></div></div>
        </div>`).join('');
}

function pintarCuentas(total, activas, suspendidas) {
    const otras = Math.max(0, total - activas - suspendidas);
    const pct = total ? Math.round(activas / total * 100) : 0;
    setText('resumenCuentas', `${plural(total, 'cuenta', 'cuentas')} · ${pct} % activas`);
    setText('cntActivas', activas);
    setText('statSuspendidos', suspendidas);
    setText('cntOtras', otras);
    [['segActivas', activas], ['segSuspendidas', suspendidas], ['segOtras', otras]].forEach(([id, n]) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.style.flexGrow = n;
        el.style.display = n ? '' : 'none';
    });
    const barra = document.getElementById('barraCuentas');
    if (barra) barra.setAttribute('aria-label', `${activas} activas, ${suspendidas} suspendidas, ${otras} inactivas o sin verificar`);
}

function pintarDashboard(stats) {
    const s = stats || {};
    quitarSkeletons();
    const t = s.tendencias || {};
    const total = numero(s.total_usuarios);
    const activos = numero(s.usuarios_activos);
    const suspendidas = numero(s.cuentas_suspendidas ?? s.cuentas_bloqueadas);

    // Usuarios activos
    setText('statActivos', activos);
    setText('statTotal', total);
    const pct = total ? Math.round(activos / total * 100) : 0;
    pintarChip('chipActivos', `${pct} %`, pct >= 90 ? 'ok' : 'aviso');
    const nuevos = suma(t.registros);
    pintarDelta('deltaActivos', `${plural(nuevos, 'registro nuevo', 'registros nuevos')} esta semana`);
    pintarSparkline('sparkRegistros', t.registros);

    // Citas pendientes
    setText('statCitas', numero(s.citas_pendientes));
    pintarChip('chipCitas', `${numero(s.citas_hoy)} hoy`, 'info');
    pintarDelta('deltaCitas', `${plural(suma(t.citas), 'cita', 'citas')} en los últimos 7 días`);
    pintarSparkline('sparkCitas', t.citas);

    // Visitas
    setText('statVisitas', numero(s.visitas_hoy));
    setText('unidadVisitas', numero(s.visitas_hoy) === 1 ? 'visita' : 'visitas');
    pintarChip('chipVisitas', `${numero(s.usuarios_online)} en línea`, 'info');
    pintarDelta('deltaVisitas', `${plural(numero(s.requests_minuto), 'petición', 'peticiones')} por minuto ahora`);

    // Alertas de seguridad
    const alertas = numero(s.alertas_criticas) + numero(s.alertas_warnings) + numero(s.alertas_info);
    setText('statAlertas', alertas);
    pintarChip('chipAlertas', alertas ? 'Revisar' : 'Bien', alertas ? 'aviso' : 'ok');
    pintarDelta('deltaAlertas',
        `${plural(numero(s.fallos_login), 'fallo', 'fallos')} de login · ${plural(numero(s.ips_bloqueadas), 'IP bloqueada', 'IPs bloqueadas')}`,
        alertas ? 'aviso' : null);
    pintarSparkline('sparkSeguridad', t.seguridad);

    pintarHoras(s.actividad_por_hora);

    // Salud del servidor
    pintarMedidor('Cpu', s.cpu, `avisa sobre ${UMBRAL_AVISO} %`);
    pintarMedidor('Ram', s.ram, `avisa sobre ${UMBRAL_AVISO} %`);
    const libre = Math.max(0, numero(s.disk_total_gb) - numero(s.disk_used_gb)).toFixed(1);
    pintarMedidor('Disk', s.disk_pct, s.disk_total_gb ? `quedan ${libre} GB libres` : 'sin datos del disco');
    setText('metricLatency', s.latencia != null ? `${s.latencia} ms` : '—');
    setText('metricUptime', s.uptime ?? '—');
    setText('metricOnline', numero(s.usuarios_online));
    setText('metricRequests', numero(s.requests_minuto));

    pintarEndpoints(s.top_endpoints);
    pintarCuentas(total, activos, suspendidas);

    const hoy = new Date();
    const fecha = hoy.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', timeZone: ZONA });
    setText('dashFecha', fecha.charAt(0).toUpperCase() + fecha.slice(1));
    setText('dashActualizado', `actualizado a las ${hoy.toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit', timeZone: ZONA })}`);
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
            container.innerHTML = '<div class="adm-vacio">No hay usuarios conectados.</div>';
            return;
        }
        container.innerHTML = data.usuarios.map(u => `
            <div class="adm-conectado">
                <span class="server-dot stable"></span>
                <span class="adm-conectado__nombre">${escapeHtml(u.nombre)}</span>
                <small>${escapeHtml(u.rol)}</small>
            </div>
        `).join('');
    } catch (e) {
        console.error('Error cargando usuarios online:', e);
    }
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
            lista.innerHTML = '<li class="adm-vacio">No hay actividad reciente.</li>';
            return;
        }
        const recientes = data.logs.slice(0, 5);
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
    const meta = [log.administrador, etiquetaOrigen(log.origen), log.fecha].filter(Boolean).map(escapeHtml).join(' · ');
    const detalle = log.detalle ? `<div class="adm-reciente__detalle" title="${escapeHtml(log.detalle)}">${escapeHtml(log.detalle)}</div>` : '';
    return `<li class="adm-reciente">
        <span class="adm-reciente__icono" style="color:${color};background:${color}1f;"><i class="fas ${icono}"></i></span>
        <div class="adm-reciente__texto">
            <div class="adm-reciente__accion">${escapeHtml(formatearAccion(log.accion))}</div>
            ${detalle}
            <div class="adm-reciente__meta">${meta}</div>
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