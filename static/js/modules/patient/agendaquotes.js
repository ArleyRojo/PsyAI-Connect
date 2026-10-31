function formatearHora(hora) {
  if (!hora) return '—';
  const partes = hora.split(':');
  const horaNum = parseInt(partes[0]);
  const minutos = parseInt(partes[1]) || 0;
  const periodo = horaNum >= 12 ? 'PM' : 'AM';
  const hora12 = horaNum === 0 ? 12 : horaNum > 12 ? horaNum - 12 : horaNum;
  // 1‑hour block
  const horaFin = horaNum + 1;
  const horaFin12 = horaFin === 0 ? 12 : horaFin > 12 ? horaFin - 12 : horaFin;
  const minFinStr = String(minutos).padStart(2, '0');
  return `${hora12}:${minFinStr} - ${horaFin12}:${minFinStr} ${periodo}`;
}

function formatearHoraCorta(hora) {
  if (!hora) return '—';
  const partes = hora.split(':');
  const horaNum = parseInt(partes[0]);
  const minutos = partes[1] || '00';
  const periodo = horaNum >= 12 ? 'PM' : 'AM';
  const hora12 = horaNum > 12 ? horaNum - 12 : horaNum === 0 ? 12 : horaNum;
  return `${hora12}:${minutos} ${periodo}`;
}

function avanzarStep(n) {
  document.querySelectorAll('.step-panel').forEach(function(p) { p.classList.add('d-none'); });
  document.getElementById('stepPanel' + n).classList.remove('d-none');
  document.querySelectorAll('.step-item').forEach(function(item) {
    var step = parseInt(item.getAttribute('data-step'));
    item.classList.toggle('active', step <= n);
  });
}

let _citasHistorialGlobal = [];

// ============================================================
// CALENDARIO
// ============================================================
let calMes, calAnio, calFechasDisponibles = [], calFechaSeleccionada = '', calFechaSinHorarios = '';

function iniciarCalendario() {
  const hoy = new Date();
  calMes  = hoy.getMonth() + 1;
  calAnio = hoy.getFullYear();
}

async function renderCalendario() {
  const idProfesional = document.getElementById('profesional').value;
  const container     = document.getElementById('diasCalendario');
  const label         = document.getElementById('labelMes');
  const meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
  label.textContent = `${meses[calMes - 1]} ${calAnio}`;

  if (!idProfesional) {
    container.innerHTML = '<span style="font-size:.8rem;color:#aaa;grid-column:span 7">Selecciona un profesional primero</span>';
    return;
  }

  container.innerHTML = '<span style="font-size:.8rem;color:#aaa;grid-column:span 7">Cargando...</span>';

  try {
    const res  = await fetch(`/api/citas/fechas-disponibles?idProfesional=${encodeURIComponent(idProfesional)}&anio=${calAnio}&mes=${calMes}`, {
      credentials: 'include'
    });
    const data = await res.json();
    calFechasDisponibles = data.fechas || [];
  } catch(e) {
    calFechasDisponibles = [];
  }
  dibujarDias();
}

function dibujarDias() {
  const container  = document.getElementById('diasCalendario');
  container.innerHTML = '';
  const primerDia  = new Date(calAnio, calMes - 1, 1).getDay();
  const diasMes    = new Date(calAnio, calMes, 0).getDate();
  const offset     = (primerDia === 0) ? 6 : primerDia - 1;
  const hoy        = new Date();
  hoy.setHours(0, 0, 0, 0);

  const isDarkMode = document.documentElement.classList.contains('dark-mode');
  const colors = isDarkMode ? {
    bg: '#1a2a40', accent: '#64B5F6', text: '#1a2a40', muted: '#78909C'
  } : {
    bg: '#e3f2fd', accent: '#1976D2', text: '#ffffff', muted: '#9e9e9e'
  };

  for (let i = 0; i < offset; i++) container.innerHTML += '<span></span>';

  for (let d = 1; d <= diasMes; d++) {
    const fechaStr   = `${calAnio}-${String(calMes).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const fecha      = new Date(calAnio, calMes - 1, d);
    const pasado     = fecha < hoy;
    const disponible = calFechasDisponibles.includes(fechaStr);
    const sel        = calFechaSeleccionada === fechaStr;
    const sinHorarios = calFechaSinHorarios === fechaStr;

    let estilo = 'border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center;margin:auto;font-size:.85rem;';
    let onclick = '';

    if (pasado) {
      estilo += `color:${colors.muted};cursor:not-allowed;`;
    } else if (sinHorarios) {
      estilo += `color:${colors.muted};cursor:not-allowed;`;
    } else if (disponible) {
      estilo += sel
        ? `background:${colors.accent};color:${colors.text};cursor:pointer;font-weight:600;box-shadow:0 2px 6px rgba(25,118,210,0.3);`
        : `background:${colors.bg};color:${colors.accent};cursor:pointer;font-weight:500;border:1.5px solid ${colors.accent};`;
      onclick = `onclick="seleccionarFecha('${fechaStr}', ${d})"`;
    } else {
      estilo += `color:${colors.muted};cursor:not-allowed;`;
    }

    container.innerHTML += `<div style="${estilo}" ${onclick}>${d}</div>`;
  }
}

function seleccionarFecha(fechaStr, dia) {
  calFechaSeleccionada = fechaStr;
  document.getElementById('date').value = fechaStr;
  document.getElementById('fechaSeleccionadaLabel').textContent = `Fecha seleccionada: ${dia}/${calMes}/${calAnio}`;
  dibujarDias();
  cargarHorarios();
}

async function cargarHorarios() {
  const idProfesional = parseInt(document.getElementById("profesional").value);
  const fecha         = document.getElementById("date").value;
  const select        = document.getElementById("time");
  const labelFecha    = document.getElementById("fechaSeleccionadaLabel");
  if (!idProfesional || !fecha) return;

  select.innerHTML = '<option value="">Cargando horarios...</option>';
  try {
    const res  = await fetch(`/api/citas/disponibles?idProfesional=${encodeURIComponent(idProfesional)}&fecha=${encodeURIComponent(fecha)}`, {
      credentials: "include"
    });
    const data = await res.json();

    if (!data.horarios || data.horarios.length === 0) {
      select.innerHTML = '<option value="">No hay horarios disponibles para esta fecha</option>';
      select.disabled = true;
      const fechaSinHorarios = document.getElementById('date').value;
      if (fechaSinHorarios) {
        calFechasDisponibles = calFechasDisponibles.filter(f => f !== fechaSinHorarios);
      }
      document.getElementById('date').value = '';
      calFechaSeleccionada = '';
      labelFecha.textContent = '';
      labelFecha.innerHTML = '<span class="text-danger"><i class="fas fa-exclamation-triangle me-1"></i>No hay horarios disponibles para esta fecha</span>';
      setTimeout(() => { labelFecha.textContent = ''; }, 3000);
      dibujarDias();
      return;
    }

    calFechaSinHorarios = '';
    select.disabled = false;
    select.innerHTML = '<option value="">Selecciona una hora</option>';
    // Keep only slots on the hour (minutes == 0) to represent 1‑hour blocks
    const horasUnicas = data.horarios.filter(h => {
      const m = parseInt(h.split(':')[1] || '0', 10);
      return m === 0;
    });
    horasUnicas.forEach(hora => {
      const partes = hora.split(':');
      const horaNum = parseInt(partes[0]);
      const minutos = parseInt(partes[1]) || 0;
      const periodo = horaNum >= 12 ? 'PM' : 'AM';
      const hora12 = horaNum === 0 ? 12 : horaNum > 12 ? horaNum - 12 : horaNum;
      const horaFin = horaNum + 1;
      const horaFin12 = horaFin === 0 ? 12 : horaFin > 12 ? horaFin - 12 : horaFin;
      const minStr = String(minutos).padStart(2, '0');
      const opt = document.createElement("option");
      opt.value = hora;
      opt.textContent = `${hora12}:${minStr} - ${horaFin12}:${minStr} ${periodo}`;
      select.appendChild(opt);
    });
  } catch(e) {
    select.innerHTML = '<option value="">Error al cargar horarios</option>';
  }
}

// ============================================================
// CARGAR CITAS DEL PACIENTE
// ============================================================
async function cargarCitasPaciente() {
  const tbody   = document.getElementById("tablaCitas");
  const btnHist = document.getElementById("btnVerHistorialPaciente");
  const contadorHist = document.getElementById("contadorHistorial");

      if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-center"><i class="fas fa-spinner fa-spin"></i> Cargando...</td></tr>';

  try {
    const res  = await fetch("/api/citas/paciente", { credentials: "include" });
    const data = await res.json();

    if (!data.success || !data.citas || data.citas.length === 0) {
      if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">No tienes citas agendadas</td></tr>';
      return;
    }

    const hoy = new Date(); hoy.setHours(0,0,0,0);
    const proximas = data.citas.filter(c => {
      const [d,m,a] = c.fecha.split('/');
      return new Date(a,m-1,d) >= hoy && c.estado !== 'Cancelada';
    });
    const historial = data.citas.filter(c => {
      const [d,m,a] = c.fecha.split('/');
      return new Date(a,m-1,d) < hoy || c.estado === 'Cancelada';
    });

    _citasHistorialGlobal = historial;
    
    if (btnHist) {
      btnHist.style.display = 'inline-flex';
      if (contadorHist) {
        contadorHist.textContent = historial.length;
        contadorHist.setAttribute('data-count', historial.length);
      }
    }

    if (tbody) {
      if (proximas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">No tienes citas próximas</td></tr>';
      } else {
        tbody.innerHTML = proximas.map(c => {
          let horaFormateada = c.hora ? formatearHora(c.hora) : '—';

          const creadaPorProfesional = c.creado_por_profesional === true || c.creado_por_profesional === 1 || c.creado_por_profesional === '1';
          const acciones = [];
          if (c.estado === 'Pendiente' && creadaPorProfesional) {
            acciones.push(`<button class="btn btn-success btn-sm py-0 me-1" onclick="confirmarCitaPaciente(${c.idCita})" title="Confirmar cita">Confirmar</button>`);
          }
          if (c.estado !== 'Cancelada') {
            acciones.push(`<button class="btn btn-outline-danger btn-sm py-0" onclick="abrirModalCancelar(${c.idCita})" title="Cancelar cita">Cancelar</button>`);
          } else {
            acciones.push('<span class="badge bg-secondary">Cancelada</span>');
          }
          const accionHtml = acciones.join('');

          // Badge de estado de la cita
          let estadoBadge = '';
          if (c.estado === 'Pendiente') {
            estadoBadge = creadaPorProfesional
              ? '<span class="badge bg-warning text-dark">Pendiente por tu confirmación</span>'
              : '<span class="badge bg-warning text-dark">Pendiente de confirmación del profesional</span>';
          } else if (c.estado === 'Confirmada') {
            estadoBadge = '<span class="badge bg-success">Confirmada</span>';
          } else if (c.estado === 'Cancelada') {
            estadoBadge = '<span class="badge bg-danger">Cancelada</span>';
          } else {
            estadoBadge = `<span class="badge bg-secondary">${c.estado}</span>`;
          }

          return `
            <tr class="align-middle">
              <td class="fw-semibold">${c.fecha}</td>
              <td class="text-dark fw-medium">${horaFormateada}</td>
              <td>${c.tipoCita}</td>
              <td>${c.motivo || '<em class="text-muted">Sin detalles</em>'}</td>
              <td>${estadoBadge}</td>
              <td>${accionHtml}</td>
            </tr>
          `;
        }).join('');
      }
    }
  } catch(err) {
    console.error(err);
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error al cargar citas</td></tr>';
  }
}

window.confirmarCitaPaciente = async function(idCita) {
  try {
    const response = await fetch(`/api/citas/${idCita}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ estado: 'Confirmada' })
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
      PsyAIAlerts.error('No se pudo confirmar', data.message || 'Inténtalo nuevamente.');
      return;
    }
    PsyAIAlerts.success('Cita confirmada', 'Tu profesional recibirá la confirmación.');
    cargarCitasPaciente();
  } catch (error) {
    console.error(error);
    PsyAIAlerts.error('Error', 'No fue posible conectar con el servidor.');
  }
};

async function abrirModalCancelar(idCita) {
  window.citaAcancelar = idCita;
  window.modalCancelar.show();
}

// ============================================================
// CARGAR PROFESIONALES
// ============================================================
async function cargarProfesionales() {
  try {
    const res    = await fetch("/api/profesionales", { credentials: "include" });
    const data   = await res.json();
    const select = document.getElementById("profesional");
    select.innerHTML = '<option value="">Seleccionar profesional</option>';
    (data.profesionales || []).forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.idUsuario;
      opt.textContent = p.nombre;
      select.appendChild(opt);
    });
  } catch(e) {
    console.error("Error cargando profesionales:", e);
  }
}

// ============================================================
// MODAL HISTORIAL
// ============================================================
function inicializarModalHistorial() {
  const modalEl = document.getElementById('modalHistorialCitasPaciente');
  if (!modalEl) return;

  modalEl.addEventListener('show.bs.modal', async () => {
    const histDiv = document.getElementById('listaHistorialCitasPaciente');
    if (!histDiv) return;

    histDiv.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';

    try {
      const res = await fetch('/api/citas/paciente', { credentials: 'include' });
      const data = await res.json();

      if (!data.success || !data.citas || data.citas.length === 0) {
        histDiv.innerHTML = `
          <div class="hist-empty">
            <div class="hist-empty__icon"><i class="far fa-calendar-alt"></i></div>
            <div class="hist-empty__title">Sin historial</div>
            <div class="hist-empty__desc">Aún no tienes citas registradas. Las citas completadas y canceladas aparecerán aquí.</div>
          </div>`;
        return;
      }

      const hoy = new Date(); hoy.setHours(0,0,0,0);
      const historial = data.citas.filter(c => {
        const [d,m,a] = c.fecha.split('/');
        return new Date(a,m-1,d) < hoy || c.estado === 'Cancelada';
      });

      if (historial.length === 0) {
        histDiv.innerHTML = `
          <div class="hist-empty">
            <div class="hist-empty__icon"><i class="far fa-calendar-check"></i></div>
            <div class="hist-empty__title">Todo al día</div>
            <div class="hist-empty__desc">No hay citas pasadas o canceladas en tu historial.</div>
          </div>`;
        return;
      }

      const completadas = historial.filter(c => c.estado === 'Completada').length;
      const canceladas = historial.filter(c => c.estado === 'Cancelada').length;

      histDiv.innerHTML = `
        <div class="hist-stats">
          <div class="hist-stats__item">
            <span class="hist-stats__value">${historial.length}</span>
            <span class="hist-stats__label">Total</span>
          </div>
          <div class="hist-stats__item">
            <span class="hist-stats__value hist-stats__value--success">${completadas}</span>
            <span class="hist-stats__label">Completadas</span>
          </div>
          <div class="hist-stats__item">
            <span class="hist-stats__value hist-stats__value--danger">${canceladas}</span>
            <span class="hist-stats__label">Canceladas</span>
          </div>
        </div>
        <div class="hist-list">
        ${historial.map((c, i) => `
          <div class="hist-card" style="animation-delay:${i * 0.04}s">
            <div class="hist-card__accent hist-card__accent--${c.estado === 'Completada' ? 'success' : 'danger'}"></div>
            <div class="hist-card__left">
              <div class="hist-card__icon ${c.estado === 'Completada' ? 'hist-card__icon--success' : 'hist-card__icon--danger'}">
                ${c.estado === 'Completada' ? '<i class="fas fa-check"></i>' : '<i class="fas fa-times"></i>'}
              </div>
              <div class="hist-card__body">
                <div class="hist-card__top">
                  <div class="hist-card__title">${c.tipoCita}</div>
                  <span class="hist-card__badge hist-card__badge--${c.estado === 'Completada' ? 'success' : 'danger'}">${c.estado}</span>
                </div>
                <div class="hist-card__meta">
                  <span><i class="fas fa-user-md"></i>${c.profesional || '&mdash;'}</span>
                  <span><i class="fas fa-calendar-day"></i>${c.fecha}</span>
                  <span><i class="far fa-clock"></i>${formatearHora(c.hora)}</span>
                  ${c.estadoPago ? `<span class="badge ${c.estadoPago === 'Pagado' ? 'bg-success' : 'bg-warning text-dark'} ms-1">${c.estadoPago === 'Pagado' ? 'Completado' : 'Pendiente'}</span>` : ''}
                </div>
                ${c.motivoCancelacion ? `<div class="hist-card__cancel-reason"><i class="fas fa-info-circle"></i><strong>Motivo:</strong> ${c.motivoCancelacion}</div>` : ''}
              </div>
            </div>
          </div>
        `).join('')}
        </div>`;
    } catch(e) {
      histDiv.innerHTML = '<div class="text-center text-muted py-3">Error al cargar historial</div>';
    }
  });
}

// ============================================================
// MODAL CANCELAR
// ============================================================
function inicializarModalCancelar() {
  const modalEl = document.getElementById('modalCancelar');
  if (!modalEl) return;

  window.modalCancelar = new bootstrap.Modal(modalEl);

  const textarea = document.getElementById('motivoCancelacion');
  const counter  = document.getElementById('charCountCancelacion');
  const errorMsg = document.getElementById('errorMotivoCancelacion');

  if (textarea) {
    textarea.addEventListener('input', function() {
      const currentLength = this.value.length;
      counter.textContent = `${currentLength}/500`;
      if (currentLength > 0) {
        errorMsg.classList.add('d-none');
        this.classList.remove('is-invalid');
      }
    });
  }

  modalEl.addEventListener('hidden.bs.modal', () => {
    if (textarea) {
      textarea.value = '';
      counter.textContent = '0/500';
      textarea.classList.remove('is-invalid');
      errorMsg.classList.add('d-none');
    }
  });

  document.getElementById('btnConfirmarCancelar').addEventListener('click', async () => {
    if (!window.citaAcancelar) return;

    const motivo = textarea ? textarea.value.trim() : '';
    if (!motivo) {
      if (textarea) {
        textarea.classList.add('is-invalid');
        errorMsg.classList.remove('d-none');
        textarea.focus();
      }
      return;
    }

    const btn = document.getElementById("btnConfirmarCancelar");
    const textOriginal = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Cancelando...';
    btn.disabled = true;

    try {
      const res  = await fetch(`/api/citas/${window.citaAcancelar}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ motivoCancelacion: motivo })
      });
      const data = await res.json();
      window.modalCancelar.hide();
      window.citaAcancelar = null;
      if (data.success) {
        PsyAIAlerts.success('Cita Cancelada', 'Tu cita ha sido cancelada exitosamente.');
        cargarCitasPaciente();
      } else {
        PsyAIAlerts.error('Error', data.message || 'No se pudo cancelar.');
      }
    } catch(e) {
      PsyAIAlerts.error('Error', 'Error de conexión.');
    } finally {
      btn.innerHTML = textOriginal;
      btn.disabled = false;
    }
  });
}

// ============================================================
// MODALIDAD (Virtual / Presencial)
// ============================================================
window.seleccionarModalidad = function(modalidad, el) {
  document.querySelectorAll('.modality-option').forEach(o => o.classList.remove('active'));
  if (el) el.classList.add('active');
  document.getElementById('modalidadCita').value = modalidad;
  try { localStorage.setItem('psyai_last_modality', modalidad); } catch(e) {}
};

function cargarModalidadGuardada() {
  try {
    const saved = localStorage.getItem('psyai_last_modality');
    if (saved === 'virtual' || saved === 'presencial') {
      const opt = document.querySelector(`.modality-option[data-modalidad="${saved}"]`);
      if (opt) {
        document.querySelectorAll('.modality-option').forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        document.getElementById('modalidadCita').value = saved;
      }
    }
  } catch(e) {}
}

// ============================================================
// FORMULARIO Y FLUJO DE PAGO (manual)
// ============================================================
function validarFormularioCita() {
  const tipoCita = document.getElementById("tipoCita").value.trim();
  const fecha    = document.getElementById("date").value.trim();
  const hora     = document.getElementById("time").value.trim();
  const motivo   = document.getElementById("motivo").value.trim();
  if (!tipoCita || !fecha || !hora || !motivo) {
    PsyAIAlerts.error('Error', 'Llena todos los campos antes de continuar.');
    return false;
  }
  return true;
}

document.getElementById("btnSolicitarCita").addEventListener("click", async () => {
  if (!validarFormularioCita()) return;

  const idProfesional = parseInt(document.getElementById("profesional").value);
  const tipoCita      = document.getElementById("tipoCita").value;
  const fecha         = document.getElementById("date").value;
  const hora          = document.getElementById("time").value;
  const motivo        = document.getElementById("motivo").value;
  const modalidad     = document.getElementById("modalidadCita").value;

  const btn = document.getElementById("btnSolicitarCita");
  const textOriginal = btn.innerHTML;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Agendando...';
  btn.disabled = true;

  try {
    // 1. Crear la cita
    const resCita = await fetch("/api/citas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        tipoCita, fecha, hora, motivo, idProfesional,
        creado_por_profesional: false,
        modalidad: modalidad
      })
    });
    const dataCita = await resCita.json();

    if (!dataCita.success) {
      PsyAIAlerts.error('Error', dataCita.message || 'No se pudo agendar la cita.');
      return;
    }

    const idCita = dataCita.idCita;

    PsyAIAlerts.success('Solicitud enviada', 'Tu solicitud de cita ha sido enviada. Tu profesional debe confirmarla; recibirás un aviso y tu factura aparecerá en Mis Pagos.');

    cargarCitasPaciente();

  } catch(e) {
    PsyAIAlerts.error('Error', 'Error al conectar con el servidor.');
  } finally {
    btn.innerHTML = textOriginal;
    btn.disabled = false;
  }
});

// ============================================================
// INICIALIZACIÓN
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  cargarProfesionales();
  iniciarCalendario();
  renderCalendario();
  cargarCitasPaciente();
  inicializarModalHistorial();
  inicializarModalCancelar();
  cargarModalidadGuardada();

  document.getElementById('btnMesAnterior').addEventListener('click', () => {
    calMes--; if (calMes < 1) { calMes = 12; calAnio--; }
    calFechaSeleccionada = '';
    calFechaSinHorarios = '';
    calFechasDisponibles = [];
    document.getElementById('date').value = '';
    document.getElementById('fechaSeleccionadaLabel').textContent = '';
    renderCalendario();
  });

  document.getElementById('btnMesSiguiente').addEventListener('click', () => {
    calMes++; if (calMes > 12) { calMes = 1; calAnio++; }
    calFechaSeleccionada = '';
    calFechaSinHorarios = '';
    calFechasDisponibles = [];
    document.getElementById('date').value = '';
    document.getElementById('fechaSeleccionadaLabel').textContent = '';
    renderCalendario();
  });

  window.addEventListener('themeChanged', () => dibujarDias());

  document.getElementById('profesional').addEventListener('change', () => {
    calFechaSeleccionada = '';
    calFechaSinHorarios = '';
    calFechasDisponibles = [];
    document.getElementById('date').value = '';
    document.getElementById('fechaSeleccionadaLabel').textContent = '';
    document.getElementById('time').innerHTML = '<option value="">Selecciona profesional y fecha para ver disponibilidad</option>';
    renderCalendario();
  });
});
