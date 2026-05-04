const API = '';

document.addEventListener('DOMContentLoaded', () => {
    verificarSesionAdmin();
    cargarStats();
    cargarActividadReciente();
});

// ── Sesión ──────────────────────────────────────────────────

async function verificarSesionAdmin() {
    try {
        const res  = await fetch(`${API}/api/session`, { credentials: 'include' });
        if (res.status === 401) { window.location.href = '../login.html'; return; }
        const data = await res.json();
        if (!data.success || data.usuario?.rol !== 'admin') {
            window.location.href = '/PsyAI%20Connect/login.html';
        } else {
            const saludo = document.querySelector('.user-info .fw-semibold');
            if (saludo) saludo.textContent = `Hola, ${data.usuario.nombre}`;
        }
    } catch (e) {
        // Si Flask no responde, no redirigir en desarrollo
    }
}

// ── Stats ───────────────────────────────────────────────────

async function cargarStats() {
    try {
        const res  = await fetch(`${API}/api/admin/stats`, { credentials: 'include' });
        const data = await res.json();
        if (!data.success) return;
        const s = data.stats;

        set('statTotal',       s.total_usuarios);
        set('statActivos',     s.usuarios_activos);
        set('statNotifs',      s.notificaciones);
        set('statSuspendidos', s.cuentas_suspendidas ?? s.cuentas_bloqueadas);
    } catch (e) {
        console.error('No se pudo cargar stats:', e);
    }
}

// ── Actividad reciente ──────────────────────────────────────
// Consume /api/admin/logs (todos los orígenes) y muestra las
// últimas 8 entradas ordenadas por fecha en #listaActividad.

async function cargarActividadReciente() {
    const lista = document.getElementById('listaActividad');
    if (!lista) return;

    lista.innerHTML = '<li class="text-muted"><i class="fas fa-spinner fa-spin me-2"></i>Cargando actividad...</li>';

    try {
        const res  = await fetch(`${API}/api/admin/logs`, { credentials: 'include' });
        const data = await res.json();

        if (!data.success || !data.logs || data.logs.length === 0) {
            lista.innerHTML = '<li class="text-muted">No hay actividad reciente.</li>';
            return;
        }

        // Los logs ya vienen ordenados por fecha DESC desde el backend;
        // tomamos solo los primeros 8 para el dashboard.
        const recientes = data.logs.slice(0, 8);
        lista.innerHTML = recientes.map(log => buildItem(log)).join('');

    } catch (e) {
        console.error('Error cargando actividad:', e);
        lista.innerHTML = '<li class="text-danger"><i class="fas fa-exclamation-circle me-2"></i>Error al cargar actividad.</li>';
    }
}

// ── Construcción de cada ítem ───────────────────────────────

function buildItem(log) {
    const { icono, color } = getIconoOrigen(log.origen, log.accion);
    const accionFormateada  = formatearAccion(log.accion);
    const detalle           = log.detalle ? `<span class="text-muted ms-1">— ${log.detalle}</span>` : '';
    const autor             = log.administrador ? `<small class="text-muted">${log.administrador}</small>` : '';

    return `
    <li class="d-flex align-items-start gap-3 py-2 border-bottom border-light">
        <div class="actividad-icono rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
             style="width:36px;height:36px;background:${color}15;">
            <i class="fas ${icono}" style="color:${color};font-size:.85rem;"></i>
        </div>
        <div class="flex-grow-1 lh-sm">
            <div class="fw-semibold" style="font-size:.875rem;">
                ${accionFormateada}${detalle}
            </div>
            <div class="d-flex gap-2 align-items-center mt-1">
                ${autor}
                <span class="badge rounded-pill" style="background:${color}18;color:${color};font-size:.68rem;">
                    ${etiquetaOrigen(log.origen)}
                </span>
                <small class="text-muted ms-auto">${log.fecha}</small>
            </div>
        </div>
    </li>`;
}

// ── Helpers visuales ────────────────────────────────────────

function getIconoOrigen(origen, accion) {
    const a = (accion || '').toLowerCase();

    // Prioridad por acción
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

    // Fallback por origen
    const map = {
        admin:        { icono: 'fa-user-shield',    color: '#673AB7' },
        auditoria:    { icono: 'fa-sign-in-alt',    color: '#2196F3' },
        notificacion: { icono: 'fa-bell',           color: '#00BCD4' },
        profesional:  { icono: 'fa-user-md',        color: '#3F51B5' },
        paciente:     { icono: 'fa-user',           color: '#4CAF50' },
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
    // Capitalizar primera letra y acortar si es muy largo
    const s = capitalizar(accion);
    return s.length > 60 ? s.slice(0, 57) + '…' : s;
}

function capitalizar(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

function set(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? '—';
}