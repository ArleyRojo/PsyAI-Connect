const API = '';
let todosUsuarios = [];
const ITEMS_PER_PAGE = 15;
let paginaActualRoles = 1;
let rolesFiltrados = [];

document.addEventListener('DOMContentLoaded', () => {
    cargarUsuarios();
    cargarHistorial();
    document.getElementById('buscarUsuario')?.addEventListener('input', filtrarUsuarios);
    document.getElementById('filtroRol')?.addEventListener('change', filtrarUsuarios);
    document.getElementById('filtroEstado')?.addEventListener('change', filtrarUsuarios);
    document.getElementById('btnAsignarRol')?.addEventListener('click', asignarRol);
    document.getElementById('btnGuardarRol')?.addEventListener('click', guardarRol);
    document.getElementById('filtroHistorial')?.addEventListener('change', () => window.renderHistorial());
    document.getElementById('filtroRolHistorial')?.addEventListener('change', () => window.renderHistorial());
    document.getElementById('fechaHistorial')?.addEventListener('change', () => window.renderHistorial());
    window.mostrarTab = mostrarTab;
    window.renderHistorial = renderHistorial;
});

async function cargarUsuarios() {
    try {
        console.log('Cargando usuarios desde API...');
        const res = await fetch('/api/admin/usuarios');
        console.log('Status:', res.status);
        const data = await res.json();
        console.log('Respuesta API:', data);
        
        if (!res.ok) {
            console.error('Error HTTP:', res.status);
            document.getElementById('tablaUsuarios').innerHTML = 
                '<tr><td colspan="5" class="text-center text-danger py-4">Error: ' + (data.message || 'No autorizado') + '</td></tr>';
            return;
        }
        
        if (!data.success || !data.usuarios) {
            document.getElementById('tablaUsuarios').innerHTML = 
                '<tr><td colspan="5" class="text-center text-muted py-4">No hay usuarios registrados.</td></tr>';
            return;
        }
        
        todosUsuarios = data.usuarios || [];
        rolesFiltrados = todosUsuarios;
        
        console.log('Usuarios encontrados:', todosUsuarios.length);
        
        if (todosUsuarios.length > 0) {
            renderizarPaginaRoles();
        } else {
            document.getElementById('tablaUsuarios').innerHTML = 
                '<tr><td colspan="5" class="text-center text-muted py-4">No hay usuarios registrados.</td></tr>';
        }
        
        const cntU = document.getElementById('cntUsuarios');
        if (cntU) cntU.textContent = todosUsuarios.length;
        const cntUE = document.getElementById('cntUsuariosEncontrados');
        if (cntUE) cntUE.textContent = todosUsuarios.length;
        
        populateUserSelect();
        
    } catch(e) { 
        console.error('Error cargando usuarios:', e); 
        document.getElementById('tablaUsuarios').innerHTML = 
            '<tr><td colspan="5" class="text-center text-danger py-4">Error de conexión</td></tr>';
    }
}



function populateUserSelect() {
    const select = document.getElementById('selUsuario');
    if (!select) return;
    
    select.innerHTML = '<option value="">-- Seleccionar usuario --</option>' + 
        todosUsuarios.map(u => `<option value="${u.email}">${u.nombre} (${u.email})</option>`).join('');
}

function renderTablaRoles(lista) {
    rolesFiltrados = lista;
    paginaActualRoles = 1;
    renderizarPaginaRoles();
}

function renderizarPaginaRoles() {
    const tbody = document.getElementById('tablaUsuarios');
    if (!tbody) return;
    
    const totalUsuarios = rolesFiltrados.length;
    const totalPaginas = Math.ceil(totalUsuarios / ITEMS_PER_PAGE) || 1;
    const inicio = (paginaActualRoles - 1) * ITEMS_PER_PAGE;
    const fin = Math.min(inicio + ITEMS_PER_PAGE, totalUsuarios);
    const paginaUsuarios = rolesFiltrados.slice(inicio, fin);

    if (!totalUsuarios) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">Sin usuarios.</td></tr>';
        document.getElementById('mostrandoInicioRoles').textContent = 0;
        document.getElementById('mostrandoFinRoles').textContent = 0;
        document.getElementById('mostrandoTotalRoles').textContent = 0;
    } else {
        tbody.innerHTML = paginaUsuarios.map(u => {
            const ini = u.nombre.split(' ').map(p=>p[0]).join('').toUpperCase().slice(0,2);
            const nom = u.nombre.replace(/'/g,"\\'");
            return `
            <tr>
              <td>
                <div class="user-cell">
                  <div class="user-avatar">${ini}</div>
                  <div><div class="user-name">${u.nombre}</div><div class="user-email">${u.email}</div></div>
                </div>
              </td>
              <td>${rolBadge(u.rol)}</td>
              <td>${estadoBadge(u)}</td>
              <td class="text-muted" style="font-size:.82rem;">${u.fechaRegistro||'—'}</td>
              <td class="text-end">
                <div class="d-flex justify-content-end gap-1">
                  <button class="btn btn-sm btn-outline-primary" onclick="abrirModalEditar(${u.idUsuario},'${nom}','${u.rol}')" title="Editar"><i class="fas fa-edit"></i></button>
                </div>
              </td>
            </tr>`;
        }).join('');
        document.getElementById('mostrandoInicioRoles').textContent = inicio + 1;
        document.getElementById('mostrandoFinRoles').textContent = fin;
        document.getElementById('mostrandoTotalRoles').textContent = totalUsuarios;
    }

    renderizarPaginacionRoles(totalPaginas);
}

function renderizarPaginacionRoles(totalPaginas) {
    const container = document.getElementById('paginacionRoles');
    if (!container) return;

    let html = '';
    html += `<button class="btn btn-light btn-sm" ${paginaActualRoles === 1 ? 'disabled' : ''} onclick="window.cambiarPaginaRoles(${paginaActualRoles - 1})"><i class="fas fa-chevron-left"></i></button>`;

    for (let i = 1; i <= totalPaginas; i++) {
        const esActiva = i === paginaActualRoles;
        const animClass = esActiva ? 'pagination-btn-anim' : '';
        html += `<button class="btn ${esActiva ? 'btn-primary' : 'btn-light'} btn-sm px-3 ${animClass}" onclick="window.cambiarPaginaRoles(${i})">${i}</button>`;
    }

    html += `<button class="btn btn-light btn-sm" ${paginaActualRoles === totalPaginas ? 'disabled' : ''} onclick="window.cambiarPaginaRoles(${paginaActualRoles + 1})"><i class="fas fa-chevron-right"></i></button>`;

    container.innerHTML = html;
}

function cambiarPaginaRoles(pagina) {
    const totalPaginas = Math.ceil(rolesFiltrados.length / ITEMS_PER_PAGE);
    if (pagina < 1 || pagina > totalPaginas) return;
    paginaActualRoles = pagina;
    renderizarPaginaRoles();
}
window.cambiarPaginaRoles = cambiarPaginaRoles;

let historialData = [];

async function cargarHistorial() {
    try {
        const res = await fetch('/api/admin/roles/historial');
        const data = await res.json();
        
        if (!data.success) {
            console.warn('No se pudo cargar el historial');
            return;
        }
        
        historialData = data.historial || [];
        
    } catch(e) { 
        console.error('Error cargando historial:', e);
        historialData = [];
    }
    
    const cntHT = document.getElementById('cntHistorialTab');
    if (cntHT) cntHT.textContent = historialData.length;
    
    renderHistorial();
}

function renderHistorial() {
    const tbody = document.getElementById('tablaHistorial');
    if (!tbody) return;
    
    const filtroAccion = document.getElementById('filtroHistorial')?.value || '';
    const filtroRol = document.getElementById('filtroRolHistorial')?.value || '';
    const filtroFecha = document.getElementById('fechaHistorial')?.value || '';
    
    const filtrados = historialData.filter(h => {
        const coincideAccion = !filtroAccion || (h.accion && h.accion.toLowerCase() === filtroAccion);
        const coincideRol = !filtroRol || 
            (h.rolNuevo && h.rolNuevo.toLowerCase() === filtroRol) ||
            (h.rolAnterior && h.rolAnterior.toLowerCase() === filtroRol);
        const coincideFecha = !filtroFecha || (h.fecha && h.fecha.startsWith(filtroFecha));
        return coincideAccion && coincideRol && coincideFecha;
    });
    
    set('cntHistorial', filtrados.length);
    
    if (!filtrados.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No hay registros que coincidan.</td></tr>';
        return;
    }
    
    tbody.innerHTML = filtrados.map(h => `
        <tr>
          <td class="mono" style="font-size:.82rem;">${h.fecha||'—'}</td>
          <td style="font-size:.82rem;"><strong>${h.usuario||'—'}</strong><br><small class="text-muted">${h.email||''}</small></td>
          <td>${getAccionBadge(h.accion)}</td>
          <td>${getRolBadge(h.rolAnterior)}</td>
          <td>${getRolBadge(h.rolNuevo)}</td>
          <td style="font-size:.82rem;">${h.administrador||'Admin'}</td>
        </tr>`).join('');
}

function getAccionBadge(accion) {
    const acc = accion?.toLowerCase() || '';
    let clase = 'bg-secondary';
    if (acc.includes('agreg')) clase = 'bg-success';
    else if (acc.includes('edit')) clase = 'bg-warning text-dark';
    else if (acc.includes('elim')) clase = 'bg-danger';
    return `<span class="badge ${clase}">${accion||'—'}</span>`;
}

function getRolBadge(rol) {
    if (!rol) return '<span class="badge bg-secondary">—</span>';
    const clases = {
        paciente: 'bg-info',
        profesional: 'bg-success',
        admin: 'bg-primary'
    };
    return `<span class="badge ${clases[rol.toLowerCase()]||'bg-secondary'}">${capitalizar(rol)}</span>`;
}

// ── Modal editar rol ──────────────────────────────────────────────────────────
let _editRolId = null;
function abrirModalEditar(id, nombre, rolActual) {
    _editRolId = id;
    set('modalNombreUsuario', nombre);
    const sel = document.getElementById('modalNuevoRol');
    if (sel) sel.value = rolActual;
    new bootstrap.Modal(document.getElementById('modalEditarRol')).show();
}
window.abrirModalEditar = abrirModalEditar;

async function guardarRol() {
    const nuevoRol = document.getElementById('modalNuevoRol')?.value;
    if (!nuevoRol || !_editRolId) return;
    try {
        const res  = await fetch(`${API}/api/admin/usuarios/${_editRolId}/rol`, {
            method: 'PATCH', headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ nuevoRol })
        });
        const data = await res.json();
        bootstrap.Modal.getInstance(document.getElementById('modalEditarRol')).hide();
        mostrarAlerta(data.success ? 'success' : 'danger', data.message);
        if (data.success) cargarUsuariosRoles();
    } catch(e) { console.error(e); }
}
window.guardarRol = guardarRol;

// ── Activar / Desactivar ──────────────────────────────────────────────────────
async function confirmarAccion(id, nombre, accion) {
    const acc = accion === 'desactivar' ? 'bloquear' : 'desbloquear';
    try {
        const res  = await fetch(`${API}/api/admin/usuarios/${id}/bloquear`, {
            method: 'PATCH', headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ accion: acc })
        });
        const data = await res.json();
        mostrarAlerta(data.success ? 'success' : 'danger', data.message);
        if (data.success) cargarUsuariosRoles();
    } catch(e) { console.error(e); }
}

// ── Asignar rol por email o select ─────────────────────────────────────────────────────
async function asignarRol() {
    const selectUsuario = document.getElementById('selUsuario')?.value;
    const emailInput = document.getElementById('emailUsuario')?.value.trim();
    const email = selectUsuario || emailInput;
    const rol    = document.getElementById('nuevoRol')?.value;
    const motivo = document.getElementById('motivoAsignacion')?.value.trim();
    
    if (!email || !rol) {
        let camposFaltantes = [];
        if (!email) camposFaltantes.push('Usuario');
        if (!rol) camposFaltantes.push('Rol');
        return mostrarAlerta('error', `Falta: ${camposFaltantes.join(', ')}`);
    }
    const usuario = todosUsuarios.find(u => u.email === email);
    if (!usuario) return mostrarAlerta('error', 'Usuario no encontrado.');
    try {
        const res  = await fetch(`${API}/api/admin/usuarios/${usuario.idUsuario}/rol`, {
            method: 'PATCH', headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ nuevoRol: rol, motivo: motivo })
        });
        const data = await res.json();
        mostrarAlerta(data.success ? 'success' : 'error', data.message);
        if (data.success) {
            document.getElementById('selUsuario').value = '';
            document.getElementById('emailUsuario').value = '';
            document.getElementById('nuevoRol').value = '';
            document.getElementById('motivoAsignacion').value = '';
            cargarUsuariosRoles();
        }
    } catch(e) { console.error(e); }
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
function mostrarTab(tab, btn) {
    ['usuarios','agregar','historial'].forEach(t => {
        const el = document.getElementById(`tab-${t}`);
        if (el) el.style.display = t === tab ? '' : 'none';
    });
    document.querySelectorAll('.roles-tab, .logs-tab, .notif-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
}



function rolBadge(rol) {
    if (!rol) return '—';
    const clases = {
        paciente: 'badge bg-info',
        profesional: 'badge bg-success',
        admin: 'badge bg-primary'
    };
    return `<span class="${clases[rol] || 'badge bg-secondary'}">${capitalizar(rol)}</span>`;
}

function estadoBadge(u) {
    if (u.activo == 0) return '<span class="badge bg-warning text-dark">Inactivo</span>';
    return '<span class="badge bg-success">Activo</span>';
}

function capitalizar(s) { return s ? s.charAt(0).toUpperCase()+s.slice(1) : ''; }
function set(id, val) { const el = document.getElementById(id); if(el) el.textContent = val; }

function mostrarAlerta(tipo, msg) {
    if (tipo === 'success' || tipo === 'error') {
        PsyAIAlerts.success('Éxito', msg);
    } else {
        PsyAIAlerts.error('Error', msg);
    }
}

function abrirModalEliminarRol(id, nombre, rol) {
    // Por ahora solo muestra alerta — borrar rol = cambiar a sin rol no aplica en este sistema
    mostrarAlerta('warning', `Para eliminar el rol de ${nombre}, cámbialo desde "Editar rol".`);
}
function filtrarUsuarios() {
    const texto  = document.getElementById('buscarUsuario')?.value.toLowerCase() || '';
    const rol    = document.getElementById('filtroRol')?.value || '';
    const estado = document.getElementById('filtroEstado')?.value || '';

    const filtrados = todosUsuarios.filter(u => {
        const coincideTexto =
            u.nombre.toLowerCase().includes(texto) ||
            u.email.toLowerCase().includes(texto);

        const coincideRol =
            rol === '' || (u.rol && u.rol.toLowerCase() === rol);

        const coincideEstado =
            estado === '' ||
            (estado === 'activo' && parseInt(u.activo) === 1) ||
            (estado === 'inactivo' && parseInt(u.activo) === 0);

        return coincideTexto && coincideRol && coincideEstado;
    });

    rolesFiltrados = filtrados;
    paginaActualRoles = 1;
    renderizarPaginaRoles();
    set('cntUsuarios', filtrados.length);
    set('cntUsuariosEncontrados', filtrados.length);
}