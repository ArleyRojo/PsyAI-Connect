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

          const cancelBtn = c.estado !== 'Cancelada'
            ? `<button class="btn btn-outline-danger btn-sm" onclick="abrirModalCancelar(${c.idCita})" title="Cancelar cita">
                 <i class="fas fa-ban me-1"></i>Cancelar
               </button>`
            : '';

          return `
            <tr class="align-middle">
              <td class="fw-semibold">${c.fecha}</td>
              <td class="text-dark fw-medium">${horaFormateada}</td>
              <td>${c.tipoCita}</td>
              <td>${c.motivo || '<em class="text-muted">Sin detalles</em>'}</td>
              <td class="text-center">${cancelBtn}</td>
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
// CUENTAS BANCARIAS (Transferencia)
// ============================================================
const CUENTAS_BANCARIAS = [
  {
    banco: 'Bancolombia',
    tipo: 'Cuenta de Ahorros',
    numero: '1234-567890-12',
    titular: 'PsyAI Connect S.A.S.',
    documento: 'NIT 901.234.567-8'
  },
  {
    banco: 'Davivienda',
    tipo: 'Cuenta Corriente',
    numero: '9876-543210-98',
    titular: 'PsyAI Connect S.A.S.',
    documento: 'NIT 901.234.567-8'
  },
  {
    banco: 'Nequi',
    tipo: 'Cuenta Digital',
    numero: '3001234567',
    titular: 'PsyAI Connect S.A.S.',
    documento: 'NIT 901.234.567-8'
  }
];

window.seleccionarSubTarjeta = function(sub) {
  document.getElementById('tipoTarjeta').value = sub;
  renderTarjetaForm(sub);
};

function renderTarjetaForm(subTipo) {
  const contenidoEl = document.getElementById("contenidoMetodoPago");

  let cuotasHtml = '';
  if (subTipo === 'credito') {
    cuotasHtml = `
      <div class="mb-3">
        <label class="form-label-pay">Número de cuotas</label>
        <select id="cuotasTarjeta" class="form-select form-control-pay">
          <option value="1">1 cuota</option>
          <option value="3">3 cuotas</option>
          <option value="6">6 cuotas</option>
          <option value="12">12 cuotas</option>
        </select>
      </div>
      <div class="mb-3 p-2 rounded" style="background:var(--card-bg);border:1px solid var(--border-color);font-size:0.85rem">
        <i class="fas fa-percent"></i> Crédito: el valor se fracciona según las cuotas seleccionadas.
      </div>`;
  } else {
    cuotasHtml = `
      <div class="mb-3">
        <div class="alert alert-info py-2 mb-0" style="font-size:0.8rem">
          <i class="fas fa-info-circle"></i> Cargo inmediato a tu cuenta débito.
        </div>
      </div>`;
  }

  contenidoEl.innerHTML = `
    <div class="mb-3">
      <div class="d-flex gap-2">
        <button type="button" class="btn btn-outline-primary btn-sm flex-fill sub-tarjeta-btn${subTipo === 'credito' ? ' active' : ''}" data-sub="credito" onclick="seleccionarSubTarjeta('credito')">Crédito</button>
        <button type="button" class="btn btn-outline-primary btn-sm flex-fill sub-tarjeta-btn${subTipo === 'debito' ? ' active' : ''}" data-sub="debito" onclick="seleccionarSubTarjeta('debito')">Débito</button>
      </div>
      <input type="hidden" id="tipoTarjeta" value="${subTipo}">
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Número de tarjeta</label>
      <input type="text" id="numTarjeta" class="form-control form-control-pay" placeholder="1234 5678 9012 3456" maxlength="19">
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Titular de la tarjeta</label>
      <input type="text" id="titularTarjeta" class="form-control form-control-pay" placeholder="Como aparece en la tarjeta">
    </div>
    <div class="row g-2 mb-3">
      <div class="col-6">
        <label class="form-label-pay">Vencimiento</label>
        <input type="text" id="vencimiento" class="form-control form-control-pay" placeholder="MM/YY" maxlength="5">
      </div>
      <div class="col-6">
        <label class="form-label-pay">CVV</label>
        <input type="text" id="cvv" class="form-control form-control-pay" placeholder="•••" maxlength="4"
          onfocus="document.getElementById('cardVisual3D').classList.add('flipped')"
          onblur="document.getElementById('cardVisual3D').classList.remove('flipped')">
      </div>
    </div>
    ${cuotasHtml}
    <div class="guardar-check">
      <input type="checkbox" id="guardarTarjeta">
      <label for="guardarTarjeta">Guardar esta tarjeta para futuros pagos</label>
    </div>`;

  // Reset card preview
  const saved = getSavedMethods().filter(m => m.tipo === 'tarjeta' && m.subTipo === subTipo);
  if (window._savedIndex !== null && saved[window._savedIndex]) {
    const s = saved[window._savedIndex];
    document.getElementById('cvNombre').textContent = s.titular;
    document.getElementById('cvNumero').textContent = `\u2022\u2022\u2022\u2022 \u2022\u2022\u2022\u2022 \u2022\u2022\u2022\u2022 ${s.ultimos}`;
    document.getElementById('cvExpiry').textContent = s.expiry;
  } else {
    document.getElementById('cvNombre').textContent = 'YOUR NAME';
    document.getElementById('cvNumero').textContent = '\u2022\u2022\u2022\u2022 \u2022\u2022\u2022\u2022 \u2022\u2022\u2022\u2022 \u2022\u2022\u2022\u2022';
    document.getElementById('cvExpiry').textContent = 'MM/YY';
    document.getElementById('cvCVV').textContent    = '\u2022\u2022\u2022';
  }

  bindCardEvents();
}

function bindCardEvents() {
  setTimeout(() => {
    document.getElementById('numTarjeta')?.addEventListener('input', e => {
      let v = e.target.value.replace(/\D/g,'').slice(0,16);
      e.target.value = v.replace(/(.{4})/g,'$1 ').trim();
      const disp = v.padEnd(16,'\u2022').replace(/(.{4})/g,'$1 ').trim();
      document.getElementById('cvNumero').textContent = disp;
    });
    document.getElementById('titularTarjeta')?.addEventListener('input', e => {
      document.getElementById('cvNombre').textContent = e.target.value.toUpperCase() || 'YOUR NAME';
    });
    document.getElementById('vencimiento')?.addEventListener('input', e => {
      let v = e.target.value.replace(/\D/g,'');
      if (v.length >= 2) v = v.slice(0,2)+'/'+v.slice(2,4);
      e.target.value = v;
      document.getElementById('cvExpiry').textContent = v || 'MM/YY';
    });
    document.getElementById('cvv')?.addEventListener('input', e => {
      document.getElementById('cvCVV').textContent = e.target.value || '\u2022\u2022\u2022';
    });
  }, 50);
}

window.copiarCuenta = function(btn, numero) {
  navigator.clipboard.writeText(numero).then(() => {
    btn.textContent = '✓ Copiado';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.innerHTML = '<i class="fas fa-copy"></i> Copiar';
      btn.classList.remove('copied');
    }, 2500);
  }).catch(() => {
    const ta = document.createElement('textarea');
    ta.value = numero;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    btn.textContent = '✓ Copiado';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.innerHTML = '<i class="fas fa-copy"></i> Copiar';
      btn.classList.remove('copied');
    }, 2500);
  });
};

window.simularPSE = function(btn) {
  const banco = document.getElementById('pseBanco')?.value;
  if (!banco) {
    PsyAIAlerts.error('Error', 'Selecciona un banco para continuar.');
    return;
  }
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Redirigiendo...';
  btn.disabled = true;
  btn.style.opacity = '0.7';
  setTimeout(() => {
    btn.innerHTML = '✓ Pago Simulado Exitosamente';
    btn.style.background = '#43a047';
    btn.disabled = true;
    document.getElementById('pseStatusPanel').style.display = 'block';
    window._pseSimulado = true;
  }, 2000);
};

window.subirComprobante = function(input) {
  const area = input.closest('.receipt-upload-area');
  const textEl = area?.querySelector('.ru-text');
  if (input.files && input.files[0]) {
    window._comprobanteTransferencia = input.files[0];
    if (textEl) textEl.textContent = '✓ ' + input.files[0].name;
    if (area) area.classList.add('has-file');
  } else {
    window._comprobanteTransferencia = null;
    if (textEl) textEl.textContent = 'Haz clic o arrastra tu comprobante aquí';
    if (area) area.classList.remove('has-file');
  }
};

// ============================================================
// FORMULARIO Y PAGO
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

document.getElementById("btnSolicitarCita").addEventListener("click", () => {
  if (!validarFormularioCita()) return;
  const facturaModal = new bootstrap.Modal(document.getElementById("facturaModal"));
  facturaModal.show();
});

// ============================================================
// PAGO — lógica completa
// ============================================================

// ── Storage de métodos guardados ──────────────────────────
const SAVED_KEY = 'psyai_saved_methods';

function getSavedMethods() {
  try { return JSON.parse(localStorage.getItem(SAVED_KEY) || '[]'); } catch { return []; }
}
function saveMethods(arr) {
  localStorage.setItem(SAVED_KEY, JSON.stringify(arr));
}
function addSavedMethod(obj) {
  const arr = getSavedMethods();
  arr.unshift(obj);
  saveMethods(arr.slice(0, 5)); // máx 5 guardados
}
function deleteSavedMethod(idx) {
  const arr = getSavedMethods();
  arr.splice(idx, 1);
  saveMethods(arr);
}

// ── Selección de método ───────────────────────────────────
window.seleccionarMetodo = function(metodo) {
  document.querySelectorAll('.pay-method-card').forEach(c => c.classList.remove('active'));
  const card = document.querySelector(`.pay-method-card[data-metodo="${metodo}"]`);
  if (card) card.classList.add('active');
  document.getElementById('metodoPagoModal').value = metodo;
  renderSavedMethods(metodo);
};

function renderSavedMethods(metodo) {
  const saved = getSavedMethods().filter(m => m.tipo === metodo);
  const wrap = document.getElementById('wrapGuardados');
  const lista = document.getElementById('listaSaved');
  if (!saved.length) { wrap.style.display = 'none'; return; }
  wrap.style.display = 'block';
  lista.innerHTML = saved.map((m, i) => `
    <div class="saved-item" onclick="usarGuardado(${i})" id="saved-${i}">
      <div class="si-icon">${m.tipo === 'pse' ? '🏦' : '💳'}</div>
      <div class="si-info">
        <div class="si-name">${m.tipo === 'pse' ? m.banco : `•••• ${m.ultimos}`}</div>
        <div class="si-sub">${m.tipo === 'pse' ? m.titular : m.titular}</div>
      </div>
      <span class="si-del" onclick="event.stopPropagation(); borrarGuardado(${i})">✕</span>
    </div>
  `).join('');
}

window.usarGuardado = function(idx) {
  document.querySelectorAll('.saved-item').forEach(el => el.classList.remove('selected'));
  const el = document.getElementById(`saved-${idx}`);
  if (el) el.classList.add('selected');
  window._savedIndex = idx;
};

window.borrarGuardado = function(idx) {
  deleteSavedMethod(idx);
  const metodo = document.getElementById('metodoPagoModal').value;
  renderSavedMethods(metodo);
};

// ── Continuar pago ────────────────────────────────────────
document.getElementById("btnContinuarPago").addEventListener("click", () => {
  const metodo = document.getElementById("metodoPagoModal").value.trim();
  if (!metodo) { PsyAIAlerts.error('Error', 'Selecciona un método de pago.'); return; }
  if (metodo === 'efectivo' && document.getElementById('modalidadCita').value === 'virtual') {
    PsyAIAlerts.error('Error', 'Pago en efectivo solo está disponible para citas presenciales.'); return;
  }

  const tituloEl    = document.getElementById("tituloMetodoPago");
  const contenidoEl = document.getElementById("contenidoMetodoPago");
  const wrapCard    = document.getElementById("wrapCardVisual");
  const wrapPSE     = document.getElementById("wrapPSEPanel");
  const wrapEfectivo = document.getElementById("wrapEfectivoPanel");
  const wrapTransferencia = document.getElementById("wrapTransferenciaPanel");

  contenidoEl.innerHTML = "";
  window._savedIndex = null;
  wrapCard.style.display = "none";
  wrapPSE.style.display = "none";
  wrapEfectivo.style.display = "none";
  wrapTransferencia.style.display = "none";

  if (metodo === "pse") {
    tituloEl.textContent = "PSE — Pago en línea";
    wrapPSE.style.display = "block";
    window._pseSimulado = false;
    contenidoEl.innerHTML = `
      <div class="mb-3">
        <label class="form-label-pay">Banco</label>
        <select id="pseBanco" class="form-control form-control-pay">
          <option value="">Selecciona tu banco</option>
          <option>Bancolombia</option><option>Davivienda</option>
          <option>Banco de Bogotá</option><option>BBVA</option>
          <option>Nequi</option><option>Daviplata</option>
          <option>Scotiabank Colpatria</option><option>Otro</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label-pay">Tipo de persona</label>
        <select id="pseTipo" class="form-control form-control-pay">
          <option value="natural">Natural</option>
          <option value="juridica">Jurídica</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label-pay">Titular de la cuenta</label>
        <input type="text" id="pseTitular" class="form-control form-control-pay" placeholder="Nombre completo">
      </div>
      <div class="pse-status-panel" id="pseStatusPanel" style="display:none">
        <div class="psp-icon"><i class="fas fa-check-circle"></i></div>
        <div class="psp-title">Redirección simulada exitosa</div>
        <div class="psp-sub">El banco ha procesado tu pago correctamente.</div>
      </div>
      <button type="button" class="btn-pago-continuar w-100" id="btnSimularPSE" onclick="simularPSE(this)">
        <i class="fas fa-external-link-alt me-2"></i>Ir al banco (simular)
      </button>
      <div class="guardar-check mt-3">
        <input type="checkbox" id="guardarPSE">
        <label for="guardarPSE">Guardar este banco para futuros pagos</label>
      </div>`;

  } else if (metodo === "efectivo") {
    tituloEl.textContent = "Pago en Efectivo";
    wrapEfectivo.style.display = "block";
    contenidoEl.innerHTML = `
      <div class="pago-summary-row">
        <span class="ps-label">Total a pagar</span>
        <span class="ps-value">$100.000 COP</span>
      </div>
      <div class="alert alert-info" style="font-size:0.82rem;border-radius:10px;margin-bottom:0">
        <i class="fas fa-info-circle me-2"></i>Puedes agendar tu cita ahora y pagar al momento de asistir.
      </div>`;

  } else if (metodo === "transferencia") {
    tituloEl.textContent = "Transferencia Bancaria";
    wrapTransferencia.style.display = "block";
    window._comprobanteTransferencia = null;
    let cuentasHtml = CUENTAS_BANCARIAS.map((c, i) => `
      <div class="bank-account-card">
        <div class="bac-header">
          <span class="bac-bank"><i class="fas fa-university me-2" style="color:#0d47a1"></i>${c.banco}</span>
          <span class="bac-type">${c.tipo}</span>
        </div>
        <div class="bac-number">${c.numero}</div>
        <div class="bac-holder">${c.titular} · ${c.documento}</div>
        <button type="button" class="bac-copy-btn" onclick="copiarCuenta(this, '${c.numero}')">
          <i class="fas fa-copy"></i> Copiar
        </button>
      </div>
    `).join('');
    contenidoEl.innerHTML = `
      <div class="bank-accounts-section">
        <div class="section-subtitle"><i class="fas fa-university"></i> Cuentas disponibles</div>
        ${cuentasHtml}
      </div>
      <div class="receipt-upload-area" onclick="document.getElementById('receiptInput').click()">
        <i class="fas fa-cloud-upload-alt"></i>
        <div class="ru-text">Haz clic o arrastra tu comprobante aquí</div>
        <div class="ru-sub">PDF, JPG o PNG · Máx 5MB</div>
        <input type="file" id="receiptInput" accept=".pdf,.jpg,.jpeg,.png" style="display:none" onchange="subirComprobante(this)">
      </div>
      <div class="pago-summary-row">
        <span class="ps-label">Total a transferir</span>
        <span class="ps-value">$100.000 COP</span>
      </div>`;

  } else if (metodo === "tarjeta") {
    const subTipo = document.getElementById('tipoTarjeta')?.value || 'credito';
    const label = subTipo === 'credito' ? "Tarjeta de Crédito" : "Tarjeta de Débito";
    tituloEl.textContent = label;
    wrapCard.style.display = "block";
    renderTarjetaForm(subTipo);
  }

  const facturaMod = bootstrap.Modal.getInstance(document.getElementById("facturaModal"));
  facturaMod.hide();
  window.modalPagoFinal.show();
});

// ── Atrás ─────────────────────────────────────────────────
document.getElementById("btnAtras").addEventListener("click", () => {
  window.modalPagoFinal.hide();
  new bootstrap.Modal(document.getElementById("facturaModal")).show();
});

// ── Finalizar pago ────────────────────────────────────────
document.getElementById("btnFinalizarPago").addEventListener("click", async () => {
  const metodo = document.getElementById("metodoPagoModal").value.trim();
  let valid = true;

  if (metodo === "pse") {
    const banco   = document.getElementById("pseBanco")?.value.trim();
    const titular = document.getElementById("pseTitular")?.value.trim();
    if (!banco || !titular) valid = false;
    if (!window._pseSimulado) { PsyAIAlerts.error('Error', 'Debes simular el pago PSE primero.'); return; }
    else if (document.getElementById('guardarPSE')?.checked) {
      addSavedMethod({ tipo: 'pse', banco, titular });
    }
  } else if (metodo === "efectivo") {
    valid = true;
  } else if (metodo === "transferencia") {
    if (!window._comprobanteTransferencia) { PsyAIAlerts.error('Error', 'Debes adjuntar el comprobante de transferencia.'); return; }
    valid = true;
  } else if (metodo === "tarjeta") {
    const num    = document.getElementById("numTarjeta")?.value.replace(/\s/g,'').trim();
    const tit    = document.getElementById("titularTarjeta")?.value.trim();
    const cvv    = document.getElementById("cvv")?.value.trim();
    const expiry = document.getElementById("vencimiento")?.value.trim();
    const subTipo = document.getElementById("tipoTarjeta")?.value || 'credito';
    if (!num || num.length < 16 || !tit || !cvv || !expiry) valid = false;
    else if (document.getElementById('guardarTarjeta')?.checked) {
      addSavedMethod({ tipo: 'tarjeta', subTipo, titular: tit, ultimos: num.slice(-4), expiry });
    }
  }

  if (!valid) { PsyAIAlerts.error('Error', 'Llena todos los campos correctamente.'); return; }

  const tipoCita      = document.getElementById("tipoCita").value;
  const fecha         = document.getElementById("date").value;
  const hora          = document.getElementById("time").value;
  const motivo        = document.getElementById("motivo").value;
  const idProfesional = document.getElementById("profesional").value;
  const modalidad     = document.getElementById("modalidadCita").value;

  try {
    const res    = await fetch("/api/citas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        tipoCita, fecha, hora, motivo, idProfesional,
        creado_por_profesional: false,
        modalidad: modalidad
      })
    });
    const result = await res.json();
    if (result.success) {
      window.modalPagoFinal.hide();
      PsyAIAlerts.success('¡Éxito!', result.message);
      cargarCitasPaciente();
    } else {
      PsyAIAlerts.error('Error', result.message);
    }
  } catch(e) {
    PsyAIAlerts.error('Error', 'Error al conectar con el servidor.');
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

  // Initialize payment modal
  window.modalPagoFinal = new bootstrap.Modal(document.getElementById("modalPagoFinal"));

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
