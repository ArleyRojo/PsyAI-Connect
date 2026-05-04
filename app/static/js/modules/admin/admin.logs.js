const API = '';
let todosLogs = [];
const ITEMS_PER_PAGE = 15;
let paginaActual = 1;
let logsFiltrados = [];

const paginas = {
    todos: { pagina: 1, filtrados: [] },
    usuarios: { pagina: 1, filtrados: [] },
    roles: { pagina: 1, filtrados: [] },
    notificaciones: { pagina: 1, filtrados: [] }
};

document.addEventListener('DOMContentLoaded', cargarLogs);

async function cargarLogs() {
    try {
        const res  = await fetch(`${API}/api/admin/logs`);
        const data = await res.json();
        if (!data.success) return;
        todosLogs = data.logs;
        renderLogs(todosLogs);
        actualizarStats(todosLogs);
    } catch(e) { console.error('Error cargando logs:', e); }
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
        <tr data-modulo="${l.modulo}">
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

    renderizarPaginacion(totalPaginas);
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
                return `<tr>
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
                return `<tr>
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
                return `<tr>
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