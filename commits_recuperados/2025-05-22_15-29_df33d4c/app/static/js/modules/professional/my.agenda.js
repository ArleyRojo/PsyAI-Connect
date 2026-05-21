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

    const citaProfesional = document.getElementById("citaProfesional");
    if (citaProfesional) {
        citaProfesional.addEventListener('change', () => {
            const selectHora = document.getElementById("citaHora");
            if (selectHora) {
                selectHora.innerHTML = '<option value="">Selecciona una fecha primero</option>';
            }
            cargarHorariosDisponibles();
        });
    }

    const citaFecha = document.getElementById("citaFecha");
    if (citaFecha) {
        citaFecha.addEventListener('change', () => {
            cargarHorariosDisponibles();
        });
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

// ── Cargar Horarios Disponibles ──────────────────────────────
async function cargarHorariosDisponibles() {
    const idProfesional = document.getElementById("citaProfesional").value;
    const fecha = document.getElementById("citaFecha").value;
    const select = document.getElementById("citaHora");

    if (!select) return;

    if (!idProfesional || !fecha) {
        select.innerHTML = '<option value="">Selecciona profesional y fecha</option>';
        return;
    }

    select.innerHTML = '<option value="">Cargando...</option>';

    try {
        const res = await fetch(`/api/citas/disponibles?idProfesional=${encodeURIComponent(idProfesional)}&fecha=${encodeURIComponent(fecha)}`, {
            credentials: "include"
        });
        const data = await res.json();
        const horariosDisponibles = data.horarios || [];

        if (horariosDisponibles.length === 0) {
            select.innerHTML = '<option value="">No hay horarios disponibles para esta fecha</option>';
            return;
        }

        const formatHora = (hora) => {
            const [h, m] = hora.split(':').map(Number);
            const esPM = h >= 12;
            const hora12 = h > 12 ? h - 12 : h === 0 ? 12 : h;
            const ampm = esPM ? 'PM' : 'AM';
            return `${hora12}:${String(m).padStart(2, '0')} ${ampm}`;
        };

        const formatHoraFin = (hora) => {
            const [h, m] = hora.split(':').map(Number);
            let horaFin = h;
            let minFin = m + 30;
            if (minFin >= 60) {
                minFin = 0;
                horaFin = h + 1;
            }
            const esPM = horaFin >= 12;
            const hora12 = horaFin > 12 ? horaFin - 12 : horaFin;
            const ampm = esPM ? 'PM' : 'AM';
            return `${hora12}:${String(minFin).padStart(2, '0')} ${ampm}`;
        };

        select.innerHTML = '<option value="">Selecciona una hora</option>';

        horariosDisponibles.forEach(hora => {
            const opt = document.createElement("option");
            opt.value = hora;
            opt.textContent = `${formatHora(hora)} - ${formatHoraFin(hora)}`;
            select.appendChild(opt);
        });

    } catch(err) {
        console.error("Error cargando horarios:", err);
        select.innerHTML = '<option value="">Error al cargar</option>';
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

    try {
        const res = await fetch("/api/citas", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ idPaciente, idProfesional, fecha, hora, tipoCita, motivo, creado_por_profesional: true })
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

    lista.innerHTML = '<li class="list-group-item text-muted">Cargando...</li>';

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
                    <li class="list-group-item text-muted">No hay citas programadas</li>
                </ul>`;
            return;
        }

        console.log("Citas recibidas:", data.citas);

        const renderCita = (c) => {
            const inicial = c.paciente ? c.paciente.charAt(0).toUpperCase() : '?';
            const fotoUrl = c.foto_perfil 
                ? `/uploads/${c.foto_perfil}` 
                : `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='35' height='35' viewBox='0 0 35 35'%3E%3Ccircle cx='17.5' cy='17.5' r='17.5' fill='%232196F3'/%3E%3Ctext x='17.5' y='21' text-anchor='middle' fill='white' font-family='Arial' font-size='12'%3E${inicial}%3C/text%3E%3C/svg%3E`;
            
            const agendoPor = (c.creado_por_profesional === true || c.creado_por_profesional === 1 || c.creado_por_profesional === '1')
                ? `<span class="badge bg-primary"><i class="fas fa-user-md me-1"></i>Agendado por ti</span>`
                : `<span class="badge bg-info text-dark"><i class="fas fa-calendar me-1"></i>Sistema</span>`;
            
            const canceladaBtn = c.estado !== 'Cancelada'
                ? `<button class="btn btn-outline-danger btn-sm ms-auto" onclick="abrirModalCancelarCita(${c.idCita})" title="Cancelar cita">
                       <i class="fas fa-ban me-1"></i>Cancelar
                   </button>`
                : '';

            const estadoBadge = c.estado === 'Cancelada' 
                ? `<span class="badge bg-danger">Cancelada</span>`
                : `<span class="badge bg-success">Confirmada</span>`;

            return `
                <li class="list-group-item d-flex align-items-center gap-2">
                    <img src="${fotoUrl}" alt="Foto" class="rounded-circle flex-shrink-0" style="width:35px;height:35px;object-fit:cover;">
                    <div class="flex-grow-1">
                        <strong>${c.paciente}</strong> — ${c.fecha} ${formatearHora(c.hora)}<br>
                        <small class="text-muted">${c.tipoCita}</small>
                        ${estadoBadge}
                        ${agendoPor}
                        ${c.motivoCancelacion ? `<div class="mt-1"><small class="text-danger"><i class="fas fa-info-circle me-1"></i><strong>Motivo cancelación:</strong> ${c.motivoCancelacion}</small></div>` : ''}
                    </div>
                    ${canceladaBtn}
                </li>
            `;
        };

        let html = '<h5 class="fw-bold text-dark mb-3"><i class="fas fa-clock me-2 text-primary"></i> Citas</h5>';
        html += `<ul class="list-group">${data.citas.map(c => renderCita(c)).join('')}</ul>`;

        contenedor.innerHTML = html;
    } catch(err) {
        console.error(err);
        lista.innerHTML = '<li class="list-group-item text-danger">Error al cargar citas</li>';
    }
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
        const res = await fetch(`/api/citas/profesional/${_citaIdACancelar}/cancelar`, {
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
