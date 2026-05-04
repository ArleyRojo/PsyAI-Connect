const API = '';
let notificaciones = [];
let notifSeleccionada = null;
const ITEMS_PER_PAGE = 15;
let paginaActualNotifs = 1;
let notifsFiltradas = [];

document.addEventListener('DOMContentLoaded', () => {
    cargarNotificaciones();

    document.getElementById('btnEnviarNotif')?.addEventListener('click', enviarNotificacion);
    document.getElementById('notifDestinatario')?.addEventListener('change', toggleUsuarioIndividual);
    document.getElementById('notifEnvio')?.addEventListener('change', toggleFechaProgramada);
    document.getElementById('notifTitulo')?.addEventListener('input', actualizarPreview);
    document.getElementById('notifMensaje')?.addEventListener('input', actualizarPreview);

    document.getElementById('filtroTipo')?.addEventListener('change', filtrarNotificaciones);
    document.getElementById('filtroDestinatario')?.addEventListener('change', filtrarNotificaciones);
    document.getElementById('filtroEstado')?.addEventListener('change', filtrarNotificaciones);
    document.getElementById('filtroFecha')?.addEventListener('change', filtrarNotificaciones);
});

async function cargarNotificaciones() {
    try {
        const res  = await fetch(`${API}/api/admin/notificaciones`);
        const data = await res.json();
        if (!data.success) return;
        notificaciones = data.notificaciones;

        // Stats dinámicos
        if (data.stats) {
            set('statEnviadas',    data.stats.enviadas);
            set('statProgramadas', data.stats.programadas);
            set('statTasa',        data.stats.tasa);
            set('statAlcanzados',  data.stats.alcanzados);
        }

        // Contadores en tiempo real
        const historial = notificaciones.filter(n => n.estado !== 'pendiente');
        const programadas = notificaciones.filter(n => n.estado === 'pendiente');
        set('cntHistorial', historial.length);
        set('cntProgramadas', programadas.length);

        renderHistorial(historial);
        renderProgramadas(programadas);
        
        // Actualizar stats
        set('statTotal', notificaciones.length);
    } catch(e) {
        console.error('Error notificaciones:', e);
    }
    
    // Actualizar cada 30 segundos
    setTimeout(cargarNotificaciones, 30000);
}

function renderHistorial(lista) {
    notifsFiltradas = lista;
    paginaActualNotifs = 1;
    renderizarPaginaNotifs();
}

function renderizarPaginaNotifs() {
    const tbody = document.getElementById('tablaNotificaciones');
    if (!tbody) return;
    
    const totalNotifs = notifsFiltradas.length;
    const totalPaginas = Math.ceil(totalNotifs / ITEMS_PER_PAGE) || 1;
    const inicio = (paginaActualNotifs - 1) * ITEMS_PER_PAGE;
    const fin = Math.min(inicio + ITEMS_PER_PAGE, totalNotifs);
    const paginaNotifs = notifsFiltradas.slice(inicio, fin);

    if (!totalNotifs) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center table-empty-msg py-4">Sin notificaciones enviadas.</td></tr>';
        document.getElementById('mostrandoInicioNotifs').textContent = 0;
        document.getElementById('mostrandoFinNotifs').textContent = 0;
        document.getElementById('mostrandoTotalNotifs').textContent = 0;
    } else {
        tbody.innerHTML = paginaNotifs.map(n => {
            const estadoTexto = n.estado === 'enviado'
                ? '<span class="estado-dot enviado"></span> <span class="estado-texto-enviado" style="font-size:.82rem;">Enviado</span>'
                : '<span class="estado-dot fallido"></span> <span class="estado-texto-fallido" style="font-size:.82rem;">Fallido</span>';
            
            let tipoBadge;
            if (n.tipo_registro === 'profesional') {
                tipoBadge = '<span class="tipo-badge" style="background:#e3f2fd;color:#1976D2;"><i class="fas fa-user-md"></i> Profesional</span>';
            } else if (n.tipo_registro === 'paciente') {
                tipoBadge = '<span class="tipo-badge" style="background:#e8f5e9;color:#388E3C;"><i class="fas fa-user"></i> Paciente</span>';
            } else {
                tipoBadge = getTipoBadge(n.tipo);
            }
            
            return `
            <tr>
              <td class="ps-4 notif-cell-date">${n.fecha_envio || n.fecha || '—'}</td>
              <td>
                <div class="notif-cell-title">${n.titulo}</div>
                <div class="notif-cell-desc">${(n.mensaje||'').substring(0,60)}${(n.mensaje||'').length>60?'...':''}</div>
              </td>
              <td>${tipoBadge}</td>
              <td>${n.tipo_registro === 'notificacion' ? getDestPill(n.destinatario, n.email_individual) : (n.enviado_por || '—')}</td>
              <td>${estadoTexto}</td>
              <td class="notif-cell-meta">${getEnviadoPorBadge(n.enviado_por)}</td>
              <td class="text-end pe-4">
                <div class="d-flex justify-content-end gap-1">
                  <button class="action-btn view" onclick="verDetalle(${n.idNotificacion})" title="Ver detalle"><i class="fas fa-eye"></i></button>
                  ${n.estado === 'fallido' && n.tipo_registro === 'notificacion' ? `<button class="action-btn send" onclick="reenviar(${n.idNotificacion})" title="Reenviar"><i class="fas fa-redo"></i></button>` : ''}
                  ${n.tipo_registro === 'notificacion' ? `<button class="action-btn delete" onclick="confirmarEliminar(${n.idNotificacion})" title="Eliminar"><i class="fas fa-trash"></i></button>` : ''}
                </div>
              </td>
            </tr>`;
        }).join('');
        document.getElementById('mostrandoInicioNotifs').textContent = inicio + 1;
        document.getElementById('mostrandoFinNotifs').textContent = fin;
        document.getElementById('mostrandoTotalNotifs').textContent = totalNotifs;
    }

    renderizarPaginacionNotifs(totalPaginas);
}

function renderizarPaginacionNotifs(totalPaginas) {
    const container = document.getElementById('paginacionNotifsAdmin');
    if (!container) return;

    let html = '';
    html += `<button class="btn btn-light btn-sm" ${paginaActualNotifs === 1 ? 'disabled' : ''} onclick="cambiarPaginaNotifs(${paginaActualNotifs - 1})"><i class="fas fa-chevron-left"></i></button>`;

    for (let i = 1; i <= totalPaginas; i++) {
        const esActiva = i === paginaActualNotifs;
        const animClass = esActiva ? 'pagination-btn-anim' : '';
        html += `<button class="btn ${esActiva ? 'btn-primary' : 'btn-light'} btn-sm px-3 ${animClass}" onclick="cambiarPaginaNotifs(${i})">${i}</button>`;
    }

    html += `<button class="btn btn-light btn-sm" ${paginaActualNotifs === totalPaginas ? 'disabled' : ''} onclick="cambiarPaginaNotifs(${paginaActualNotifs + 1})"><i class="fas fa-chevron-right"></i></button>`;

    container.innerHTML = html;
}

function cambiarPaginaNotifs(pagina) {
    const totalPaginas = Math.ceil(notifsFiltradas.length / ITEMS_PER_PAGE);
    if (pagina < 1 || pagina > totalPaginas) return;
    paginaActualNotifs = pagina;
    renderizarPaginaNotifs();
}

function renderProgramadas(lista) {
    const tbody = document.querySelector('#tab-programadas tbody');
    if (!tbody) return;
    if (!lista.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center table-empty-msg py-4">Sin notificaciones programadas.</td></tr>';
        return;
    }
    tbody.innerHTML = lista.map(n => `
        <tr>
          <td class="ps-4 notif-cell-date">${n.fecha_programada || n.fecha_envio || '—'}</td>
          <td>
            <div class="notif-cell-title">${n.titulo}</div>
            <div class="notif-cell-desc">${(n.mensaje||'').substring(0,50)}...</div>
          </td>
          <td>${getTipoBadge(n.tipo)}</td>
          <td>${getDestPill(n.destinatario, n.email_individual)}</td>
          <td class="text-end pe-4">
            <div class="d-flex justify-content-end gap-1">
              <button class="action-btn delete" onclick="confirmarEliminar(${n.idNotificacion})" title="Cancelar"><i class="fas fa-trash"></i></button>
            </div>
          </td>
        </tr>`
    ).join('');
}

async function enviarNotificacion() {
    const titulo           = document.getElementById('notifTitulo')?.value.trim();
    const mensaje          = document.getElementById('notifMensaje')?.value.trim();
    const tipo             = document.getElementById('notifTipo')?.value;
    const destinatario     = document.getElementById('notifDestinatario')?.value;
    const envio            = document.getElementById('notifEnvio')?.value;
    const fecha_programada = document.getElementById('notifFecha')?.value || null;
    const email_individual = document.getElementById('notifEmail')?.value.trim() || null;

    if (!titulo || !mensaje || !tipo || !destinatario) {
        mostrarAlerta('error', 'Completa todos los campos requeridos.');
        return;
    }
    try {
        const res  = await fetch(`${API}/api/admin/notificaciones`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify({ titulo, mensaje, tipo, destinatario, envio, fecha_programada, email_individual })
        });
        const data = await res.json();
        if (data.success) {
            mostrarAlerta('success', 'Notificación enviada con éxito.');
            limpiarFormulario();
            cargarNotificaciones();
        } else {
            mostrarAlerta('error', data.message);
        }
    } catch(e) { 
        console.error(e); 
        mostrarAlerta('error', 'Error de conexión.');
    }
}

async function confirmarEliminar(id) {
    if (!confirm('¿Eliminar esta notificación?')) return;
    try {
        const res  = await fetch(`${API}/api/admin/notificaciones/${id}`, {
            method: 'DELETE', headers: {'Content-Type': 'application/json'},
            credentials: 'include'
        });
        const data = await res.json();
        if (data.success) {
            mostrarAlerta('success', 'Notificación eliminada.');
            cargarNotificaciones();
        }
    } catch(e) { 
        console.error(e); 
        mostrarAlerta('error', 'Error de conexión.');
    }
}

function verDetalle(id) {
    const n = notificaciones.find(x => x.idNotificacion === id);
    if (!n) return;
    set('detalleTitle',       n.titulo);
    set('detalleBody',        n.mensaje);
    set('detalleTipo',        n.tipo_registro === 'profesional' ? 'Actividad Profesional' : n.tipo_registro === 'paciente' ? 'Actividad Paciente' : n.tipo);
    set('detalleDestinatario', n.tipo_registro === 'notificacion' ? (n.destinatario === 'individual' ? n.email_individual : n.destinatario) : n.enviado_por);
    set('detalleEnviadoPor',  n.enviado_por || 'Sistema');
    set('detalleFecha',       n.fecha_envio || n.fecha);
    set('detalleEstado',      n.estado);
    new bootstrap.Modal(document.getElementById('modalDetalle')).show();
}

function reenviar(id) {
    mostrarAlerta('success', 'Reenvío registrado.');
}

function toggleUsuarioIndividual() {
    const val  = document.getElementById('notifDestinatario')?.value;
    const campo = document.getElementById('campoIndividual');
    if (campo) campo.style.display = val === 'individual' ? '' : 'none';
}

function toggleFechaProgramada() {
    const val  = document.getElementById('notifEnvio')?.value;
    const campo = document.getElementById('campoFecha');
    const btn   = document.getElementById('btnEnviarNotif');
    if (campo) campo.style.display = val === 'programado' ? '' : 'none';
    if (btn) btn.innerHTML = val === 'programado'
        ? '<i class="fas fa-clock me-2"></i>Programar envío'
        : '<i class="fas fa-paper-plane me-2"></i>Enviar ahora';
}

function actualizarPreview() {
    const titulo  = document.getElementById('notifTitulo')?.value || 'Título de la notificación';
    const mensaje = document.getElementById('notifMensaje')?.value || 'El mensaje aparecerá aquí mientras escribes.';
    set('previewTitulo',  titulo);
    set('previewMensaje', mensaje);
}

function limpiarFormulario() {
    ['notifTitulo','notifMensaje','notifEmail','notifFecha'].forEach(id => {
        const el = document.getElementById(id); if (el) el.value = '';
    });
    ['notifTipo','notifDestinatario','notifEnvio'].forEach(id => {
        const el = document.getElementById(id); if (el) el.selectedIndex = 0;
    });
    actualizarPreview();
}

function mostrarTab(tab, btn) {
    document.querySelectorAll('[id^="tab-"]').forEach(el => el.style.display = 'none');
    const target = document.getElementById(`tab-${tab}`);
    if (target) target.style.display = '';
    document.querySelectorAll('.notif-tab, .logs-tab, .roles-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
}

function getTipoBadge(tipo) {
    const map = {
        sistema:      '<span class="tipo-badge sistema"><i class="fas fa-cog"></i> Sistema</span>',
        cita:         '<span class="tipo-badge cita"><i class="fas fa-calendar-check"></i> Cita</span>',
        recordatorio: '<span class="tipo-badge recordatorio"><i class="fas fa-clock"></i> Recordatorio</span>',
        alerta:       '<span class="tipo-badge alerta"><i class="fas fa-exclamation-triangle"></i> Alerta</span>',
        info:         '<span class="tipo-badge info"><i class="fas fa-info-circle"></i> Info</span>'
    };
    return map[tipo] || `<span class="tipo-badge info">${tipo||'—'}</span>`;
}

function getDestPill(dest, email) {
    const map = {
        todos:         '<span class="recipient-pill all"><i class="fas fa-users"></i> Todos</span>',
        pacientes:     '<span class="recipient-pill paciente"><i class="fas fa-user"></i> Pacientes</span>',
        profesionales: '<span class="recipient-pill profesional"><i class="fas fa-user-md"></i> Profesionales</span>',
        individual:    `<span class="recipient-pill individual"><i class="fas fa-user-circle"></i> ${email || 'Individual'}</span>`
    };
    return map[dest] || `<span class="recipient-pill individual">${dest||'—'}</span>`;
}

function getEnviadoPorBadge(usuario) {
    if (!usuario || usuario === 'Sistema') {
        return '<span class="badge-origin badge-origen-sistema"><i class="fas fa-cog"></i> Sistema</span>';
    }
    return `<span class="badge-origin badge-origen-admin"><i class="fas fa-user-shield"></i> ${usuario}</span>`;
}

function mostrarAlerta(tipo, msg) {
    if (tipo === 'success') {
        PsyAIAlerts.success('Éxito', msg);
    } else {
        PsyAIAlerts.error('Error', msg);
    }
}

function set(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
function filtrarNotificaciones() {
    const tipo   = document.getElementById('filtroTipo')?.value.toLowerCase() || '';
    const dest   = document.getElementById('filtroDestinatario')?.value.toLowerCase() || '';
    const estado = document.getElementById('filtroEstado')?.value.toLowerCase() || '';
    const fecha  = document.getElementById('filtroFecha')?.value || '';

    const filtradas = notificaciones.filter(n => {
        const coincideTipo =
            tipo === '' || (n.tipo && n.tipo.toLowerCase() === tipo);

        const coincideDest =
            dest === '' || (n.destinatario && n.destinatario.toLowerCase() === dest);

        const coincideEstado =
            estado === '' || (n.estado && n.estado.toLowerCase() === estado);

        const coincideFecha =
            fecha === '' || (n.fecha && n.fecha.startsWith(fecha));

        return coincideTipo && coincideDest && coincideEstado && coincideFecha;
    });

    notifsFiltradas = filtradas;
    paginaActualNotifs = 1;
    renderizarPaginaNotifs();
}