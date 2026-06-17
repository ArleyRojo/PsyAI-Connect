const API = '';
let todosLogs = [];
const ITEMS_PER_PAGE = 15;
let paginaActual = 1;
let logsFiltrados = [];
let _logsEventSource = null;

// Flags for SSE initialization handling
window.logsInitialized = false;
window._pendingLogs = [];

const paginas = {
    todos: { pagina: 1, filtrados: [] },
    usuarios: { pagina: 1, filtrados: [] },
    roles: { pagina: 1, filtrados: [] },
    notificaciones: { pagina: 1, filtrados: [] }
};

window._logsData = window._logsData || [];

// Cache compartido para evitar 4 fetch al mismo endpoint
let _logsFetchPromise = null;
async function _fetchLogsOnce() {
    if (!_logsFetchPromise) {
        _logsFetchPromise = (async () => {
            const res = await fetch(`${API}/api/admin/logs`, { credentials: 'include' });
            const data = await res.json();
            if (!data.success) throw new Error('No success from API');
            return data.logs;
        })();
    }
    return _logsFetchPromise;
}

document.addEventListener('DOMContentLoaded', async () => {
    // Cada tab se carga como promesa independiente: una falla no bloquea las demás
    const resultados = await Promise.allSettled([
        cargarTabTodos(),
        cargarTabUsuarios(),
        cargarTabRoles(),
        cargarTabNotificaciones(),
    ]);
    const nombres = ['todos', 'usuarios', 'roles', 'notificaciones'];
    resultados.forEach((r, i) => {
        if (r.status === 'rejected') {
            console.warn(`Tab "${nombres[i]}" falló:`, r.reason);
            const div = document.getElementById(`tab-log-${nombres[i]}`);
            if (div) div.innerHTML = '<div class="text-danger p-3">Error al cargar datos de esta sección.</div>';
        }
    });
    iniciarLogsStream();
});

async function cargarTabTodos() {
    const logs = await _fetchLogsOnce();
    // Merge con logs pendientes de SSE (misma lógica que estaba en cargarLogs)
    if (window._pendingLogs && window._pendingLogs.length > 0) {
        const logKey = (log) => `${log.origen}-${log.id}`;
        const map = new Map();
        logs.forEach(l => map.set(logKey(l), l));
        window._pendingLogs.forEach(l => map.set(logKey(l), l));
        const mergedLogs = Array.from(map.values());
        mergedLogs.sort((a, b) => {
            const parse = (fecha) => {
                const [datePart, timePart = '00:00'] = fecha.split(' ');
                const [d, m, y] = datePart.split('/');
                const [h, min] = (timePart || '00:00').split(':');
                return new Date(y, m - 1, d, h, min).getTime();
            };
            return parse(b.fecha) - parse(a.fecha);
        });
        todosLogs = mergedLogs;
        window._pendingLogs = [];
    } else {
        todosLogs = logs;
    }
    window._logsData = todosLogs;
    renderLogs(todosLogs);
    actualizarStats(todosLogs);
    window.logsInitialized = true;
}

async function cargarTabUsuarios() {
    const logs = await _fetchLogsOnce();
    const filtrados = logs.filter(l => l.modulo === 'usuarios' || l.modulo === 'accesos');
    const div = document.getElementById('tab-log-usuarios');
    if (div) div._data = filtrados;
}

async function cargarTabRoles() {
    const logs = await _fetchLogsOnce();
    const filtrados = logs.filter(l => l.modulo === 'roles');
    const div = document.getElementById('tab-log-roles');
    if (div) div._data = filtrados;
}

async function cargarTabNotificaciones() {
    const logs = await _fetchLogsOnce();
    const filtrados = logs.filter(l => l.modulo === 'notificaciones');
    const div = document.getElementById('tab-log-notificaciones');
    if (div) div._data = filtrados;
}

// ── SSE para logs en tiempo real ──────────────────────────────────────────────
function iniciarLogsStream() {
    if (_logsEventSource) {
        _logsEventSource.close();
    }

    _logsEventSource = new EventSource(`${API}/api/admin/logs/stream`);

    // Helper to generate unique key for a log entry (to handle same IDs across different sources)
    function logKey(log) {
        return `${log.origen}-${log.id}`;
    }

    _logsEventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.success && data.logs && data.logs.length > 0) {
                // If initial load not yet complete, queue these logs for later
                if (!window.logsInitialized) {
                    window._pendingLogs.push(...data.logs);
                    return;
                }

                // New logs arrived - prepend to the list
                const nuevosLogs = data.logs;
                // Only add logs that are not already in the list (by composite key)
                const keysExistentes = new Set(todosLogs.map(logKey));
                const logsNuevosReales = nuevosLogs.filter(l => !keysExistentes.has(logKey(l)));

                if (logsNuevosReales.length > 0) {
                    // Prepend new logs to the beginning
                    todosLogs = [...logsNuevosReales, ...todosLogs];
                    window._logsData = todosLogs;

                    // Re-apply current filter and re-render
                    filtrarLogs();

                    // Update stats
                    actualizarStats(todosLogs);
                }
            }
        } catch (e) {
            console.error('Error procesando SSE de logs:', e);
        }
    };

    _logsEventSource.onerror = function() {
        console.warn('SSE de logs desconectado, reintentando en 3s...');
        _logsEventSource.close();
        _logsEventSource = null;

        // Reconnect after 3 seconds
        setTimeout(() => {
            iniciarLogsStream();
        }, 3000);
    };
}

async function cargarLogs() {
    try {
        const res  = await fetch(`${API}/api/admin/logs`, { credentials: 'include' });
        const data = await res.json();
        if (!data.success) throw new Error('No success from API');
        
        // Merge any logs that arrived via SSE during the initial fetch
        if (window._pendingLogs && window._pendingLogs.length > 0) {
            const logKey = (log) => `${log.origen}-${log.id}`;
            const map = new Map();
            // Add API logs first
            data.logs.forEach(l => map.set(logKey(l), l));
            // Add pending logs (may overwrite duplicates with newer versions)
            window._pendingLogs.forEach(l => map.set(logKey(l), l));
            const mergedLogs = Array.from(map.values());
            // Sort by fecha descending (parse DD/MM/YYYY HH:MM)
            mergedLogs.sort((a, b) => {
                const parse = (fecha) => {
                    const [datePart, timePart = '00:00'] = fecha.split(' ');
                    const [d, m, y] = datePart.split('/');
                    const [h, min] = (timePart || '00:00').split(':');
                    return new Date(y, m-1, d, h, min).getTime();
                };
                return parse(b.fecha) - parse(a.fecha);
            });
            data.logs = mergedLogs;
            window._pendingLogs = [];
        }
        
        todosLogs = data.logs;
        window._logsData = todosLogs;
        renderLogs(todosLogs);
        actualizarStats(todosLogs);
    } catch(e) {
        console.error('Error cargando logs:', e);
        // Even on error, process any pending logs to avoid losing them
        if (window._pendingLogs && window._pendingLogs.length > 0) {
            const logKey = (log) => `${log.origen}-${log.id}`;
            const map = new Map();
            window._pendingLogs.forEach(l => map.set(logKey(l), l));
            const mergedLogs = Array.from(map.values());
            mergedLogs.sort((a, b) => {
                const parse = (fecha) => {
                    const [datePart, timePart = '00:00'] = fecha.split(' ');
                    const [d, m, y] = datePart.split('/');
                    const [h, min] = (timePart || '00:00').split(':');
                    return new Date(y, m-1, d, h, min).getTime();
                };
                return parse(b.fecha) - parse(a.fecha);
            });
            todosLogs = mergedLogs;
            window._pendingLogs = [];
        } else {
            todosLogs = [];
        }
        window._logsData = todosLogs;
        renderLogs(todosLogs);
        actualizarStats(todosLogs);
    } finally {
        window.logsInitialized = true;
    }
}

function actualizarStats(lista) {
    const usuariosLogs = lista.filter(l => l.modulo === 'usuarios').length;
    const accesosLogs = lista.filter(l => l.modulo === 'accesos').length;
    const rolesLogs = lista.filter(l => l.modulo === 'roles').length;
    const notifsLogs = lista.filter(l => l.modulo === 'notificaciones').length;
    
    const total = lista.length;
    const usuariosTotal = usuariosLogs + accesosLogs;

    set('statTotal', total);
    set('statUsuarios', usuariosTotal);
    set('statRoles', rolesLogs);
    set('statNotifs', notifsLogs);
    set('cntTodos', total);
    set('cntUsuarios', usuariosTotal);
    set('cntRoles', rolesLogs);
    set('cntNotifs', notifsLogs);
    set('mostrando', total);
}

function getBadgeOrigen(origen) {
    const label = origen === 'auditoria' ? 'Acceso' : capitalizar(origen);
    const icons = {
        profesional: 'fa-user-md',
        paciente: 'fa-user',
        sistema: 'fa-cog',
        admin: 'fa-user-shield',
        notificacion: 'fa-bell',
        auditoria: 'fa-sign-in-alt'
    };
    return `<span class="badge-origin badge-origen-${origen}"><i class="fas ${icons[origen] || 'fa-circle'}"></i> ${label}</span>`;
}

function getBadgeModulo(modulo) {
    const iconos = { usuarios:'fa-users', roles:'fa-user-shield', notificaciones:'fa-bell', accesos:'fa-sign-in-alt', sistema:'fa-cog' };
    const icono = iconos[modulo] || 'fa-circle';
    return `<span class="badge-modulo badge-modulo-${modulo}"><i class="fas ${icono}"></i> ${capitalizar(modulo)}</span>`;
}

function getBadgeUsuario(usuario) {
    if (!usuario) return '—';
    return `<span class="badge-usuario">${usuario}</span>`;
}

function getBadgeRol(rol) {
    if (!rol) return '—';
    const clases = {
        paciente: 'badge-rol badge-rol-paciente',
        profesional: 'badge-rol badge-rol-profesional',
        admin: 'badge-rol badge-rol-admin'
    };
    const icons = {
        paciente: 'fa-user',
        profesional: 'fa-user-md',
        admin: 'fa-user-shield'
    };
    return `<span class="${clases[rol] || 'badge-rol'}"><i class="fas ${icons[rol] || 'fa-user'}"></i> ${capitalizar(rol)}</span>`;
}

function getBadgeAccion(accion) {
    if (!accion) return '—';
    const a = accion.toLowerCase();
    
    let clase = 'log-badge';
    if (a.includes('login') || a.includes('exitoso')) clase += ' login';
    else if (a.includes('crear') || a.includes('nuevo')) clase += ' create';
    else if (a.includes('editar') || a.includes('actua')) clase += ' edit';
    else if (a.includes('eliminar') || a.includes('borrar')) clase += ' delete';
    else if (a.includes('bloquear') || a.includes('bloqu')) clase += ' alerta';
    else if (a.includes('rol')) clase += ' role';
    else if (a.includes('notif') || a.includes('envi')) clase += ' info';
    else clase += ' sistema';
    
    return `<span class="${clase}">${accion}</span>`;
}



function renderLogs(lista) {
    logsFiltrados = lista;
    paginaActual = 1;
    renderizarPagina();
}

function renderizarPagina() {
    const tbody = document.getElementById('tablaLogsTodos');
    if (!tbody) return;
    
    const totalLogs = logsFiltrados.length;
    const totalPaginas = Math.ceil(totalLogs / ITEMS_PER_PAGE) || 1;
    const inicio = (paginaActual - 1) * ITEMS_PER_PAGE;
    const fin = Math.min(inicio + ITEMS_PER_PAGE, totalLogs);
    const paginaLogs = logsFiltrados.slice(inicio, fin);

    if (!totalLogs) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No hay registros.</td></tr>';
        set('mostrandoInicio', 0);
        set('mostrandoFin', 0);
        set('mostrandoTotal', 0);
    } else {
        tbody.innerHTML = paginaLogs.map(l => {
            return `
        <tr class="log-row ${severidad(l)}" data-modulo="${l.modulo}">
          <td class="ps-4"><span class="sev-dot ${severidad(l)}"></span></td>
          <td class="mono">${l.fecha}</td>
          <td>
            <div class="user-cell">
              <div class="user-avatar" style="background:#e8faf6;color:#283593;">${iniciales(l.administrador)}</div>
              <span class="user-name">${l.administrador}</span>
            </div>
          </td>
          <td>${getBadgeModulo(l.modulo)}</td>
          <td>${getBadgeAccion(l.accion)}</td>
          <td>${getBadgeOrigen(l.origen)}</td>
          <td><span class="detalle-badge">${l.detalle || '—'}</span></td>
        </tr>`;
        }).join('');
        set('mostrandoInicio', inicio + 1);
        set('mostrandoFin', fin);
        set('mostrandoTotal', totalLogs);
    }

    aplicarLabelsResponsiveLogs(tbody);
    renderizarPaginacion(totalPaginas);
}

function aplicarLabelsResponsiveLogs(tbody) {
    const table = tbody?.closest('table');
    if (!table) return;

    const labels = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
    Array.from(tbody.querySelectorAll('tr')).forEach(row => {
        Array.from(row.children).forEach((cell, index) => {
            if (!cell.hasAttribute('data-label')) {
                cell.setAttribute('data-label', labels[index] || '');
            }
        });
    });
}

function renderizarPaginacion(totalPaginas) {
    const container = document.getElementById('paginacionLogs');
    if (!container) return;

    let html = '';
    
    html += `<button class="btn btn-light btn-sm" ${paginaActual === 1 ? 'disabled' : ''} onclick="cambiarPagina(${paginaActual - 1})"><i class="fas fa-chevron-left"></i></button>`;

    for (let i = 1; i <= totalPaginas; i++) {
        const esActiva = i === paginaActual;
        const animClass = esActiva ? 'pagination-btn-anim' : '';
        html += `<button class="btn ${esActiva ? 'btn-primary' : 'btn-light'} btn-sm px-3 ${animClass}" onclick="cambiarPagina(${i})">${i}</button>`;
    }

    html += `<button class="btn btn-light btn-sm" ${paginaActual === totalPaginas ? 'disabled' : ''} onclick="cambiarPagina(${paginaActual + 1})"><i class="fas fa-chevron-right"></i></button>`;

    container.innerHTML = html;
}

function cambiarPagina(pagina) {
    const totalPaginas = Math.ceil(logsFiltrados.length / ITEMS_PER_PAGE);
    if (pagina < 1 || pagina > totalPaginas) return;
    paginaActual = pagina;
    renderizarPagina();
}

function iniciales(nombre) {
    if (!nombre) return 'AD';
    return nombre.split(' ').map(p => p[0]).join('').toUpperCase().slice(0, 2);
}

function iconModulo(m) {
    const map = { usuarios:'users', roles:'user-shield', notificaciones:'bell', accesos:'sign-in-alt', sistema:'cog', admin:'shield-alt' };
    return map[m] || 'circle';
}

function etiquetaModulo(m) {
    const map = { usuarios:'Usuarios', roles:'Roles', notificaciones:'Notificaciones', accesos:'Accesos', sistema:'Sistema', admin:'Admin' };
    return map[m] || capitalizar(m);
}



function severidad(l) {
    const a = (l.accion || '').toLowerCase();
    if (a.includes('eliminar') || a.includes('borrar')) return 'sev-eliminar';
    if (a.includes('bloquear') || a.includes('bloqu')) return 'sev-bloquear';
    if (a.includes('crear') || a.includes('nuevo')) return 'sev-crear';
    if (a.includes('editar') || a.includes('actua')) return 'sev-editar';
    if (a.includes('login') || a.includes('exitoso')) return 'sev-login';
    if (a.includes('rol')) return 'sev-rol';
    if (a.includes('notif') || a.includes('envi')) return 'sev-notif';
    return 'sev-default';
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
function mostrarTabLogs(tab, btn) {
    ['todos','usuarios','roles','notificaciones'].forEach(t => {
        const el = document.getElementById(`tab-log-${t}`);
        if (el) el.style.display = t === tab ? '' : 'none';
    });
    document.querySelectorAll('.logs-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    filtrarLogs();
}

function mostrarPanelAdmin(panel, btn) {
    ['logs', 'rendimiento'].forEach(nombre => {
        const el = document.getElementById(`panel-${nombre}`);
        if (el) el.style.display = nombre === panel ? '' : 'none';
    });

    document.querySelectorAll('.admin-panel-tab').forEach(tab => {
        tab.classList.remove('active');
        tab.setAttribute('aria-selected', 'false');
    });

    if (btn) {
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
    }

    if (panel === 'rendimiento' && typeof cargarRendimiento === 'function') {
        if (!window.rendimientoCargado) {
            cargarRendimiento();
        }
    }
}

// ── Filtros ───────────────────────────────────────────────────────────────────
function filtrarLogs() {
    const tabActiva = document.querySelector('.logs-tab.active');
    if (!tabActiva) return;
    
    const tabText = tabActiva.textContent.trim().toLowerCase();

    const tab = tabText.includes('todos') ? 'todos' : 
                tabText.includes('usuarios') ? 'usuarios' : 
                tabText.includes('roles') ? 'roles' : 
                tabText.includes('notificaciones') ? 'notificaciones' : 'todos';
    
    let accion = '';
    let texto = '';
    let moduloFiltro = [];
    
    if (tab === 'todos') {
        accion = (document.getElementById('filtroAccion')?.value || '').toLowerCase();
        texto = (document.getElementById('filtroTexto')?.value || '').toLowerCase();
    } else if (tab === 'usuarios') {
        moduloFiltro = ['usuarios', 'accesos'];
        accion = (document.getElementById('filtroAccionUsuarios')?.value || '').toLowerCase();
        texto = (document.getElementById('filtroTextoUsuarios')?.value || '').toLowerCase();
    } else if (tab === 'roles') {
        moduloFiltro = ['roles'];
        accion = (document.getElementById('filtroAccionRoles')?.value || '').toLowerCase();
        texto = (document.getElementById('filtroTextoRoles')?.value || '').toLowerCase();
    } else if (tab === 'notificaciones') {
        moduloFiltro = ['notificaciones'];
        accion = (document.getElementById('filtroAccionNotifs')?.value || '').toLowerCase();
        texto = (document.getElementById('filtroTextoNotifs')?.value || '').toLowerCase();
    }

    const filtrado = todosLogs.filter(l => {
        let coincideModulo = true;
        if (tab !== 'todos' && moduloFiltro.length > 0) {
            coincideModulo = moduloFiltro.includes(l.modulo);
        }

        const coincideAccion =
            !accion || (l.accion && l.accion.toLowerCase().includes(accion));

        const coincideTexto =
            !texto ||
            (l.detalle || '').toLowerCase().includes(texto) ||
            (l.accion || '').toLowerCase().includes(texto) ||
            (l.administrador || '').toLowerCase().includes(texto) ||
            (l.usuario_afectado || '').toLowerCase().includes(texto);

        return coincideModulo && coincideAccion && coincideTexto;
    });

    logsFiltrados = filtrado;
    paginaActual = 1;
    
    if (tab === 'todos') {
        renderizarPagina();
    } else {
        paginas[tab].filtrados = filtrado;
        paginas[tab].pagina = 1;
        renderLogsTab(filtrado, tab);
    }
}

function renderLogsTab(lista, tab) {
    let tabId = 'todos';
    if (tab.includes('usuarios')) tabId = 'usuarios';
    else if (tab.includes('roles')) tabId = 'roles';
    else if (tab.includes('notificaciones')) tabId = 'notificaciones';

    const div = document.getElementById(`tab-log-${tabId}`);
    if (!div) return;
    
    if (tabId === 'usuarios') {
        renderizarPaginacionTab('usuarios', lista, 'paginacionUsuarios', 'mostrandoInicioUsuarios', 'mostrandoFinUsuarios', 'mostrandoTotalUsuarios');
    } else if (tabId === 'roles') {
        renderizarPaginacionTab('roles', lista, 'paginacionRoles', 'mostrandoInicioRoles', 'mostrandoFinRoles', 'mostrandoTotalRoles');
    } else if (tabId === 'notificaciones') {
        renderizarPaginacionTab('notificaciones', lista, 'paginacionNotifs', 'mostrandoInicioNotifs', 'mostrandoFinNotifs', 'mostrandoTotalNotifs');
    }
}

function capitalizar(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''; }
function set(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }

function renderizarPaginacionTab(tabId, lista, containerId, inicioId, finId, totalId) {
    const totalLogs = lista.length;
    const totalPaginas = Math.ceil(totalLogs / ITEMS_PER_PAGE) || 1;
    const p = paginas[tabId] || { pagina: 1 };
    const inicio = (p.pagina - 1) * ITEMS_PER_PAGE;
    const fin = Math.min(inicio + ITEMS_PER_PAGE, totalLogs);
    const paginaLogs = lista.slice(inicio, fin);

    const tbodyId = tabId === 'usuarios' ? 'tablaLogsUsuarios' : 
                    tabId === 'roles' ? 'tablaLogsRoles' : 'tablaLogsNotifs';
    const tbody = document.getElementById(tbodyId);
    
    if (!tbody) return;

    if (!totalLogs) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No hay registros.</td></tr>`;
        set(inicioId, 0);
        set(finId, 0);
        set(totalId, 0);
    } else {
        if (tabId === 'usuarios') {
            tbody.innerHTML = paginaLogs.map(l => {
                return `<tr class="log-row ${severidad(l)}">
                  <td class="ps-4"><span class="sev-dot ${severidad(l)}"></span></td>
                  <td class="mono">${l.fecha}</td>
                  <td>${getBadgeAccion(l.accion)}</td>
                  <td>${getBadgeUsuario(l.usuario_afectado || l.administrador)}</td>
                  <td>${getBadgeOrigen(l.origen)}</td>
                  <td><span class="detalle-badge">${l.detalle || '—'}</span></td>
                </tr>`;
            }).join('');
        } else if (tabId === 'roles') {
            tbody.innerHTML = paginaLogs.map(l => {
                return `<tr class="log-row ${severidad(l)}">
                  <td class="ps-4"><span class="sev-dot ${severidad(l)}"></span></td>
                  <td class="mono">${l.fecha}</td>
                  <td>${getBadgeAccion(l.accion)}</td>
                  <td>${getBadgeUsuario(l.usuario_afectado || l.administrador)}</td>
                  <td>${getBadgeOrigen(l.origen)}</td>
                  <td>${getBadgeRol(l.rol_anterior)}</td>
                  <td>${getBadgeRol(l.rol_nuevo)}</td>
                </tr>`;
            }).join('');
        } else if (tabId === 'notificaciones') {
            tbody.innerHTML = paginaLogs.map(l => {
                return `<tr class="log-row ${severidad(l)}">
                  <td class="ps-4"><span class="sev-dot ${severidad(l)}"></span></td>
                  <td class="mono">${l.fecha}</td>
                  <td>${getBadgeAccion(l.accion)}</td>
                  <td>${getBadgeOrigen(l.origen)}</td>
                  <td>${getBadgeUsuario(l.usuario_afectado || l.administrador)}</td>
                  <td><span class="detalle-badge">${l.detalle || '—'}</span></td>
                </tr>`;
            }).join('');
        }
        set(inicioId, inicio + 1);
        set(finId, fin);
        set(totalId, totalLogs);
    }

    aplicarLabelsResponsiveLogs(tbody);
    renderizarBotonesPaginacion(tabId, totalPaginas, containerId);
}

function renderizarBotonesPaginacion(tabId, totalPaginas, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const p = paginas[tabId] || { pagina: 1 };
    
    let html = '';
    html += `<button class="btn btn-light btn-sm" ${p.pagina === 1 ? 'disabled' : ''} onclick="cambiarPaginaTab('${tabId}', ${p.pagina - 1})"><i class="fas fa-chevron-left"></i></button>`;

    for (let i = 1; i <= totalPaginas; i++) {
        const esActiva = i === p.pagina;
        const animClass = esActiva ? 'pagination-btn-anim' : '';
        html += `<button class="btn ${esActiva ? 'btn-primary' : 'btn-light'} btn-sm px-3 ${animClass}" onclick="cambiarPaginaTab('${tabId}', ${i})">${i}</button>`;
    }

    html += `<button class="btn btn-light btn-sm" ${p.pagina === totalPaginas ? 'disabled' : ''} onclick="cambiarPaginaTab('${tabId}', ${p.pagina + 1})"><i class="fas fa-chevron-right"></i></button>`;

    container.innerHTML = html;
}

function cambiarPaginaTab(tabId, pagina) {
    const p = paginas[tabId];
    if (!p) return;
    
    const totalPaginas = Math.ceil(p.filtrados.length / ITEMS_PER_PAGE);
    if (pagina < 1 || pagina > totalPaginas) return;
    
    p.pagina = pagina;
    
    if (tabId === 'usuarios') {
        renderizarPaginacionTab('usuarios', p.filtrados, 'paginacionUsuarios', 'mostrandoInicioUsuarios', 'mostrandoFinUsuarios', 'mostrandoTotalUsuarios');
    } else if (tabId === 'roles') {
        renderizarPaginacionTab('roles', p.filtrados, 'paginacionRoles', 'mostrandoInicioRoles', 'mostrandoFinRoles', 'mostrandoTotalRoles');
    } else if (tabId === 'notificaciones') {
        renderizarPaginacionTab('notificaciones', p.filtrados, 'paginacionNotifs', 'mostrandoInicioNotifs', 'mostrandoFinNotifs', 'mostrandoTotalNotifs');
    }
}
