// ============================================================
// js/aside-professional/my.agenda.js — Mi Agenda Profesional
// ============================================================

function formatearHora(hora) {
    if (!hora) return '—';
    const partes = hora.split(':');
    const horaNum = parseInt(partes[0]);
    const minutos = partes[1] || '00';
    const periodo = horaNum >= 12 ? 'PM' : 'AM';
    const hora12 = horaNum > 12 ? horaNum - 12 : horaNum === 0 ? 12 : horaNum;
    return `${hora12}:${minutos} ${periodo}`;
}

document.addEventListener('DOMContentLoaded', function() {
    inicializarEventos();
    cargarDatosIniciales();
    inicializarModalCancelar();
});

function inicializarEventos() {
    const btnDisponibilidad = document.getElementById("btnDisponibilidad");
    if (btnDisponibilidad) {
        btnDisponibilidad.addEventListener('click', guardarDisponibilidad);
    }

    const btnAgendar = document.getElementById("btnAgendarCita");
    if (btnAgendar) {
        btnAgendar.addEventListener('click', agendarCita);
    }
}

async function cargarDatosIniciales() {
    await Promise.all([
        cargarPacientes(),
        cargarProfesionales(),
        cargarCitasProfesional()
    ]);
}

// ── Disponibilidad ──────────────────────────────────────────
async function guardarDisponibilidad() {
    const fecha = document.getElementById("fecha").value;
    const horaSeleccionada = document.getElementById("hora_disponible").value;

    if (!fecha || !horaSeleccionada) {
        let camposFaltantes = [];
        if (!fecha) camposFaltantes.push('Fecha');
        if (!horaSeleccionada) camposFaltantes.push('Horario');
        PsyAIAlerts.warning('Campos Requeridos', `Falta: ${camposFaltantes.join(', ')}`);
        return;
    }

    const [hora_inicio, hora_fin] = horaSeleccionada.split('-');

    try {
        const response = await fetch("/api/disponibilidad", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ fecha, hora_inicio, hora_fin })
        });

        const data = await response.json();
        if (data.success) {
            PsyAIAlerts.success('Disponibilidad Creada', 'Tu disponibilidad ha sido configurada correctamente.');
            document.getElementById('fecha').value = '';
            document.getElementById('hora_disponible').value = '';
        } else {
            PsyAIAlerts.error('Error', data.message || 'No se pudo crear la disponibilidad.');
        }
    } catch(err) {
        console.error(err);
        PsyAIAlerts.error('Error', 'Error de conexión.');
    }
}

// ── Cargar Pacientes ─────────────────────────────────────────
async function cargarPacientes() {
    const select = document.getElementById("citaPaciente");
    if (!select) return;

    try {
        const res = await fetch("/api/pacientes", {
            credentials: "include"
        });
        const data = await res.json();

        if (!data.success || !data.pacientes) return;

        select.innerHTML = '<option value="">Seleccionar paciente...</option>';
        data.pacientes.forEach(p => {
            const opt = document.createElement("option");
            opt.value = p.idUsuario;
            opt.textContent = p.nombre;
            select.appendChild(opt);
        });
    } catch(err) {
        console.error(err);
    }
}

// ── Cargar Profesionales ─────────────────────────────────────
async function cargarProfesionales() {
    const select = document.getElementById("citaProfesional");
    if (!select) return;

    try {
        const res = await fetch("/api/profesionales", {
            credentials: "include"
        });
        const data = await res.json();

        if (!data.success || !data.profesionales) return;

        select.innerHTML = '<option value="">Seleccionar profesional...</option>';
        data.profesionales.forEach(p => {
            const opt = document.createElement("option");
            opt.value = p.idUsuario;
            opt.textContent = p.nombre;
            select.appendChild(opt);
        });
    } catch(err) {
        console.error(err);
    }
}


// ── Agendar Cita ────────────────────────────────────────────
async function agendarCita() {
    const idPaciente = document.getElementById("citaPaciente").value;
    const idProfesional = document.getElementById("citaProfesional").value;
    const fecha = document.getElementById("citaFecha").value;
    const hora = document.getElementById("citaHora").value;
    const tipoCita = document.getElementById("citaTipo").value;
    const motivo = document.getElementById("citaMotivo").value;

    if (!idProfesional || !idPaciente || !fecha || !hora || !tipoCita || !motivo) {
        let camposFaltantes = [];
        if (!idProfesional) camposFaltantes.push('Profesional');
        if (!idPaciente) camposFaltantes.push('Paciente');
        if (!fecha) camposFaltantes.push('Fecha');
        if (!hora) camposFaltantes.push('Hora');
        if (!tipoCita) camposFaltantes.push('Tipo de Cita');
        if (!motivo) camposFaltantes.push('Motivo');
        PsyAIAlerts.warning('Campos Requeridos', `Falta: ${camposFaltantes.join(', ')}`);
        return;
    }

    const [horaSeleccion = ""] = hora.split('-');
    const horaEnvio = horaSeleccion || hora;

    try {
        const res = await fetch("/api/citas", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ idPaciente, idProfesional, fecha, hora: horaEnvio, tipoCita, motivo, creado_por_profesional: true })
        });
        const data = await res.json();

        if (data.success) {
            PsyAIAlerts.success('Cita Agendada', 'La cita ha sido creada correctamente.');
            document.getElementById('citaProfesional').value = '';
            document.getElementById('citaPaciente').value = '';
            document.getElementById('citaFecha').value = '';
            document.getElementById('citaHora').value = '';
            document.getElementById('citaTipo').value = '';
            document.getElementById('citaMotivo').value = '';
            cargarCitasProfesional();
        } else {
            PsyAIAlerts.error('Error', data.message || 'No se pudo agendar la cita.');
        }
    } catch(err) {
        console.error(err);
        PsyAIAlerts.error('Error', 'Error de conexión.');
    }
}

// ── Cargar Citas del Profesional ────────────────────────────
async function cargarCitasProfesional() {
    const contenedor = document.getElementById("contenedorCitas");
    const lista = document.getElementById("listaCitas");
    if (!contenedor || !lista) {
        console.error("No se encontró el elemento contenedorCitas o listaCitas");
        return;
    }

    lista.innerHTML = '';
    for (let i = 0; i < 3; i++) {
        const li = document.createElement('li');
        li.className = 'list-group-item skeleton-item';
        li.innerHTML = '<div class="skeleton-shimmer"></div><div class="skeleton-shimmer"></div>';
        lista.appendChild(li);
    }

    try {
        const res = await fetch("/api/citas/profesional", {
            credentials: "include"
        });
        
        if (!res.ok) {
            lista.innerHTML = '<li class="list-group-item text-danger">Error de conexión</li>';
            return;
        }
        
        const data = await res.json();

        if (!data.success || !data.citas || data.citas.length === 0) {
            contenedor.innerHTML = `
                <h5 class="fw-bold text-dark mb-3"><i class="fas fa-clock me-2 text-primary"></i> Citas</h5>
                <ul class="list-group" id="listaCitas">
                    <li class="list-group-item border-0">
                        <div class="empty-agenda">
                            <svg viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <circle cx="60" cy="45" r="22" stroke="%2390CAF9" stroke-width="2" fill="%23E3F2FD"/>
                                <path d="M60 67v8" stroke="%2390CAF9" stroke-width="2" stroke-linecap="round"/>
                                <path d="M60 83v4" stroke="%2390CAF9" stroke-width="2" stroke-linecap="round"/>
                                <rect x="28" y="74" width="64" height="38" rx="6" stroke="%2390CAF9" stroke-width="2" fill="%23F0F5FC"/>
                                <path d="M38 86h44M38 94h28" stroke="%23D6E8FA" stroke-width="2" stroke-linecap="round"/>
                            </svg>
                            <h6>No hay citas programadas</h6>
                            <p>Las citas que registres aparecerán aquí</p>
                        </div>
                    </li>
                </ul>`;
            actualizarStats([]);
            return;
        }

        const citas = data.citas;
        actualizarStats(citas);

        const renderCita = (c) => {
            const inicial = c.paciente ? encodeURIComponent(c.paciente.charAt(0).toUpperCase()) : '?';
            const pacienteId = Number(c.idPaciente);
            const citaId = Number(c.idCita);
            if (!Number.isSafeInteger(citaId) || citaId < 1) return '';
            const fotoUrl = c.foto_perfil 
                ? `/uploads/${c.foto_perfil}` 
                : `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='38' height='38' viewBox='0 0 38 38'%3E%3Ccircle cx='19' cy='19' r='19' fill='%232196F3'/%3E%3Ctext x='19' y='23' text-anchor='middle' fill='white' font-family='Arial' font-size='14' font-weight='bold'%3E${inicial}%3C/text%3E%3C/svg%3E`;
            
            const esCancelada = c.estado === 'Cancelada';
            const creadaPorProfesional = c.creado_por_profesional === true || c.creado_por_profesional === 1 || c.creado_por_profesional === '1';
            
            const origen = creadaPorProfesional
                ? `<span class="badge bg-primary"><i class="fas fa-user-md me-1"></i>Agendado por ti</span>`
                : `<span class="badge bg-info text-dark"><i class="fas fa-calendar me-1"></i>Sistema</span>`;

            const tipoCitaBadge = c.tipoCita 
                ? `<span class="badge" style="background:${c.tipoCita === 'Primera sesión' ? '#e3f2fd' : c.tipoCita === 'Evaluación' ? '#fff3e0' : '#e8f5e9'};color:${c.tipoCita === 'Primera sesión' ? '#1565C0' : c.tipoCita === 'Evaluación' ? '#e65100' : '#2e7d32'};font-weight:600;font-size:0.68rem;border-radius:20px;padding:0.25em 0.6em;">${escapeHtmlAgenda(c.tipoCita)}</span>`
                : '';
            
            let estadoBadge = '';
            let acciones = [];
            if (c.estado === 'Cancelada') {
                estadoBadge = `<span class="badge bg-danger">Cancelada</span>`;
            } else if (c.estado === 'Confirmada') {
                estadoBadge = `<span class="badge bg-success">Confirmada</span>`;
                // Facturar solo si confirmada
                acciones.push(`<a href="facturacion.html?paciente=${Number.isSafeInteger(pacienteId) ? pacienteId : ''}" class="btn btn-outline-primary btn-sm flex-shrink-0" title="Facturar" style="border-radius:8px;font-weight:600;font-size:0.75rem;padding:0.3rem 0.7rem;">
                    <i class="fas fa-file-invoice-dollar me-1"></i>Facturar
                </a>`);
            } else if (c.estado === 'Pendiente') {
                estadoBadge = `<span class="badge bg-warning text-dark">${creadaPorProfesional ? 'Esperando confirmación del paciente' : 'Pendiente de tu confirmación'}</span>`;
                if (!creadaPorProfesional) {
                    acciones.push(`<button class="btn btn-success btn-sm flex-shrink-0" onclick="confirmarCita(${citaId})" title="Confirmar cita" style="border-radius:8px;font-weight:600;font-size:0.75rem;padding:0.3rem 0.7rem;">
                        <i class="fas fa-check me-1"></i>Confirmar
                    </button>`);
                }
                // Cancelar también disponible
                acciones.push(`<button class="btn btn-outline-danger btn-sm flex-shrink-0" onclick="abrirModalCancelarCita(${citaId})" title="Cancelar cita" style="border-radius:8px;font-weight:600;font-size:0.75rem;padding:0.3rem 0.7rem;">
                    <i class="fas fa-ban me-1"></i>Cancelar
                </button>`);
            }
            const canceladaBtn = acciones.length > 0
                ? `<div class="d-flex gap-1 ms-auto flex-shrink-0">${acciones.join('')}</div>`
                : '';

            const horaFormateada = formatearHora(c.hora);

            return `
                <li class="list-group-item d-flex align-items-center gap-2" style="${esCancelada ? 'opacity:0.65;' : ''}">
                    <img src="${escapeHtmlAgenda(fotoUrl)}" alt="${escapeHtmlAgenda(c.paciente)}" class="rounded-circle flex-shrink-0" style="width:38px;height:38px;object-fit:cover;">
                    <div class="flex-grow-1 min-w-0">
                        <div class="d-flex align-items-center gap-2 flex-wrap">
                            <strong>${escapeHtmlAgenda(c.paciente)}</strong>
                            ${tipoCitaBadge}
                            ${estadoBadge}
                            ${origen}
                        </div>
                        <div class="d-flex align-items-center gap-2 mt-1">
                            <small class="text-muted"><i class="far fa-calendar-alt me-1" style="font-size:0.7rem;"></i>${escapeHtmlAgenda(c.fecha)}</small>
                            <small class="text-muted"><i class="far fa-clock me-1" style="font-size:0.7rem;"></i>${horaFormateada}</small>
                        </div>
                        ${c.motivoCancelacion ? `<div class="mt-1"><small class="text-danger"><i class="fas fa-info-circle me-1"></i><strong>Motivo:</strong> ${escapeHtmlAgenda(c.motivoCancelacion)}</small></div>` : ''}
                    </div>
                    ${canceladaBtn}
                </li>
            `;
        };

        let html = '<h5 class="fw-bold text-dark mb-3"><i class="fas fa-clock me-2 text-primary"></i> Citas</h5>';
        html += `<ul class="list-group" id="listaCitas">${citas.map(c => renderCita(c)).join('')}</ul>`;

        contenedor.innerHTML = html;
    } catch(err) {
        console.error(err);
        lista.innerHTML = '<li class="list-group-item text-danger">Error al cargar citas</li>';
    }
}

function escapeHtmlAgenda(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[character]);
}

// ── Actualizar Stats ────────────────────────────────────────
function actualizarStats(citas) {
    const total = citas.length;
    const confirmadas = citas.filter(c => c.estado === 'Confirmada').length;
    const pendientes = citas.filter(c => c.estado === 'Pendiente').length;
    const canceladas = citas.filter(c => c.estado === 'Cancelada').length;

    const hoy = new Date();
    const proximas = citas.filter(c => {
        if (c.estado === 'Cancelada') return false;
        const fechaCita = new Date(c.fecha + 'T' + (c.hora || '00:00'));
        return fechaCita >= hoy;
    }).length;

    const animarNumero = (el, valor) => {
        if (!el) return;
        const original = el.textContent;
        el.textContent = valor;
        el.style.transition = 'transform 0.3s ease';
        el.style.transform = 'scale(1.2)';
        setTimeout(() => { el.style.transform = 'scale(1)'; }, 300);
    };

    animarNumero(document.getElementById('statTotal'), total);
    animarNumero(document.getElementById('statConfirmadas'), confirmadas);
    animarNumero(document.getElementById('statPendientes'), pendientes);
    animarNumero(document.getElementById('statCanceladas'), canceladas);
    animarNumero(document.getElementById('statProximas'), proximas);
}

// ── Modal Cancelar Cita (Profesional) ───────────────────────
let _citaIdACancelar = null;
let _modalCancelarCitaPro = null;

function inicializarModalCancelar() {
    const modalEl = document.getElementById('modalCancelarCitaPro');
    if (!modalEl) return;

    _modalCancelarCitaPro = new bootstrap.Modal(modalEl);

    // Contador de caracteres
    const textarea = document.getElementById('motivoCancelacionPro');
    const counter  = document.getElementById('charCountMotivo');
    if (textarea && counter) {
        textarea.addEventListener('input', () => {
            counter.textContent = textarea.value.length;
        });
    }

    // Limpiar al cerrar
    modalEl.addEventListener('hidden.bs.modal', () => {
        _citaIdACancelar = null;
        if (textarea) textarea.value = '';
        if (counter)  counter.textContent = '0';
    });

    document.getElementById('btnConfirmarCancelarPro').addEventListener('click', confirmarCancelacionProfesional);
}

function abrirModalCancelarCita(idCita) {
    _citaIdACancelar = idCita;
    document.getElementById('motivoCancelacionPro').value = '';
    document.getElementById('charCountMotivo').textContent = '0';
    _modalCancelarCitaPro.show();
}

async function confirmarCita(idCita) {
    try {
        const res = await fetch(`/api/citas/${idCita}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ estado: 'Confirmada' })
        });
        const data = await res.json();
        if (data.success) {
            PsyAIAlerts.success('Cita Confirmada', 'La cita ha sido confirmada y la factura generada.');
            cargarCitasProfesional();
        } else {
            PsyAIAlerts.error('Error', data.message || 'No se pudo confirmar la cita.');
        }
    } catch(err) {
        console.error(err);
        PsyAIAlerts.error('Error', 'Error de conexión.');
    }
}

async function confirmarCancelacionProfesional() {
    if (!_citaIdACancelar) return;

    const motivo = document.getElementById('motivoCancelacionPro').value.trim();
    if (!motivo) {
        PsyAIAlerts.warning('Campo requerido', 'Debes indicar el motivo de la cancelación.');
        return;
    }

    const btn = document.getElementById('btnConfirmarCancelarPro');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Cancelando...';

    try {
        const res = await fetch(`/api/citas/${_citaIdACancelar}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ motivoCancelacion: motivo })
        });
        const data = await res.json();

        _modalCancelarCitaPro.hide();

        if (data.success) {
            PsyAIAlerts.success('Cita Cancelada', 'La cita ha sido cancelada exitosamente.');
            cargarCitasProfesional();
        } else {
            PsyAIAlerts.error('Error', data.message || 'No se pudo cancelar la cita.');
        }
    } catch(err) {
        console.error(err);
        PsyAIAlerts.error('Error', 'Error de conexión.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-ban me-1"></i>Confirmar Cancelación';
    }
}
