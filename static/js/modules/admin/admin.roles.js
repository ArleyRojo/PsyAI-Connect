const API = '';
function escapeHtmlRoles(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}
function inlineJsArgRoles(value) {
    return escapeHtmlRoles(JSON.stringify(String(value ?? '')).replace(/[<>&\u2028\u2029]/g, char => ({ '<': '\\u003c', '>': '\\u003e', '&': '\\u0026', '\u2028': '\\u2028', '\u2029': '\\u2029' })[char]));
}
let todosUsuarios = [];
const ITEMS_PER_PAGE = 15;
let paginaActualRoles = 1;
let rolesFiltrados = [];

document.addEventListener('DOMContentLoaded', () => {
    cargarUsuarios();
    cargarHistorial();
    cargarCatalogo();
    document.getElementById('btnCrearRolCatalogo')?.addEventListener('click', crearRolCatalogo);
    document.getElementById('tablaCatalogo')?.addEventListener('click', e => {
        const btn = e.target.closest('[data-eliminar-rol]');
        if (btn) eliminarRolCatalogo(Number(btn.dataset.eliminarRol), btn.dataset.nombre);
    });
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
        const res = await fetch('/api/admin/usuarios');
        const data = await res.json();
        
        if (!res.ok) {
            console.error('Error HTTP:', res.status);
            document.getElementById('tablaUsuarios').innerHTML = 
                '<tr><td colspan="5" class="text-center text-danger py-4">Error: ' + escapeHtmlRoles(data.message || 'No autorizado') + '</td></tr>';
            return;
        }
        
        if (!data.success || !data.usuarios) {
            document.getElementById('tablaUsuarios').innerHTML = 
                '<tr><td colspan="5" class="text-center text-muted py-4">No hay usuarios registrados.</td></tr>';
            return;
        }
        
        todosUsuarios = data.usuarios || [];
        rolesFiltrados = todosUsuarios;
        
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
        todosUsuarios.map(u => `<option value="${escapeHtmlRoles(u.email)}">${escapeHtmlRoles(u.nombre)} (${escapeHtmlRoles(u.email)})</option>`).join('');
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
            const ini = escapeHtmlRoles(String(u.nombre || '').split(' ').map(p=>p[0]).join('').toUpperCase().slice(0,2));
            return `
            <tr>
              <td data-label="Usuario">
                <div class="user-cell">
                  <div class="user-avatar">${ini}</div>
                  <div><div class="user-name">${escapeHtmlRoles(u.nombre)}</div><div class="user-email">${escapeHtmlRoles(u.email)}</div></div>
                </div>
              </td>
              <td data-label="Rol">${rolBadge(u.rol, u.rolPersonalizado)}</td>
              <td data-label="Estado">${estadoBadge(u)}</td>
              <td data-label="Última actividad" class="text-muted" style="font-size:.82rem;">${escapeHtmlRoles(u.fechaRegistro||'—')}</td>
              <td class="text-end">
                <div class="d-flex justify-content-end gap-1">
                  <button class="btn btn-sm btn-outline-primary" onclick="abrirModalEditar(${Number(u.idUsuario)},${inlineJsArgRoles(u.nombre)},${inlineJsArgRoles(u.idRolPersonalizado ? 'custom:' + u.idRolPersonalizado : u.rol)})" title="Editar"><i class="fas fa-edit"></i></button>
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
          <td class="mono" style="font-size:.82rem;">${escapeHtmlRoles(h.fecha||'—')}</td>
          <td style="font-size:.82rem;"><strong>${escapeHtmlRoles(h.usuario||'—')}</strong><br><small class="text-muted">${escapeHtmlRoles(h.email||'')}</small></td>
          <td>${getAccionBadge(h.accion)}</td>
          <td>${getRolBadge(h.rolAnterior)}</td>
          <td>${getRolBadge(h.rolNuevo)}</td>
          <td style="font-size:.82rem;">${escapeHtmlRoles(h.administrador||'Admin')}</td>
        </tr>`).join('');
}

function getAccionBadge(accion) {
    const acc = accion?.toLowerCase() || '';
    let clase = 'sistema';
    if (acc.includes('agreg') || acc.includes('crear')) clase = 'create';
    else if (acc.includes('edit')) clase = 'edit';
    else if (acc.includes('elim')) clase = 'delete';
    else if (acc.includes('rol')) clase = 'role';
    return `<span class="log-badge ${clase}">${escapeHtmlRoles(accion||'—')}</span>`;
}

function getRolBadge(rol) {
    if (!rol) return '<span class="log-badge sistema">—</span>';
    const cls = rol === 'admin' ? 'badge-rol-admin' : rol === 'profesional' ? 'badge-rol-profesional' : 'badge-rol-paciente';
    return `<span class="badge-rol ${cls}">${escapeHtmlRoles(capitalizar(rol))}</span>`;
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
        const res  = await fetch(`${API}/api/admin/usuarios/${_editRolId}`, {
            method: 'PATCH', headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ nuevoRol })
        });
        const data = await res.json();
        bootstrap.Modal.getInstance(document.getElementById('modalEditarRol')).hide();
        mostrarAlerta(data.success ? 'success' : 'danger', data.message);
        if (data.success) { cargarUsuarios(); cargarHistorial(); cargarCatalogo(); }
    } catch(e) { console.error(e); }
}
window.guardarRol = guardarRol;

// ── Activar / Desactivar ──────────────────────────────────────────────────────
async function confirmarAccion(id, nombre, accion) {
    const acc = accion === 'desactivar' ? 'bloquear' : 'desbloquear';
    try {
        const res  = await fetch(`${API}/api/admin/usuarios/${id}`, {
            method: 'PATCH', headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ accion: acc })
        });
        const data = await res.json();
        mostrarAlerta(data.success ? 'success' : 'danger', data.message);
        if (data.success) { cargarUsuarios(); cargarHistorial(); cargarCatalogo(); }
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
        const res  = await fetch(`${API}/api/admin/usuarios/${usuario.idUsuario}`, {
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
            cargarUsuarios(); cargarHistorial(); cargarCatalogo();
        }
    } catch(e) { console.error(e); }
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
function mostrarTab(tab, btn) {
    ['usuarios','catalogo','agregar','historial'].forEach(t => {
        const el = document.getElementById(`tab-${t}`);
        if (el) {
            el.style.display = t === tab ? '' : 'none';
            if (t === tab) { el.style.opacity = '1'; el.style.transform = 'none'; }
        }
    });
    document.querySelectorAll('.admin-panel-tab').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
    });
    if (btn) {
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
    }
}



function rolBadge(rol, personalizado) {
    if (!rol) return '—';
    const cls = rol === 'admin' ? 'badge-rol-admin' : rol === 'profesional' ? 'badge-rol-profesional' : 'badge-rol-paciente';
    if (personalizado) {
        // Rol del catálogo (HU-11): se muestra su nombre y debajo el rol base del que hereda permisos
        return `<span class="badge-rol ${cls}">${escapeHtmlRoles(personalizado)}</span>` +
            `<small class="d-block text-muted" style="font-size:.72rem;">Base: ${escapeHtmlRoles(capitalizar(rol))}</small>`;
    }
    return `<span class="badge-rol ${cls}">${escapeHtmlRoles(capitalizar(rol))}</span>`;
}

function estadoBadge(u) {
    if (u.activo == 0) return '<span class="badge-estado badge-estado-suspendido">Suspendido</span>';
    return '<span class="badge-estado badge-estado-activo">Activo</span>';
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


// ── Catálogo de roles (HU-11) ─────────────────────────────────────────────────
const NOMBRES_BASE = { paciente: 'Paciente', profesional: 'Profesional', admin: 'Administrador' };
let catalogoPersonalizados = [];

function avisoRoles(tipo, mensaje, titulo) {
    if (window.PsyAIAlerts && typeof window.PsyAIAlerts[tipo] === 'function') window.PsyAIAlerts[tipo](mensaje, titulo);
}

// Llena los selectores de rol (asignar y editar) con los roles base y los personalizados
function llenarSelectoresRol() {
    const opcionesBase = Object.keys(NOMBRES_BASE)
        .map(k => `<option value="${k}">${NOMBRES_BASE[k]}</option>`).join('');
    const opcionesCustom = catalogoPersonalizados.length
        ? '<optgroup label="Roles personalizados">' + catalogoPersonalizados.map(r =>
            `<option value="custom:${Number(r.idRol)}">${escapeHtmlRoles(r.nombre)} (${escapeHtmlRoles(r.rolBaseNombre)})</option>`).join('') + '</optgroup>'
        : '';
    const asignar = document.getElementById('nuevoRol');
    if (asignar) {
        const valor = asignar.value;
        asignar.innerHTML = '<option value="">Seleccionar rol</option><optgroup label="Roles base">' + opcionesBase + '</optgroup>' + opcionesCustom;
        asignar.value = valor;
    }
    const editar = document.getElementById('modalNuevoRol');
    if (editar) {
        const valor = editar.value;
        editar.innerHTML = '<optgroup label="Roles base">' + opcionesBase + '</optgroup>' + opcionesCustom;
        editar.value = valor;
    }
}

async function cargarCatalogo() {
    const tbody = document.getElementById('tablaCatalogo');
    try {
        const res = await fetch('/api/admin/roles/catalogo', { credentials: 'include' });
        const data = await res.json();
        if (!res.ok || !data.success) throw new Error(data.message || 'Error');
        catalogoPersonalizados = data.personalizados || [];
        set('cntCatalogo', (data.base || []).length + catalogoPersonalizados.length);
        const filasBase = (data.base || []).map(r => `
            <tr>
              <td><strong>${escapeHtmlRoles(r.nombre)}</strong><small class="d-block text-muted">${escapeHtmlRoles(r.descripcion)}</small></td>
              <td>${rolBadge(r.rolBase)}</td>
              <td>${Number(r.usuarios)}</td>
              <td class="text-end"><span class="text-muted" style="font-size:.78rem;"><i class="fas fa-lock me-1"></i>Rol del sistema</span></td>
            </tr>`).join('');
        const filasCustom = catalogoPersonalizados.map(r => `
            <tr>
              <td><strong>${escapeHtmlRoles(r.nombre)}</strong><small class="d-block text-muted">${escapeHtmlRoles(r.descripcion || 'Sin descripción')}</small></td>
              <td>${rolBadge(r.rolBase)}</td>
              <td>${Number(r.usuarios)}</td>
              <td class="text-end">
                <button type="button" class="btn btn-sm btn-outline-danger" data-eliminar-rol="${Number(r.idRol)}" data-nombre="${escapeHtmlRoles(r.nombre)}" title="Eliminar rol"${r.usuarios ? ' disabled' : ''}>
                  <i class="fas fa-trash"></i>
                </button>
              </td>
            </tr>`).join('');
        tbody.innerHTML = filasBase + (filasCustom || '<tr><td colspan="4" class="text-center text-muted py-3">Todavía no hay roles personalizados.</td></tr>');
        llenarSelectoresRol();
    } catch (e) {
        console.error(e);
        if (tbody) tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger py-4">No se pudo cargar el catálogo.</td></tr>';
    }
}

async function crearRolCatalogo() {
    const nombre = document.getElementById('catNombre').value.trim();
    const rolBase = document.getElementById('catBase').value;
    const descripcion = document.getElementById('catDescripcion').value.trim();
    if (nombre.length < 3) return avisoRoles('warning', 'Escribe un nombre de al menos 3 caracteres.', 'Falta un dato');
    if (!rolBase) return avisoRoles('warning', 'Elige el rol base.', 'Falta un dato');
    const btn = document.getElementById('btnCrearRolCatalogo');
    btn.disabled = true;
    try {
        const res = await fetch('/api/admin/roles/catalogo', {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre, rolBase, descripcion })
        });
        const data = await res.json();
        if (!res.ok || !data.success) return avisoRoles('error', data.message || 'No se pudo crear el rol.', 'Error');
        avisoRoles('success', data.message, 'Rol creado');
        document.getElementById('catNombre').value = '';
        document.getElementById('catBase').value = '';
        document.getElementById('catDescripcion').value = '';
        cargarCatalogo();
        cargarHistorial();
    } catch (e) {
        console.error(e);
        avisoRoles('error', 'No se pudo conectar con el servidor.', 'Error');
    } finally {
        btn.disabled = false;
    }
}

async function eliminarRolCatalogo(idRol, nombre) {
    if (window.Swal) {
        const r = await Swal.fire({
            title: `¿Eliminar el rol "${nombre}"?`, icon: 'warning', showCancelButton: true,
            confirmButtonText: 'Sí, eliminar', cancelButtonText: 'Cancelar',
        });
        if (!r.isConfirmed) return;
    }
    try {
        const res = await fetch(`/api/admin/roles/catalogo/${idRol}`, { method: 'DELETE', credentials: 'include' });
        const data = await res.json();
        if (!res.ok || !data.success) return avisoRoles('error', data.message || 'No se pudo eliminar.', 'No se eliminó');
        avisoRoles('success', data.message, 'Rol eliminado');
        cargarCatalogo();
        cargarHistorial();
    } catch (e) {
        console.error(e);
        avisoRoles('error', 'No se pudo conectar con el servidor.', 'Error');
    }
}
