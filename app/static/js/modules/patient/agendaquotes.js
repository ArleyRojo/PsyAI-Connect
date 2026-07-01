function formatearHora(hora) {
  if (!hora) return '—';
  const partes = hora.split(':');
  const horaNum = parseInt(partes[0]);
  const minutos = parseInt(partes[1]) || 0;
  const periodo = horaNum >= 12 ? 'PM' : 'AM';
  const hora12 = horaNum === 0 ? 12 : horaNum > 12 ? horaNum - 12 : horaNum;
  const minutosFin = minutos + 30;
  let horaFin = horaNum;
  let minFinStr = String(minutosFin).padStart(2, '0');
  if (minutosFin >= 60) {
    horaFin = horaNum + 1;
    minFinStr = '00';
  }
  const horaFin12 = horaFin === 0 ? 12 : horaFin > 12 ? horaFin - 12 : horaFin;
  return `${hora12}:${String(minutos).padStart(2, '0')} - ${horaFin12}:${minFinStr} ${periodo}`;
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
    data.horarios.forEach(hora => {
      const partes = hora.split(':');
      const horaNum = parseInt(partes[0]);
      const minutos = parseInt(partes[1]) || 0;
      const periodo = horaNum >= 12 ? 'PM' : 'AM';
      const hora12 = horaNum === 0 ? 12 : horaNum > 12 ? horaNum - 12 : horaNum;
      const minutosFin = minutos + 30;
      let horaFin = horaNum;
      let minFinStr = String(minutosFin).padStart(2, '0');
      if (minutosFin >= 60) {
        horaFin = horaNum + 1;
        minFinStr = '00';
      }
      const horaFin12 = horaFin === 0 ? 12 : horaFin > 12 ? horaFin - 12 : horaFin;
      const opt = document.createElement("option");
      opt.value = hora;
      opt.textContent = `${hora12}:${String(minutos).padStart(2, '0')} - ${horaFin12}:${minFinStr} ${periodo}`;
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

  if (tbody) tbody.innerHTML = '<tr><td colspan="5" class="text-center"><i class="fas fa-spinner fa-spin"></i> Cargando...</td></tr>';

  try {
    const res  = await fetch("/api/citas/paciente", { credentials: "include" });
    const data = await res.json();

    if (!data.success || !data.citas || data.citas.length === 0) {
      if (tbody) tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No tienes citas agendadas</td></tr>';
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
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No tienes citas próximas</td></tr>';
      } else {
        tbody.innerHTML = proximas.map(c => {
          let horaFormateada = '—';
          if (c.hora) {
            const partes = c.hora.split(':');
            const horaNum = parseInt(partes[0]);
            const minutos = parseInt(partes[1]) || 0;
            const periodo = horaNum >= 12 ? 'PM' : 'AM';
            const hora12 = horaNum === 0 ? 12 : horaNum > 12 ? horaNum - 12 : horaNum;
            const minutosFin = minutos + 30;
            let horaFin = horaNum;
            let minFinStr = String(minutosFin).padStart(2, '0');
            if (minutosFin >= 60) {
              horaFin = horaNum + 1;
              minFinStr = '00';
            }
            const horaFin12 = horaFin === 0 ? 12 : horaFin > 12 ? horaFin - 12 : horaFin;
            horaFormateada = `${hora12}:${String(minutos).padStart(2, '0')} - ${horaFin12}:${minFinStr} ${periodo}`;
          }

          const actions = [];
          if (c.estado !== 'Cancelada') {
            actions.push(`<button class="btn btn-outline-danger btn-sm" onclick="abrirModalCancelar(${c.idCita})" title="Cancelar cita">
              <i class="fas fa-ban me-1"></i>Cancelar
            </button>`);
          }

          return `
            <tr class="align-middle">
              <td class="fw-semibold">${c.fecha}</td>
              <td class="text-dark fw-medium">${horaFormateada}</td>
              <td>${c.tipoCita}</td>
              <td>${c.motivo || '<em class="text-muted">Sin detalles</em>'}</td>
              <td class="text-center">
                <div class="d-flex gap-1 justify-content-center flex-wrap">
                  ${actions.join('')}
                </div>
              </td>
            </tr>
          `;
        }).join('');
      }
    }
  } catch(err) {
    console.error(err);
    if (tbody) tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error al cargar citas</td></tr>';
  }
}

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
// CARGAR PACIENTES (para historial modal)
// ============================================================
async function cargarPacientes() {
  // Placeholder - currently not used in main flow but kept for compatibility
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
      } else {
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
                  </div>
                  ${c.motivoCancelacion ? `<div class="hist-card__cancel-reason"><i class="fas fa-info-circle"></i><strong>Motivo:</strong> ${c.motivoCancelacion}</div>` : ''}
                </div>
              </div>
            </div>
          `).join('')}
          </div>`;
      }
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
  actualizarMetodosPorModalidad();
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

function actualizarMetodosPorModalidad() {
  const modalidad = document.getElementById('modalidadCita').value;
  const efectivoCard = document.querySelector('.pay-method-card[data-metodo="efectivo"]');
  if (!efectivoCard) return;
  if (modalidad === 'virtual') {
    efectivoCard.classList.add('disabled');
    efectivoCard.style.pointerEvents = 'none';
    efectivoCard.style.opacity = '0.4';
  } else {
    efectivoCard.classList.remove('disabled');
    efectivoCard.style.pointerEvents = '';
    efectivoCard.style.opacity = '';
  }
}

// ============================================================
// FORMULARIO Y MÉTODO DE PAGO
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

window.seleccionarMetodo = function(metodo) {
  const modalidad = document.getElementById('modalidadCita').value;
  if (metodo === 'efectivo' && modalidad !== 'presencial') {
    PsyAIAlerts.info('El pago en efectivo está disponible únicamente para citas presenciales.', 'Solo presencial');
    return;
  }
  document.querySelectorAll('.pay-method-card').forEach(c => c.classList.remove('active'));
  const card = document.querySelector(`.pay-method-card[data-metodo="${metodo}"]`);
  if (card) card.classList.add('active');
  document.getElementById('metodoPagoModal').value = metodo;
  document.getElementById('btnConfirmarPago').disabled = false;
};

document.getElementById("btnSolicitarCita").addEventListener("click", () => {
  if (!validarFormularioCita()) return;
  document.getElementById('metodoPagoModal').value = '';
  document.getElementById('btnConfirmarPago').disabled = true;
  document.querySelectorAll('.pay-method-card').forEach(c => c.classList.remove('active'));
  new bootstrap.Modal(document.getElementById('facturaModal')).show();
});

document.getElementById("btnConfirmarPago").addEventListener("click", async () => {
  const metodo = document.getElementById('metodoPagoModal').value;
  if (!metodo) return;

  const tipoCita      = document.getElementById("tipoCita").value;
  const fecha         = document.getElementById("date").value;
  const hora          = document.getElementById("time").value;
  const motivo        = document.getElementById("motivo").value;
  const idProfesional = document.getElementById("profesional").value;
  const modalidad     = document.getElementById("modalidadCita").value;

  const btn = document.getElementById('btnConfirmarPago');
  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Agendando...';

  try {
    const res = await fetch("/api/citas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        tipoCita, fecha, hora, motivo, idProfesional,
        creado_por_profesional: false,
        modalidad: modalidad,
        metodoPago: metodo
      })
    });
    const result = await res.json();
    if (result.success) {
      const resumen = `${fecha} · ${hora} · ${tipoCita}`;
      document.getElementById('modalCitaResumen').textContent = resumen;
      const msgEl = document.getElementById('modalCitaFacturaMsg');
      if (result.idFactura) {
        if (result.estadoPagoFactura === 'Pagado') {
          msgEl.textContent = 'Se generó la factura y el pago quedó marcado como Pagado en modo simulado.';
        } else {
          msgEl.textContent = 'Se generó la factura pendiente. Puedes verla desde Mis Facturas.';
        }
      } else {
        msgEl.textContent = result.facturaError
          ? `La cita se creó, pero la factura no se pudo generar: ${result.facturaError}`
          : 'Recibirás un recordatorio antes de tu cita.';
      }
      bootstrap.Modal.getInstance(document.getElementById('facturaModal')).hide();
      new bootstrap.Modal(document.getElementById('modalCitaCreada')).show();
      cargarCitasPaciente();
    } else {
      PsyAIAlerts.error('Error', result.message);
    }
  } catch(e) {
    PsyAIAlerts.error('Error', 'Error al conectar con el servidor.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Confirmar y agendar';
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
  actualizarMetodosPorModalidad();

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
