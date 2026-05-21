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
      if (historial.length > 0) {
        btnHist.style.display = 'inline-block';
        if (contadorHist) contadorHist.textContent = historial.length;
      } else {
        btnHist.style.display = 'inline-block';
        if (contadorHist) contadorHist.textContent = '0';
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

          const modalidadIcon = c.tipoSesion === 'Presencial'
            ? '<i class="fas fa-building me-1" title="Presencial"></i>'
            : '<i class="fas fa-video me-1" title="Virtual"></i>';

          const pagoBadge = c.estadoPago === 'Pagado'
            ? '<span class="badge bg-success ms-1"><i class="fas fa-check me-1"></i>Pagado</span>'
            : c.estadoPago === 'Pendiente' && c.metodoPago
              ? `<span class="badge bg-warning text-dark ms-1">${c.metodoPago}</span>`
              : '';

          const cancelBtn = c.estado !== 'Cancelada'
            ? `<button class="btn btn-outline-danger btn-sm" onclick="abrirModalCancelar(${c.idCita})" title="Cancelar cita">
                 <i class="fas fa-ban me-1"></i>Cancelar
               </button>`
            : '';

          return `
            <tr class="align-middle">
              <td class="fw-semibold">${c.fecha}</td>
              <td class="text-dark fw-medium">${horaFormateada}</td>
              <td>${c.tipoCita} ${modalidadIcon}</td>
              <td>${c.motivo || '<em class="text-muted">Sin detalles</em>'} ${pagoBadge}</td>
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

function abrirModalCancelar(idCita) {
  document.getElementById('modalCancelar').setAttribute('data-cita-id', idCita);
  const el = document.getElementById('modalCancelar');
  if (!el) return;
  (bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el)).show();
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
        histDiv.innerHTML = '<div class="text-center text-muted py-3">No hay citas en el historial</div>';
        return;
      }

      const hoy = new Date(); hoy.setHours(0,0,0,0);
      const historial = data.citas.filter(c => {
        const [d,m,a] = c.fecha.split('/');
        return new Date(a,m-1,d) < hoy || c.estado === 'Cancelada';
      });

      if (historial.length === 0) {
        histDiv.innerHTML = '<div class="text-center text-muted py-3">No hay citas en el historial</div>';
      } else {
        histDiv.innerHTML = historial.map(c => {
          const modalidadIcon = c.tipoSesion === 'Presencial'
            ? '<i class="fas fa-building ms-1" title="Presencial"></i>'
            : c.tipoSesion === 'Virtual'
              ? '<i class="fas fa-video ms-1" title="Virtual"></i>'
              : '';
          const pagoTag = c.estadoPago === 'Pagado'
            ? '<span class="badge bg-success ms-1" style="font-size:.7rem;">Pagado</span>'
            : c.metodoPago
              ? `<span class="badge bg-warning text-dark ms-1" style="font-size:.7rem;">${c.metodoPago}</span>`
              : '';
          return `
          <div class="list-group-item d-flex justify-content-between align-items-start">
            <div>
              <div class="fw-semibold">${c.tipoCita} ${modalidadIcon} &mdash; ${c.profesional || '&mdash;'}</div>
              <small class="text-muted">${c.fecha} &middot; ${formatearHora(c.hora)}</small>
              ${pagoTag}
              ${c.motivoCancelacion ? `<div class="mt-1"><small class="text-danger"><i class="fas fa-info-circle me-1"></i><strong>Motivo cancelación:</strong> ${c.motivoCancelacion}</small></div>` : ''}
            </div>
            <span class="badge bg-${c.estado === 'Completada' ? 'success' : c.estado === 'Cancelada' ? 'danger' : 'secondary'} ms-2 flex-shrink-0">${c.estado}</span>
          </div>`;
        }).join('');
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
  const textarea = document.getElementById('motivoCancelacion');
  const counter  = document.getElementById('charCountCancelacion');
  const errorMsg = document.getElementById('errorMotivoCancelacion');

  if (!modalEl || !textarea) return;

  if (counter) {
    textarea.addEventListener('input', function() {
      counter.textContent = `${this.value.length}/500`;
      if (this.value.trim()) {
        errorMsg?.classList.add('d-none');
        this.classList.remove('is-invalid');
      }
    });
  }

  modalEl.addEventListener('hidden.bs.modal', () => {
    textarea.value = '';
    if (counter) counter.textContent = '0/500';
    textarea.classList.remove('is-invalid');
    errorMsg?.classList.add('d-none');
    modalEl.removeAttribute('data-cita-id');
  });
}

async function confirmarCancelar(btn) {
  const modalEl  = document.getElementById('modalCancelar');
  const textarea = document.getElementById('motivoCancelacion');
  const errorMsg = document.getElementById('errorMotivoCancelacion');
  const idCita   = modalEl ? modalEl.getAttribute('data-cita-id') : null;

  if (!idCita || !textarea) return;

  const motivo = textarea.value.trim();
  if (!motivo) {
    textarea.classList.add('is-invalid');
    if (errorMsg) errorMsg.classList.remove('d-none');
    textarea.focus();
    return;
  }

  const textOriginal = btn.innerHTML;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Cancelando...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/citas/' + idCita, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ motivoCancelacion: motivo })
    });
    const data = await res.json();

    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
    modalEl.removeAttribute('data-cita-id');

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
}

// ============================================================
// CUENTAS GUARDADAS (localStorage)
// ============================================================
const SAVED_KEY = 'psyai_pay_accounts';

function getSavedAccounts() {
  try { return JSON.parse(localStorage.getItem(SAVED_KEY) || '[]'); } catch { return []; }
}
function saveAccounts(arr) {
  localStorage.setItem(SAVED_KEY, JSON.stringify(arr));
}
function addAccount(acct) {
  const arr = getSavedAccounts();
  arr.unshift(acct);
  saveAccounts(arr.slice(0, 10));
}
function removeAccount(idx) {
  const arr = getSavedAccounts();
  arr.splice(idx, 1);
  saveAccounts(arr);
}

function renderSavedAccounts(metodo) {
  const section = document.getElementById('seccionGuardados');
  const lista = document.getElementById('listaGuardados');
  const accounts = getSavedAccounts().filter(a => a.metodo === metodo);
  if (!accounts.length) { section.style.display = 'none'; return; }
  section.style.display = 'block';
  lista.innerHTML = accounts.map((a, i) => {
    function subLabel(acct) {
      if (acct.metodo === 'efectivo') return acct.doc || '';
      if (acct.metodo === 'transferencia') return acct.banco || '';
      if (acct.metodo === 'tarjeta') return '•••• ' + (acct.ultimos || '');
      return acct.banco || '';
    }
    function nameLabel(acct) {
      return acct.nombre || acct.titular || 'Sin nombre';
    }
    function iconClass(acct) {
      if (acct.metodo === 'efectivo') return 'fa-money-bill-wave';
      if (acct.metodo === 'transferencia') return 'fa-university';
      if (acct.metodo === 'tarjeta') return 'fa-credit-card';
      return 'fa-exchange-alt';
    }
    return `
    <div class="guardado-item" onclick="usarCuentaGuardada(${i})">
      <div class="gi-icon"><i class="fas ${iconClass(a)}"></i></div>
      <div class="gi-info">
        <div class="gi-nombre">${nameLabel(a)}</div>
        <div class="gi-sub">${subLabel(a)}</div>
      </div>
      <span class="gi-del" onclick="event.stopPropagation(); eliminarCuenta(${i})"><i class="fas fa-trash-alt"></i></span>
    </div>
  `;}).join('');
}

window.eliminarCuenta = function(idx) {
  removeAccount(idx);
  const metodo = document.getElementById('metodoPagoSeleccionado').value;
  renderSavedAccounts(metodo);
  if (!getSavedAccounts().filter(a => a.metodo === metodo).length) {
    document.getElementById('seccionGuardados').style.display = 'none';
  }
};

window.ocultarGuardados = function() {
  document.getElementById('seccionGuardados').style.display = 'none';
};

window.usarCuentaGuardada = function(idx) {
  const accounts = getSavedAccounts();
  const a = accounts[idx];
  if (!a) return;
  document.getElementById('seccionGuardados').style.display = 'none';
  document.getElementById('formularioPago').style.display = 'block';

  if (a.metodo === 'efectivo') {
    document.getElementById('efNombre').value = a.nombre || '';
    document.getElementById('efTipoDoc').value = a.tipoDoc || 'CC';
    document.getElementById('efNumDoc').value = a.doc || '';
    document.getElementById('efTelefono').value = a.telefono || '';
    document.getElementById('efEmail').value = a.email || '';
  } else if (a.metodo === 'transferencia') {
    document.getElementById('trNombre').value = a.titular || '';
    document.getElementById('trBanco').value = a.banco || '';
    document.getElementById('trEmail').value = a.email || '';
  } else if (a.metodo === 'tarjeta') {
    document.getElementById('tjTitular').value = a.titular || '';
    document.getElementById('tjEmail').value = a.email || '';
  } else if (a.metodo === 'pse') {
    document.getElementById('pseBanco').value = a.banco || '';
    document.getElementById('pseTipoPersona').value = a.tipoPersona || 'natural';
    document.getElementById('pseTipoDoc').value = a.tipoDoc || 'CC';
    document.getElementById('pseNumDoc').value = a.doc || '';
    document.getElementById('pseNombre').value = a.nombre || '';
    document.getElementById('pseEmail').value = a.email || '';
    document.getElementById('pseTelefono').value = a.telefono || '';
  }
};

// ============================================================
// FORMULARIO Y PAGO
// ============================================================
function validarFormularioCita() {
  const tipoCita = document.getElementById("tipoCita").value.trim();
  const modalidad = document.querySelector('input[name="modalidad"]:checked');
  const fecha    = document.getElementById("date").value.trim();
  const hora     = document.getElementById("time").value.trim();
  const motivo   = document.getElementById("motivo").value.trim();
  if (!tipoCita || !modalidad || !fecha || !hora || !motivo) {
    PsyAIAlerts.error('Error', 'Llena todos los campos antes de continuar.');
    return false;
  }
  return true;
}

// ── Formularios de pago por método ─────────────────────────
function formEfectivo() {
  return `
    <div class="pago-proc-header"><i class="fas fa-money-bill-wave"></i> Pago en Efectivo</div>
    <div class="pago-proc-body">
      <p>Realiza el pago en efectivo el día de tu cita en el consultorio.</p>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Nombre completo <span class="text-danger">*</span></label>
      <input type="text" id="efNombre" class="form-control form-control-pay" placeholder="Como aparece en tu documento" required>
    </div>
    <div class="row g-2 mb-3">
      <div class="col-5">
        <label class="form-label-pay">Tipo de documento <span class="text-danger">*</span></label>
        <select id="efTipoDoc" class="form-control form-control-pay">
          <option value="CC">Cédula de Ciudadanía</option>
          <option value="CE">Cédula de Extranjería</option>
          <option value="NIT">NIT</option>
          <option value="Pasaporte">Pasaporte</option>
        </select>
      </div>
      <div class="col-7">
        <label class="form-label-pay">Número de documento <span class="text-danger">*</span></label>
        <input type="text" id="efNumDoc" class="form-control form-control-pay" placeholder="Sin puntos ni guiones" required>
      </div>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Teléfono <span class="text-danger">*</span></label>
      <input type="tel" id="efTelefono" class="form-control form-control-pay" placeholder="300 123 4567" required>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Correo electrónico <span class="text-danger">*</span></label>
      <input type="email" id="efEmail" class="form-control form-control-pay" placeholder="tucorreo@ejemplo.com" required>
    </div>
    <div class="guardar-checkbox mb-2">
      <input type="checkbox" id="guardarEf" checked>
      <label for="guardarEf">Guardar esta cuenta para próximos pagos</label>
    </div>
    <div class="alert alert-info py-2 mb-0" style="font-size:.8rem;">
      <i class="fas fa-info-circle me-1"></i>Pagas en efectivo el día de la cita. Te enviaremos el recibo a tu correo.
    </div>`;
}

function formTransferencia() {
  return `
    <div class="pago-proc-header"><i class="fas fa-university"></i> Transferencia Bancaria</div>
    <div class="pago-proc-body">
      <p>Transfiere $100,000 COP a la siguiente cuenta:</p>
    </div>
    <div class="cuenta-bancaria mb-3">
      <div class="cb-row"><span>Banco:</span> <strong>Bancolombia</strong></div>
      <div class="cb-row"><span>Tipo:</span> <strong>Cuenta de Ahorros</strong></div>
      <div class="cb-row"><span>Número:</span> <strong>123-456789-01</strong></div>
      <div class="cb-row"><span>Titular:</span> <strong>PsyAI Connect SAS</strong></div>
      <div class="cb-row"><span>NIT:</span> <strong>901.123.456-7</strong></div>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Nombre completo del titular <span class="text-danger">*</span></label>
      <input type="text" id="trNombre" class="form-control form-control-pay" placeholder="Quién realiza la transferencia" required>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Banco de origen <span class="text-danger">*</span></label>
      <select id="trBanco" class="form-control form-control-pay">
        <option value="">Selecciona tu banco</option>
        <option>Bancolombia</option><option>Davivienda</option>
        <option>Banco de Bogotá</option><option>BBVA</option>
        <option>Nequi</option><option>Daviplata</option>
        <option>Scotiabank Colpatria</option><option>Banco Popular</option>
        <option>Banco Agrario</option><option>Otro</option>
      </select>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Número de referencia / comprobante <span class="text-danger">*</span></label>
      <input type="text" id="trReferencia" class="form-control form-control-pay" placeholder="Código de la transferencia" required>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Fecha de la transferencia <span class="text-danger">*</span></label>
      <input type="date" id="trFecha" class="form-control form-control-pay" required>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Correo electrónico <span class="text-danger">*</span></label>
      <input type="email" id="trEmail" class="form-control form-control-pay" placeholder="Para enviarte el comprobante" required>
    </div>
    <div class="guardar-checkbox mb-2">
      <input type="checkbox" id="guardarTr" checked>
      <label for="guardarTr">Guardar esta cuenta para próximos pagos</label>
    </div>
    <div class="alert alert-warning py-2 mb-0" style="font-size:.8rem;">
      <i class="fas fa-exclamation-triangle me-1"></i>La cita quedará confirmada una vez verifiquemos la transferencia (1-2 días hábiles).
    </div>`;
}

function formTarjeta() {
  return `
    <div class="pago-proc-header"><i class="fas fa-credit-card"></i> Pago con Tarjeta</div>
    <div class="pago-proc-body">
      <p>Paga de forma segura con tu tarjeta de crédito o débito.</p>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Tipo de tarjeta <span class="text-danger">*</span></label>
      <select id="tjTipo" class="form-control form-control-pay">
        <option value="credito">Crédito</option>
        <option value="debito">Débito</option>
      </select>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Número de tarjeta <span class="text-danger">*</span></label>
      <input type="text" id="tjNumero" class="form-control form-control-pay" placeholder="1234 5678 9012 3456" maxlength="19" required
        oninput="this.value = this.value.replace(/\D/g,'').slice(0,16).replace(/(.{4})/g,'$1 ').trim()">
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Titular de la tarjeta <span class="text-danger">*</span></label>
      <input type="text" id="tjTitular" class="form-control form-control-pay" placeholder="Como aparece en la tarjeta" required>
    </div>
    <div class="row g-2 mb-3">
      <div class="col-6">
        <label class="form-label-pay">Vencimiento <span class="text-danger">*</span></label>
        <input type="text" id="tjVencimiento" class="form-control form-control-pay" placeholder="MM/AA" maxlength="5" required
          oninput="var v=this.value.replace(/\D/g,'');if(v.length>=2)v=v.slice(0,2)+'/'+v.slice(2,4);this.value=v">
      </div>
      <div class="col-6">
        <label class="form-label-pay">CVV <span class="text-danger">*</span></label>
        <input type="text" id="tjCvv" class="form-control form-control-pay" placeholder="•••" maxlength="4" required
          oninput="this.value=this.value.replace(/\D/g,'').slice(0,4)">
      </div>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Correo electrónico <span class="text-danger">*</span></label>
      <input type="email" id="tjEmail" class="form-control form-control-pay" placeholder="Para enviarte el comprobante" required>
    </div>
    <div class="guardar-checkbox mb-2">
      <input type="checkbox" id="guardarTj" checked>
      <label for="guardarTj">Guardar esta tarjeta para próximos pagos</label>
    </div>
    <div class="alert alert-success py-2 mb-0" style="font-size:.8rem;">
      <i class="fas fa-lock me-1"></i>Pago seguro procesado con encriptación SSL.
    </div>`;
}

function formPSE() {
  return `
    <div class="pago-proc-header"><i class="fas fa-exchange-alt"></i> Pago PSE</div>
    <div class="pago-proc-body">
      <p>Paga en línea de forma segura a través de PSE.</p>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Banco <span class="text-danger">*</span></label>
      <select id="pseBanco" class="form-control form-control-pay">
        <option value="">Selecciona tu banco</option>
        <option>Bancolombia</option><option>Davivienda</option>
        <option>Banco de Bogotá</option><option>BBVA</option>
        <option>Nequi</option><option>Daviplata</option>
        <option>Scotiabank Colpatria</option><option>Banco Popular</option>
        <option>Banco Agrario</option><option>Otro</option>
      </select>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Tipo de persona <span class="text-danger">*</span></label>
      <select id="pseTipoPersona" class="form-control form-control-pay">
        <option value="natural">Natural</option>
        <option value="juridica">Jurídica</option>
      </select>
    </div>
    <div class="row g-2 mb-3">
      <div class="col-5">
        <label class="form-label-pay">Tipo de documento <span class="text-danger">*</span></label>
        <select id="pseTipoDoc" class="form-control form-control-pay">
          <option value="CC">Cédula de Ciudadanía</option>
          <option value="CE">Cédula de Extranjería</option>
          <option value="NIT">NIT</option>
          <option value="Pasaporte">Pasaporte</option>
        </select>
      </div>
      <div class="col-7">
        <label class="form-label-pay">Número de documento <span class="text-danger">*</span></label>
        <input type="text" id="pseNumDoc" class="form-control form-control-pay" placeholder="Sin puntos ni guiones" required>
      </div>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Nombre completo <span class="text-danger">*</span></label>
      <input type="text" id="pseNombre" class="form-control form-control-pay" placeholder="Como aparece en tu documento" required>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Correo electrónico <span class="text-danger">*</span></label>
      <input type="email" id="pseEmail" class="form-control form-control-pay" placeholder="Para enviarte el comprobante" required>
    </div>
    <div class="mb-3">
      <label class="form-label-pay">Teléfono <span class="text-danger">*</span></label>
      <input type="tel" id="pseTelefono" class="form-control form-control-pay" placeholder="300 123 4567" required>
    </div>
    <div class="guardar-checkbox mb-2">
      <input type="checkbox" id="guardarPse" checked>
      <label for="guardarPse">Guardar esta cuenta para próximos pagos</label>
    </div>
    <div class="alert alert-success py-2 mb-0" style="font-size:.8rem;">
      <i class="fas fa-lock me-1"></i>Pago seguro procesado a través de la red PSE. Serás redirigido a tu banco.
    </div>`;
}

window.seleccionarMetodoPago = function(metodo) {
  document.querySelectorAll('.metodo-pago-card').forEach(c => c.classList.remove('active'));
  const card = document.querySelector(`.metodo-pago-card[data-metodo="${metodo}"]`);
  if (card) card.classList.add('active');
  document.getElementById('metodoPagoSeleccionado').value = metodo;

  const formDiv = document.getElementById('formularioPago');
  formDiv.style.display = 'block';
  if (metodo === 'efectivo') formDiv.innerHTML = formEfectivo();
  else if (metodo === 'transferencia') formDiv.innerHTML = formTransferencia();
  else if (metodo === 'tarjeta') formDiv.innerHTML = formTarjeta();
  else if (metodo === 'pse') formDiv.innerHTML = formPSE();

  renderSavedAccounts(metodo);
  document.getElementById('btnConfirmarPago').disabled = false;
};

function actualizarMetodosPago() {
  const virtual = document.getElementById('modalidadVirtual')?.checked;
  const efCard = document.querySelector('.metodo-pago-card[data-metodo="efectivo"]');
  if (!efCard) return;
  if (virtual) {
    efCard.classList.add('disabled');
    efCard.title = 'Solo disponible en citas presenciales';
    if (efCard.classList.contains('active')) {
      efCard.classList.remove('active');
      document.getElementById('metodoPagoSeleccionado').value = '';
      document.getElementById('formularioPago').style.display = 'none';
      document.getElementById('formularioPago').innerHTML = '';
      document.getElementById('seccionGuardados').style.display = 'none';
      document.getElementById('btnConfirmarPago').disabled = true;
    }
  } else {
    efCard.classList.remove('disabled');
    efCard.title = '';
  }
}

document.querySelectorAll('input[name="modalidad"]').forEach(r => {
  r.addEventListener('change', actualizarMetodosPago);
});

document.getElementById("btnSolicitarCita").addEventListener("click", () => {
  if (!validarFormularioCita()) return;

  actualizarMetodosPago();

  document.querySelectorAll('.metodo-pago-card').forEach(c => c.classList.remove('active'));
  document.getElementById('metodoPagoSeleccionado').value = '';
  document.getElementById('formularioPago').style.display = 'none';
  document.getElementById('formularioPago').innerHTML = '';
  document.getElementById('seccionGuardados').style.display = 'none';
  document.getElementById('btnConfirmarPago').disabled = true;

  const modal = new bootstrap.Modal(document.getElementById("modalPago"));
  modal.show();
});

function validarCamposPago(metodo) {
  if (metodo === 'efectivo') {
    const nom = document.getElementById('efNombre')?.value.trim();
    const doc = document.getElementById('efNumDoc')?.value.trim();
    const tel = document.getElementById('efTelefono')?.value.trim();
    const email = document.getElementById('efEmail')?.value.trim();
    if (!nom || !doc || !tel || !email) return false;
    return true;
  }
  if (metodo === 'transferencia') {
    const nom = document.getElementById('trNombre')?.value.trim();
    const banco = document.getElementById('trBanco')?.value;
    const ref = document.getElementById('trReferencia')?.value.trim();
    const fecha = document.getElementById('trFecha')?.value;
    const email = document.getElementById('trEmail')?.value.trim();
    if (!nom || !banco || !ref || !fecha || !email) return false;
    return true;
  }
  if (metodo === 'tarjeta') {
    const num = document.getElementById('tjNumero')?.value.replace(/\s/g,'').trim();
    const tit = document.getElementById('tjTitular')?.value.trim();
    const ven = document.getElementById('tjVencimiento')?.value.trim();
    const cvv = document.getElementById('tjCvv')?.value.trim();
    const email = document.getElementById('tjEmail')?.value.trim();
    if (!num || num.length < 16 || !tit || !ven || !cvv || !email) return false;
    return true;
  }
  if (metodo === 'pse') {
    const banco = document.getElementById('pseBanco')?.value;
    const doc = document.getElementById('pseNumDoc')?.value.trim();
    const nom = document.getElementById('pseNombre')?.value.trim();
    const email = document.getElementById('pseEmail')?.value.trim();
    const tel = document.getElementById('pseTelefono')?.value.trim();
    if (!banco || !doc || !nom || !email || !tel) return false;
    return true;
  }
  return false;
}

function obtenerDatosCuenta(metodo) {
  if (metodo === 'efectivo') {
    return {
      metodo: 'efectivo',
      nombre: document.getElementById('efNombre')?.value.trim(),
      tipoDoc: document.getElementById('efTipoDoc')?.value,
      doc: document.getElementById('efNumDoc')?.value.trim(),
      telefono: document.getElementById('efTelefono')?.value.trim(),
      email: document.getElementById('efEmail')?.value.trim()
    };
  }
  if (metodo === 'transferencia') {
    return {
      metodo: 'transferencia',
      titular: document.getElementById('trNombre')?.value.trim(),
      banco: document.getElementById('trBanco')?.value,
      email: document.getElementById('trEmail')?.value.trim()
    };
  }
  if (metodo === 'tarjeta') {
    const num = document.getElementById('tjNumero')?.value.replace(/\s/g,'').trim();
    return {
      metodo: 'tarjeta',
      titular: document.getElementById('tjTitular')?.value.trim(),
      ultimos: num ? num.slice(-4) : '',
      email: document.getElementById('tjEmail')?.value.trim()
    };
  }
  if (metodo === 'pse') {
    return {
      metodo: 'pse',
      banco: document.getElementById('pseBanco')?.value,
      tipoPersona: document.getElementById('pseTipoPersona')?.value,
      tipoDoc: document.getElementById('pseTipoDoc')?.value,
      doc: document.getElementById('pseNumDoc')?.value.trim(),
      nombre: document.getElementById('pseNombre')?.value.trim(),
      email: document.getElementById('pseEmail')?.value.trim(),
      telefono: document.getElementById('pseTelefono')?.value.trim()
    };
  }
  return null;
}

function debeGuardarCuenta(metodo) {
  if (metodo === 'efectivo') return document.getElementById('guardarEf')?.checked;
  if (metodo === 'transferencia') return document.getElementById('guardarTr')?.checked;
  if (metodo === 'tarjeta') return document.getElementById('guardarTj')?.checked;
  if (metodo === 'pse') return document.getElementById('guardarPse')?.checked;
  return false;
}

function obtenerReferencia(metodo) {
  if (metodo === 'transferencia') {
    return document.getElementById('trReferencia')?.value.trim() || null;
  }
  return null;
}

document.getElementById("btnConfirmarPago").addEventListener("click", async () => {
  const metodo = document.getElementById("metodoPagoSeleccionado").value.trim();
  if (!metodo) {
    PsyAIAlerts.error('Error', 'Selecciona un método de pago.');
    return;
  }

  if (!validarCamposPago(metodo)) {
    PsyAIAlerts.error('Error', 'Completa todos los campos del formulario de pago.');
    return;
  }

  const modalidad = document.querySelector('input[name="modalidad"]:checked')?.value || 'Virtual';
  const tipoCita      = document.getElementById("tipoCita").value;
  const fecha         = document.getElementById("date").value;
  const hora          = document.getElementById("time").value;
  const motivo        = document.getElementById("motivo").value;
  const idProfesional = document.getElementById("profesional").value;
  const referencia    = obtenerReferencia(metodo);

  const btn = document.getElementById("btnConfirmarPago");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Agendando...';

  try {
    const res    = await fetch("/api/citas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        tipoCita,
        tipoSesion: modalidad,
        fecha,
        hora,
        motivo,
        idProfesional,
        metodoPago: metodo,
        referenciaPago: referencia,
        creado_por_profesional: false
      })
    });
    const result = await res.json();
    if (result.success) {
      if (debeGuardarCuenta(metodo)) {
        const data = obtenerDatosCuenta(metodo);
        if (data) addAccount(data);
      }
      const modal = bootstrap.Modal.getInstance(document.getElementById("modalPago"));
      modal.hide();
      PsyAIAlerts.success('¡Cita agendada!', 'Tu cita ha sido creada exitosamente. Revisa el estado del pago en tu historial.');
      cargarCitasPaciente();
    } else {
      PsyAIAlerts.error('Error', result.message);
    }
  } catch(e) {
    PsyAIAlerts.error('Error', 'Error al conectar con el servidor.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-check me-1"></i>Confirmar y Agendar';
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

  // No longer need modal initialization - modalPago is created on demand

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