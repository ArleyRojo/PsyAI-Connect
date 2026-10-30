const API = '';
let notificaciones = [];
let notifSeleccionada = null;
const ITEMS_PER_PAGE = 15;
let paginaActualNotifs = 1;
let notifsFiltradas = [];
let _notifTimer = null;
let _pageVisible = true;

// Pause auto-refresh when tab is hidden
document.addEventListener('visibilitychange', () => {
    _pageVisible = !document.hidden;
});

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
    // Skip if page is hidden
    if (!_pageVisible) {
        _notifTimer = setTimeout(cargarNotificaciones, 30000);
        return;
    }
    
    try {
        // Clear any existing timer before creating a new one
        if (_notifTimer) {
            clearTimeout(_notifTimer);
            _notifTimer = null;
        }

        const res  = await fetch(`${API}/api/admin/notificaciones`, {
            credentials: 'include',
            cache: 'no-store'
        });
        const data = await res.json();
        if (!data.success) return;
        // Filtrar notificaciones de chatbot (no son notificaciones de sistema)
        notificaciones = data.notificaciones.filter(n => n.tipo !== 'chatbot');

        // Stats dinámicos - usar stats reales de la BD
        if (data.stats) {
            // "Enviadas hoy" es un contador real de hoy
            set('statEnviadas',    data.stats.enviadas_hoy);
            set('statProgramadas', data.stats.programadas);
            set('statTasa',        data.stats.tasa);
            set('statAlcanzados',  data.stats.alcanzados);
            // Total historial para paginación
            window.__totalHistorial = data.stats.total_historial;
        }

        // Contadores en tiempo real
        const historial = notificaciones.filter(n => n.estado !== 'pendiente');
        const programadas = notificaciones.filter(n => n.estado === 'pendiente');
        // Badge de la pestaña usa el total real de la BD
        set('cntHistorial', window.__totalHistorial || historial.length);
        set('cntProgramadas', programadas.length);
        
        renderHistorial(historial);
        renderProgramadas(programadas);
        
        // Actualizar stats
        set('statTotal', notificaciones.length);
    } catch(e) {
        console.error('Error notificaciones:', e);
    }
    
    // Actualizar cada 30 segundos (solo si la página está visible)
    _notifTimer = setTimeout(cargarNotificaciones, 30000);
}

function esc(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&')
        .replace(/</g, '<')
        .replace(/>/g, '>')
        .replace(/"/g, '"')
        .replace(/'/g, '&#039;');
}

function renderHistorial(lista) {
    notifsFiltradas = lista;
    paginaActualNotifs = 1;
    renderizarPaginaNotifs();
}

function renderizarPaginaNotifs() {
    const tbody = document.getElementById('tablaNotificaciones');
    if (!tbody) return;
    
    // Detectar si hay filtros activos
    const hayFiltros = (document.getElementById('filtroTipo')?.value ||
                       document.getElementById('filtroDestinatario')?.value ||
                       document.getElementById('filtroEstado')?.value ||
                       document.getElementById('filtroFecha')?.value);
    
    // Si no hay filtros, usar el total real de la BD; si hay filtros, usar la longitud filtrada
    const totalReal = window.__totalHistorial || 0;
    const totalNotifs = hayFiltros ? notifsFiltradas.length : totalReal;
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
            
            const destinatarioTexto = n.tipo_registro === 'notificacion'
                ? getDestPill(n.destinatario, n.email_individual)
                : n.tipo_registro === 'profesional'
                    ? '<span class="recipient-pill paciente"><i class="fas fa-user"></i> ' + esc(extraerDestinatarioDeMensaje(n.mensaje, 'Paciente: ')) + '</span>'
                    : n.tipo_registro === 'paciente'
                        ? '<span class="recipient-pill profesional"><i class="fas fa-user-md"></i> ' + esc(extraerDestinatarioDeMensaje(n.mensaje, 'Profesional: ')) + '</span>'
                        : esc(n.enviado_por || '—');
            
            return `
            <tr>
              <td class="ps-4 notif-cell-date">${esc(n.fecha_envio || n.fecha || '—')}</td>
              <td>
                <div class="notif-cell-title">${esc(n.titulo)}</div>
                <div class="notif-cell-desc">${esc((n.mensaje||'').substring(0,60))}${(n.mensaje||'').length>60?'...':''}</div>
              </td>
              <td>${tipoBadge}</td>
              <td>${destinatarioTexto}</td>
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
          <td class="ps-4 notif-cell-date">${esc(n.fecha_programada || n.fecha_envio || '—')}</td>
          <td>
            <div class="notif-cell-title">${esc(n.titulo)}</div>
            <div class="notif-cell-desc">${esc((n.mensaje||'').substring(0,50))}...</div>
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
    const btn = document.getElementById('btnEnviarNotif');
    if (btn?.dataset.busy === '1') return; // Prevent double-click
    
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
    
    // UI: loading state
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Enviando...';
    btn.disabled = true;
    btn.dataset.busy = '1';
    
    try {
        // Use PsyAIConnection for automatic CSRF handling
        const data = await PsyAIConnection.post('/api/admin/notificaciones', {
            titulo, mensaje, tipo, destinatario, envio, fecha_programada, email_individual
        });
        if (data.success) {
            if (envio === 'inmediato') {
                mostrarAlerta('success', 'Notificación enviada con éxito.');
                
                // Optimistic update: add to historial immediately without waiting for GET
                const nuevaNotif = {
                    idNotificacion: Date.now(), // temp ID
                    titulo,
                    mensaje,
                    tipo,
                    destinatario,
                    email_individual,
                    estado: 'enviado',
                    enviado_por: 'Admin',
                    tipo_registro: 'notificacion',
                    fecha: new Date().toLocaleString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
                    fecha_orden: new Date().toISOString()
                };
                notificaciones.unshift(nuevaNotif);
                
                // Update badge immediately
                set('cntHistorial', parseInt(document.getElementById('cntHistorial')?.textContent || '0') + 1);
                
                // Switch to Historial tab
                const btnHistorial = document.querySelector('[onclick="mostrarTab(\'historial\', this)"]');
                if (btnHistorial) mostrarTab('historial', btnHistorial);
                
                // Refresh in background (non-blocking)
                cargarNotificaciones();
            } else {
                mostrarAlerta('success', 'Notificación programada correctamente.');
                await cargarNotificaciones();
                const btnProgramadas = document.querySelector('[onclick="mostrarTab(\'programadas\', this)"]');
                if (btnProgramadas) mostrarTab('programadas', btnProgramadas);
            }
            limpiarFormulario();
        } else {
            mostrarAlerta('error', data.message);
        }
    } catch(e) {
        console.error(e);
        const msg = (e && e.message) ? e.message : 'Error de conexión.';
        mostrarAlerta('error', msg);
    } finally {
        // Restore button
        btn.innerHTML = originalHtml;
        btn.disabled = false;
        btn.dataset.busy = '0';
    }
}

async function confirmarEliminar(id) {
    if (!confirm('¿Eliminar esta notificación?')) return;
    try {
        // Use PsyAIConnection for automatic CSRF handling
        const data = await PsyAIConnection.del(`/api/admin/notificaciones/${id}`);
        if (data.success) {
            mostrarAlerta('success', 'Notificación eliminada.');
            cargarNotificaciones();
        }
    } catch(e) { 
        console.error(e); 
        const msg = (e && e.message) ? e.message : 'Error de conexión.';
        mostrarAlerta('error', msg);
    }
}

function verDetalle(id) {
    const n = notificaciones.find(x => x.idNotificacion === id);
    if (!n) return;
    set('detalleTitle',       esc(n.titulo));
    set('detalleBody',        esc(n.mensaje));
    set('detalleTipo',        n.tipo_registro === 'profesional' ? 'Actividad Profesional' : n.tipo_registro === 'paciente' ? 'Actividad Paciente' : n.tipo);
    
    // Mostrar nombre real del destinatario
    let destinatario;
    if (n.tipo_registro === 'notificacion') {
        if (n.email_individual && n.destinatario === 'individual') {
            destinatario = esc(n.email_individual);
        } else if (n.destinatario && ['todos','pacientes','profesionales','individual'].includes(n.destinatario)) {
            const labels = {todos:'Todos los usuarios', pacientes:'Solo pacientes', profesionales:'Solo profesionales', individual:'Individual'};
            destinatario = labels[n.destinatario] || n.destinatario;
        } else {
            destinatario = esc(n.destinatario || '—');
        }
    } else if (n.tipo_registro === 'profesional') {
        destinatario = esc(extraerDestinatarioDeMensaje(n.mensaje, 'Paciente: ') || n.enviado_por || '—');
    } else if (n.tipo_registro === 'paciente') {
        destinatario = esc(extraerDestinatarioDeMensaje(n.mensaje, 'Profesional: ') || n.enviado_por || '—');
    } else {
        destinatario = esc(n.enviado_por || '—');
    }
    set('detalleDestinatario', destinatario);
    
    set('detalleEnviadoPor',  esc(n.enviado_por || 'Sistema'));
    set('detalleFecha',       esc(n.fecha_envio || n.fecha));
    set('detalleEstado',      esc(n.estado));
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
    set('previewTitulo',  esc(titulo));
    set('previewMensaje', esc(mensaje));
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
    if (target) {
        target.style.display = '';
        target.style.opacity = '1';
        target.style.transform = 'none';
    }
    document.querySelectorAll('.admin-panel-tab').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
    });
    if (btn) {
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
    }
}

function extraerDestinatarioDeMensaje(mensaje, prefijo) {
    if (!mensaje) return '—';
    const idx = mensaje.indexOf(prefijo);
    if (idx === -1) return '—';
    return mensaje.substring(idx + prefijo.length).trim();
}

function getTipoBadge(tipo) {
    const key = (tipo || '').toLowerCase();
    const map = {
        sistema:      '<span class="tipo-badge sistema"><i class="fas fa-cog"></i> Sistema</span>',
        cita:         '<span class="tipo-badge cita"><i class="fas fa-calendar-check"></i> Cita</span>',
        recordatorio: '<span class="tipo-badge recordatorio"><i class="fas fa-clock"></i> Recordatorio</span>',
        alerta:       '<span class="tipo-badge alerta"><i class="fas fa-exclamation-triangle"></i> Alerta</span>',
        info:         '<span class="tipo-badge info"><i class="fas fa-info-circle"></i> Info</span>',
        seguimiento:  '<span class="tipo-badge seguimiento"><i class="fas fa-eye"></i> Seguimiento</span>'
    };
    return map[key] || `<span class="tipo-badge info">${esc(tipo||'—')}</span>`;
}

function getDestPill(dest, email) {
    const map = {
        todos:         '<span class="recipient-pill all"><i class="fas fa-users"></i> Todos</span>',
        pacientes:     '<span class="recipient-pill paciente"><i class="fas fa-user"></i> Pacientes</span>',
        profesionales: '<span class="recipient-pill profesional"><i class="fas fa-user-md"></i> Profesionales</span>',
        individual:    `<span class="recipient-pill individual"><i class="fas fa-user-circle"></i> ${esc(email || 'Individual')}</span>`
    };
    return map[dest] || `<span class="recipient-pill individual"><i class="fas fa-user-circle"></i> ${esc(dest || '—')}</span>`;
}

function getEnviadoPorBadge(usuario) {
    if (!usuario || usuario === 'Sistema') {
        return '<span class="badge-origin badge-origen-sistema"><i class="fas fa-cog"></i> Sistema</span>';
    }
    return `<span class="badge-origin badge-origen-admin"><i class="fas fa-user-shield"></i> ${esc(usuario)}</span>`;
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
    const fecha  = document.getElementById('filtroFecha')?.value || ''; // YYYY-MM-DD

    // Convertir YYYY-MM-DD a dd/mm/YYYY para comparar con n.fecha
    let fechaFormateada = '';
    if (fecha) {
        const parts = fecha.split('-');
        if (parts.length === 3) {
            fechaFormateada = `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
    }

    const filtradas = notificaciones.filter(n => {
        // Excluir pendientes del historial (van a Programadas)
        if (n.estado === 'pendiente') return false;

        const coincideTipo =
            tipo === '' || (n.tipo && n.tipo.toLowerCase() === tipo);

        const coincideDest =
            dest === '' || (n.destinatario && n.destinatario.toLowerCase() === dest);

        const coincideEstado =
            estado === '' || (n.estado && n.estado.toLowerCase() === estado);

        const coincideFecha =
            fechaFormateada === '' || (n.fecha && n.fecha.startsWith(fechaFormateada));

        return coincideTipo && coincideDest && coincideEstado && coincideFecha;
    });

    notifsFiltradas = filtradas;
    paginaActualNotifs = 1;
    renderizarPaginaNotifs();
}