const API = '';
let usuarios = [];
let usuarioSeleccionado = null;
const ITEMS_PER_PAGE = 15;
let paginaActualUsuarios = 1;
let usuariosFiltrados = [];

document.addEventListener('DOMContentLoaded', () => {
    cargarUsuarios();
    document.getElementById('buscarUsuarioInput')?.addEventListener('input', filtrarTabla);
    document.getElementById('filtroRol')?.addEventListener('change', filtrarTabla);
    document.getElementById('filtroEstado')?.addEventListener('change', filtrarTabla);
    document.getElementById('btnConfirmarBloqueo')?.addEventListener('click', confirmarBloqueo);
    document.getElementById('btnConfirmarEliminar')?.addEventListener('click', confirmarEliminar);
});

async function cargarUsuarios() {
    const res  = await fetch(`${API}/api/admin/usuarios`, {
        credentials: "include"
    });
    const data = await res.json();
    if (data.success) {
        usuarios = data.usuarios;
        renderTabla(usuarios);

        // Stats
        const total     = data.usuarios.length;
        const activos   = data.usuarios.filter(u => parseInt(u.activo) === 1 && (u.estadoCuenta === 'Activa' || !u.estadoCuenta)).length;
        const suspendidos = data.usuarios.filter(u => parseInt(u.activo) === 0 || u.estadoCuenta === 'Suspendida').length;

        document.getElementById('statTotal').textContent     = total;
        document.getElementById('statActivos').textContent   = activos;
        document.getElementById('statSuspendidos').textContent = suspendidos;

        document.getElementById('cntTodos').textContent      = total;
        document.getElementById('cntActivos').textContent    = activos;
        document.getElementById('cntSuspendidos').textContent = suspendidos;

        // Actualizar badge de suspendidos en el sidebar
        actualizarBadgeSidebarSuspendidos(suspendidos);
    }
}

function renderTabla(lista) {
    usuariosFiltrados = lista;
    paginaActualUsuarios = 1;
    renderizarPaginaUsuarios();
}

function renderizarPaginaUsuarios() {
    const tbody = document.querySelector('#tablaUsuarios tbody');
    if (!tbody) return;
    
    const totalUsuarios = usuariosFiltrados.length;
    const totalPaginas = Math.ceil(totalUsuarios / ITEMS_PER_PAGE) || 1;
    const inicio = (paginaActualUsuarios - 1) * ITEMS_PER_PAGE;
    const fin = Math.min(inicio + ITEMS_PER_PAGE, totalUsuarios);
    const paginaUsuarios = usuariosFiltrados.slice(inicio, fin);

    if (totalUsuarios === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No hay usuarios registrados.</td></tr>';
        document.getElementById('mostrandoInicio').textContent = 0;
        document.getElementById('mostrandoFin').textContent = 0;
        document.getElementById('mostrandoTotal').textContent = 0;
    } else {
        tbody.innerHTML = paginaUsuarios.map(u => {
            const iniciales  = u.nombre.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase();
            const rolBadge   = u.rol === 'profesional'
                ? '<span class="badge-rol badge-rol-profesional"><i class="fas fa-user-md"></i> Profesional</span>'
                : u.rol === 'admin'
                ? '<span class="badge-rol badge-rol-admin"><i class="fas fa-user-shield"></i> Admin</span>'
                : '<span class="badge-rol badge-rol-paciente"><i class="fas fa-user"></i> Paciente</span>';
            const activoNum  = parseInt(u.activo);
            const estado = u.estadoCuenta || 'Activa';
            let estadoBadge, btnToggle;
            if (estado === 'Pendiente' || estado === 'Verificacion') {
                estadoBadge = '<span class="badge bg-warning text-dark">Pendiente</span>';
                btnToggle = `<button class="btn btn-sm btn-outline-success" onclick="abrirBloqueo(${u.idUsuario},'${u.nombre}','activar')" title="Activar"><i class="fas fa-check"></i></button>`;
            } else if (activoNum === 0 || estado === 'Suspendida') {
                estadoBadge = '<span class="badge bg-danger">Suspendido</span>';
                btnToggle = `<button class="btn btn-sm btn-outline-success" onclick="abrirBloqueo(${u.idUsuario},'${u.nombre}','activar')" title="Activar"><i class="fas fa-check"></i></button>`;
            } else {
                estadoBadge = '<span class="badge bg-success">Activo</span>';
                btnToggle = `<button class="btn btn-sm btn-outline-warning" onclick="abrirBloqueo(${u.idUsuario},'${u.nombre}','suspender')" title="Suspender"><i class="fas fa-ban"></i></button>`;
            }

            return `
            <tr>
              <td class="ps-4">
                <div class="d-flex align-items-center gap-2">
                  <div style="width:36px;height:36px;border-radius:50%;background:#e8f0fe;color:#1565C0;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.82rem;">${iniciales}</div>
                  <div>
                    <div class="fw-semibold" style="font-size:.9rem;">${u.nombre}</div>
                    <div class="text-muted" style="font-size:.78rem;">${u.email}</div>
                  </div>
                </div>
              </td>
              <td>${rolBadge}</td>
              <td>${estadoBadge}</td>
              <td class="text-muted" style="font-size:.82rem;">${u.fechaRegistro || '—'}</td>
              <td class="text-muted" style="font-size:.82rem;">${u.ultimoAcceso || '—'}</td>
              <td class="text-end pe-4">
                <div class="d-flex justify-content-end gap-1">
                  <button class="btn btn-sm btn-outline-primary" onclick="abrirEditar(${u.idUsuario},'${u.nombre}','${u.email}','${u.rol}','${u.estadoCuenta || 'Activa'}')" title="Editar"><i class="fas fa-edit"></i></button>
                  <button class="btn btn-sm btn-outline-danger" onclick="abrirEliminar(${u.idUsuario},'${u.nombre}')" title="Eliminar"><i class="fas fa-trash"></i></button>
                  ${btnToggle}
                </div>
              </td>
            </tr>`;
        }).join('');
        document.getElementById('mostrandoInicio').textContent = inicio + 1;
        document.getElementById('mostrandoFin').textContent = fin;
        document.getElementById('mostrandoTotal').textContent = totalUsuarios;
    }

    renderizarPaginacionUsuarios(totalPaginas);
}

function renderizarPaginacionUsuarios(totalPaginas) {
    const container = document.getElementById('paginacionUsuarios');
    if (!container) return;

    let html = '';
    html += `<button class="btn btn-light btn-sm" ${paginaActualUsuarios === 1 ? 'disabled' : ''} onclick="cambiarPaginaUsuarios(${paginaActualUsuarios - 1})"><i class="fas fa-chevron-left"></i></button>`;

    for (let i = 1; i <= totalPaginas; i++) {
        const esActiva = i === paginaActualUsuarios;
        const animClass = esActiva ? 'pagination-btn-anim' : '';
        html += `<button class="btn ${esActiva ? 'btn-primary' : 'btn-light'} btn-sm px-3 ${animClass}" onclick="cambiarPaginaUsuarios(${i})">${i}</button>`;
    }

    html += `<button class="btn btn-light btn-sm" ${paginaActualUsuarios === totalPaginas ? 'disabled' : ''} onclick="cambiarPaginaUsuarios(${paginaActualUsuarios + 1})"><i class="fas fa-chevron-right"></i></button>`;

    container.innerHTML = html;
}

function cambiarPaginaUsuarios(pagina) {
    const totalPaginas = Math.ceil(usuariosFiltrados.length / ITEMS_PER_PAGE);
    if (pagina < 1 || pagina > totalPaginas) return;
    paginaActualUsuarios = pagina;
    renderizarPaginaUsuarios();
}

function filtrarTabla() {
    const texto  = document.getElementById('buscarUsuarioInput')?.value.toLowerCase() || '';
    const rol    = document.getElementById('filtroRol')?.value || '';
    const estado = document.getElementById('filtroEstado')?.value || '';
    
    const filtrados = usuarios.filter(u => {
        const coincideTexto  = u.nombre.toLowerCase().includes(texto) || u.email.toLowerCase().includes(texto);
        const coincideRol    = rol === '' || u.rol === rol;
        const coincideEstado = estado === '' ||
            (estado === 'activo' && parseInt(u.activo) === 1 && (u.estadoCuenta === 'Activa' || !u.estadoCuenta)) ||
            (estado === 'suspendido' && (parseInt(u.activo) === 0 || u.estadoCuenta === 'Suspendida'));
        return coincideTexto && coincideRol && coincideEstado;
    });

    usuariosFiltrados = filtrados;
    paginaActualUsuarios = 1;
    renderizarPaginaUsuarios();
}
function actualizarContador(n) {
    const el = document.getElementById('contadorUsuarios');
    if (el) el.textContent = `${n} usuarios encontrados`;
}

async function guardarNuevoUsuario() {
    const nombre      = (document.getElementById('nuevoNombre')?.value.trim() + ' ' +
                        document.getElementById('nuevoApellido')?.value.trim()).trim();
    const email       = document.getElementById('nuevoCorreo')?.value.trim();
    const rol         = document.getElementById('nuevoRol')?.value;
    const contrasena  = document.getElementById('nuevoPassword')?.value.trim();
    const contrasena2 = document.getElementById('nuevoPassword2')?.value.trim();

    if (!nombre || !email || !rol || !contrasena) {
        let camposFaltantes = [];
        if (!nombre) camposFaltantes.push('Nombre');
        if (!email) camposFaltantes.push('Correo');
        if (!rol) camposFaltantes.push('Rol');
        if (!contrasena) camposFaltantes.push('Contraseña');
        PsyAIAlerts.warning('Campos Requeridos', `Falta: ${camposFaltantes.join(', ')}`);
        return;
    }
    if (contrasena !== contrasena2) {
        PsyAIAlerts.error('Error', 'Las contraseñas no coinciden');
        return;
    }
    if (contrasena.length < 8) {
        PsyAIAlerts.error('Error', 'La contraseña debe tener al menos 8 caracteres');
        return;
    }

    try {
        const res  = await fetch(`${API}/api/admin/usuarios`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ nombre, email, rol, contrasena })
        });
        const data = await res.json();
        if (data.success) {
            PsyAIAlerts.success('Usuario Creado', data.message || 'Usuario creado correctamente');
            document.getElementById('formNuevoUsuario').reset();
            cargarUsuarios();
            setTimeout(() => {
                mostrarTabUsuarios('todos', document.querySelector('.users-tab, .logs-tab'));
            }, 1000);
        } else {
            PsyAIAlerts.error('Error', data.message || 'No se pudo crear el usuario');
        }
    } catch(e) {
        console.error(e);
        PsyAIAlerts.error('Error', 'Error de conexión');
    }
}
function abrirEditar(id, nombre, email, rol, estado) {
    usuarioSeleccionado = { idUsuario: id };
    document.getElementById('editId').value    = id;
    document.getElementById('editNombre').value = nombre;
    document.getElementById('editCorreo').value = email;
    document.getElementById('editEstado').value = estado || 'Activa';
    new bootstrap.Modal(document.getElementById('modalEditarUsuario')).show();
}

async function guardarEdicion() {
    const nombre = document.getElementById('editNombre')?.value.trim();
    const email  = document.getElementById('editCorreo')?.value.trim();
    const estado = document.getElementById('editEstado')?.value;

    if (!nombre || !email) {
        PsyAIAlerts.warning('Campos Requeridos', 'Nombre y correo son obligatorios');
        return;
    }

    const res = await fetch(`${API}/api/admin/usuarios/${usuarioSeleccionado.idUsuario}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ nombre, email, estado })
    });
    const data = await res.json();
    if (data.success) {
        bootstrap.Modal.getInstance(document.getElementById('modalEditarUsuario'))?.hide();
        PsyAIAlerts.success('Actualizado', 'Usuario actualizado correctamente');
        cargarUsuarios();
    } else {
        PsyAIAlerts.error('Error', data.message);
    }
}

function abrirEliminar(id, nombre) {
    usuarioSeleccionado = { idUsuario: id };
    document.getElementById('eliminarNombreUsuario').textContent = nombre;
    new bootstrap.Modal(document.getElementById('modalEliminarUsuario')).show();
}

async function confirmarEliminar() {
    const res = await fetch(`${API}/api/admin/usuarios/${usuarioSeleccionado.idUsuario}`, {
        method: 'DELETE', headers: {'Content-Type': 'application/json'},
        credentials: 'include'
    });
    const data = await res.json();
    if (data.success) {
        bootstrap.Modal.getInstance(document.getElementById('modalEliminarUsuario'))?.hide();
        PsyAIAlerts.success('Eliminado', 'Usuario eliminado correctamente');
        cargarUsuarios();
    } else {
        PsyAIAlerts.error('Error', data.message);
    }
}

function abrirBloqueo(id, nombre, accion) {
    usuarioSeleccionado = { idUsuario: id, accion };
    const textoAccion = accion === 'suspender' ? 'suspender' : 'reestablecer';
    document.getElementById('bloqueoAccion').textContent = textoAccion;
    document.getElementById('bloqueoNombre').textContent = nombre;
    new bootstrap.Modal(document.getElementById('modalBloqueo')).show();
}

async function confirmarBloqueo() {
    const res = await fetch(`${API}/api/admin/usuarios/${usuarioSeleccionado.idUsuario}/bloquear`, {
        method: 'PATCH', headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify({ accion: usuarioSeleccionado.accion })
    });
    const data = await res.json();
    if (data.success) {
        bootstrap.Modal.getInstance(document.getElementById('modalBloqueo'))?.hide();
        const msg = usuarioSeleccionado.accion === 'suspender' ? 'Usuario suspendido' : 'Cuenta reestablecida';
        PsyAIAlerts.success('Actualizado', msg);
        cargarUsuarios();
    } else {
        PsyAIAlerts.error('Error', data.message);
    }
}

function mostrarTabUsuarios(tab, btn) {
    ['todos','activos','suspendidos','nuevo'].forEach(t => {
        const el = document.getElementById('tab-u-' + t);
        if (el) el.style.display = 'none';
    });
    document.querySelectorAll('.users-tab, .logs-tab').forEach(b => b.classList.remove('active'));
    const target = document.getElementById('tab-u-' + tab);
    if (target) target.style.display = 'block';
    if (btn) btn.classList.add('active');

    if (tab === 'todos') {
        renderTabla(usuarios);
    } else if (tab === 'activos') {
        const activos = usuarios.filter(u => parseInt(u.activo) === 1 && (u.estadoCuenta === 'Activa' || !u.estadoCuenta));
        renderTablaFiltrada('tab-u-activos', activos);
    } else if (tab === 'suspendidos') {
        const suspendidos = usuarios.filter(u => parseInt(u.activo) === 0 || u.estadoCuenta === 'Suspendida');
        renderTablaFiltrada('tab-u-suspendidos', suspendidos);
    }
}

function renderTablaFiltrada(tabId, lista) {
    const tbody = document.querySelector('#' + tabId + ' tbody');
    if (!tbody) return;

    if (lista.length === 0) {
        const colspan = tabId === 'tab-u-suspendidos' ? 5 : 5;
        tbody.innerHTML = `<tr><td colspan="${colspan}" class="text-center text-muted py-3">No hay usuarios en esta categoría</td></tr>`;
        return;
    }

    if (tabId === 'tab-u-suspendidos') {
        tbody.innerHTML = lista.map(u => {
            const iniciales = u.nombre.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase();
            const rolBadge  = u.rol === 'profesional'
                ? '<span class="badge-rol badge-rol-profesional"><i class="fas fa-user-md"></i> Profesional</span>'
                : u.rol === 'admin'
                ? '<span class="badge-rol badge-rol-admin"><i class="fas fa-user-shield"></i> Admin</span>'
                : '<span class="badge-rol badge-rol-paciente"><i class="fas fa-user"></i> Paciente</span>';
            
            return `
            <tr>
              <td class="ps-4">
                <div class="d-flex align-items-center gap-2">
                  <div style="width:36px;height:36px;border-radius:50%;background:#ffebee;color:#c62828;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.82rem;">${iniciales}</div>
                  <div>
                    <div class="fw-semibold">${u.nombre}</div>
                    <div class="text-muted" style="font-size:.78rem;">${u.email}</div>
                  </div>
                </div>
              </td>
              <td>${rolBadge}</td>
              <td class="text-muted">${u.motivoSuspension || 'No especificado'}</td>
              <td class="text-muted">${u.fechaSuspension || u.fechaRegistro || '—'}</td>
              <td class="text-end pe-4">
                <button class="btn btn-sm btn-outline-success" onclick="abrirBloqueo(${u.idUsuario},'${u.nombre}','activar')" title="Reestablecer"><i class="fas fa-check"></i> Reestablecer</button>
              </td>
            </tr>`;
        }).join('');
        return;
    }

    tbody.innerHTML = lista.map(u => {
        const iniciales = u.nombre.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase();
        const rolBadge  = u.rol === 'profesional'
            ? '<span class="badge-rol badge-rol-profesional"><i class="fas fa-user-md"></i> Profesional</span>'
            : u.rol === 'admin'
            ? '<span class="badge-rol badge-rol-admin"><i class="fas fa-user-shield"></i> Admin</span>'
            : '<span class="badge-rol badge-rol-paciente"><i class="fas fa-user"></i> Paciente</span>';
        
        const activoNum = parseInt(u.activo);
        const btnToggle = activoNum === 0
            ? `<button class="btn btn-sm btn-outline-success" onclick="abrirBloqueo(${u.idUsuario},'${u.nombre}','activar')" title="Activar"><i class="fas fa-check"></i></button>`
            : `<button class="btn btn-sm btn-outline-warning" onclick="abrirBloqueo(${u.idUsuario},'${u.nombre}','suspender')" title="Suspender"><i class="fas fa-ban"></i></button>`;

        return `
        <tr>
          <td class="ps-4">
            <div class="d-flex align-items-center gap-2">
              <div style="width:36px;height:36px;border-radius:50%;background:#e8f0fe;color:#1565C0;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.82rem;">${iniciales}</div>
              <div>
                <div class="fw-semibold">${u.nombre}</div>
                <div class="text-muted" style="font-size:.78rem;">${u.email}</div>
              </div>
            </div>
          </td>
          <td>${rolBadge}</td>
          <td class="text-muted">${u.fechaRegistro || '—'}</td>
          <td class="text-muted">${u.ultimoAcceso || '—'}</td>
          <td class="text-end pe-4">
            <div class="d-flex justify-content-end gap-1">
              <button class="btn btn-sm btn-outline-primary" onclick="abrirEditar(${u.idUsuario},'${u.nombre}','${u.email}','${u.rol}','${u.estadoCuenta || 'Activa'}')" title="Editar"><i class="fas fa-edit"></i></button>
              <button class="btn btn-sm btn-outline-danger" onclick="abrirEliminar(${u.idUsuario},'${u.nombre}')" title="Eliminar"><i class="fas fa-trash"></i></button>
              ${btnToggle}
            </div>
          </td>
        </tr>`;
    }).join('');
}

function actualizarBadgeSidebarSuspendidos(cantidad) {
    const badge = document.getElementById('sidebarSuspendidos');
    if (!badge) return;
    if (cantidad > 0) {
        badge.textContent = cantidad;
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }
}