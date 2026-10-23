const urlParams = new URLSearchParams(window.location.search);
let pacienteSeleccionado = urlParams.get('pacienteId');

if (pacienteSeleccionado) {
  cargarDatosPaciente();
} else {
  document.addEventListener('DOMContentLoaded', () => {
    mostrarSelector();
    cargarSelectorPacientes();
  });
}

function cargarDatosPaciente() {
  fetch('/api/profesional/pacientes')
    .then(r => r.json())
    .then(data => {
      let pacientes = [];
      if (Array.isArray(data)) {
        pacientes = data;
      } else if (data && data.success && Array.isArray(data.pacientes)) {
        pacientes = data.pacientes;
      }
      const paciente = pacientes.find(p => p.idUsuario == pacienteSeleccionado);
      if (!paciente) { mostrarSelector(); return; }
      actualizarBanner(paciente);
      // hide selector when a patient is loaded
      const sel = document.getElementById('patient-selector');
      if (sel) sel.style.display = 'none';
    })
    .catch(() => {});

  loadDocumentos();
}

function actualizarBanner(paciente) {
  const nameEl = document.getElementById('patient-name');
  if (nameEl) nameEl.textContent = paciente.nombre || 'Paciente';
  const metaEl = document.getElementById('patient-email');
  if (metaEl) metaEl.textContent = (paciente.contacto || '') + '  ·  Paciente activo';
  const bcEl = document.getElementById('bc-patient-name');
  if (bcEl) bcEl.textContent = paciente.nombre || 'Paciente';
  const avatar = document.getElementById('patient-avatar');
  if (avatar) avatar.textContent = (paciente.nombre || 'P').charAt(0).toUpperCase();
  const switchBtn = document.getElementById('btn-switch-paciente');
  if (switchBtn) switchBtn.style.display = '';
}

function mostrarSelector() {
  const sel = document.getElementById('patient-selector');
  if (sel) sel.style.display = '';
  const switchBtn = document.getElementById('btn-switch-paciente');
  if (switchBtn) switchBtn.style.display = 'none';
  const nameEl = document.getElementById('patient-name');
  if (nameEl) nameEl.textContent = 'Ningún paciente seleccionado';
  const metaEl = document.getElementById('patient-email');
  if (metaEl) metaEl.textContent = 'Elige un paciente para ver su historia clínica y subir documentos.';
  const bcEl = document.getElementById('bc-patient-name');
  if (bcEl) bcEl.textContent = 'Sin paciente';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Helper: safe JSON fetch with ok check
async function fetchJson(url) {
  try {
    const r = await fetch(url, { credentials: 'same-origin' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const ct = r.headers.get('content-type') || '';
    if (!ct.includes('application/json')) throw new Error('Not JSON');
    return await r.json();
  } catch (e) {
    console.warn('fetchJson error', url, e);
    throw e;
  }
}

// Normalise patient list from either endpoint
function normalizarPacientes(data) {
  let arr = [];
  if (Array.isArray(data)) arr = data;
  else if (data && data.success && Array.isArray(data.pacientes)) arr = data.pacientes;
  return arr.map(p => ({
    id: p.idUsuario ?? p.idPaciente ?? p.id ?? '',
    nombre: p.nombre ?? p.nombreCompleto ?? 'Paciente',
    correo: p.contacto ?? p.email ?? ''
  })).filter(p => p.id);
}

function setSelectorState(state, msg) {
  const sel = document.getElementById('selector-paciente');
  const wrap = document.getElementById('patient-selector');
  if (!sel || !wrap) return;
  // remove previous retry button
  const old = wrap.querySelector('.retry-btn');
  if (old) old.remove();
  switch (state) {
    case 'loading':
      sel.disabled = true;
      sel.innerHTML = '<option value="">Cargando pacientes…</option>';
      break;
    case 'empty':
      sel.disabled = true;
      sel.innerHTML = '<option value="">No hay pacientes registrados</option>';
      break;
    case 'error':
      sel.disabled = true;
      sel.innerHTML = `<option value="">${escapeHtml(msg || 'No se pudieron cargar los pacientes')}</option>`;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-sm btn-outline-primary retry-btn mt-2';
      btn.textContent = 'Reintentar';
      btn.onclick = () => cargarSelectorPacientes();
      wrap.appendChild(btn);
      break;
    case 'ready':
      sel.disabled = false;
      break;
  }
}

async function cargarSelectorPacientes() {
  setSelectorState('loading');
  // 1️⃣ assigned patients
  let pacientes = await fetchJson('/api/profesional/pacientes').catch(() => []);
  pacientes = normalizarPacientes(pacientes);
  // 2️⃣ fallback to global list (accessible to professional) if none
  if (!pacientes.length) {
    const all = await fetchJson('/api/profesional/pacientes/todos').catch(() => []);
    pacientes = normalizarPacientes(all);
  }
  const select = document.getElementById('selector-paciente');
  if (!select) return;
  if (!pacientes.length) {
    setSelectorState('empty');
    return;
  }
  select.innerHTML = '<option value="">Selecciona un paciente…</option>' +
    pacientes.map(p => {
      const label = `${escapeHtml(p.nombre)}${p.correo ? ` (${escapeHtml(p.correo)})` : ''}`;
      return `<option value="${p.id}" data-email="${escapeHtml(p.correo)}">${label}</option>`;
    }).join('');
  setSelectorState('ready');

  // Preselect if URL has pacienteId
  const urlParams = new URLSearchParams(window.location.search);
  const pid = urlParams.get('pacienteId');
  if (pid) {
    const opt = select.querySelector(`option[value="${pid}"]`);
    if (opt) {
      select.value = pid;
      elegirPaciente();
    }
  }
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

async function elegirPaciente() {
  const select = document.getElementById('selector-paciente');
  if (!select || !select.value) return;
  const option = select.options[select.selectedIndex];
  pacienteSeleccionado = select.value;

  // Assign patient to professional (idempotent) before proceeding
  try {
    const assignRes = await fetch(`/api/profesional/pacientes/${pacienteSeleccionado}/asignar`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': getCookie('csrftoken')
      }
    });
    if (!assignRes.ok) {
      console.warn('Advertencia al asignar paciente al profesional:', assignRes.status);
    }
  } catch (err) {
    console.warn('Error al asignar paciente:', err);
  }

  actualizarBanner({
    nombre: option ? option.text.split(' (')[0] : 'Paciente',
    contacto: option ? option.dataset.email || '' : '',
  });
  const sel = document.getElementById('patient-selector');
  if (sel) sel.style.display = 'none';
  loadDocumentos();
  showToast('Paciente seleccionado', 'success');
}

function loadDocumentos() {
  const list = document.getElementById('my-docs-list');
  if (!list) return;
  fetch(`/api/profesional/paciente/${pacienteSeleccionado}/documentos`)
    .then(r => r.json())
    .then(data => {
      if (!data.success || !data.documentos || data.documentos.length === 0) {
        list.innerHTML = '<div class="empty-state"><i class="fas fa-folder-open"></i><p>No hay documentos del paciente.</p></div>';
        return;
      }
      list.innerHTML = '';
      data.documentos.forEach(d => addFileToList(d, false));
    })
    .catch(() => showToast('Error al cargar documentos', 'warn'));
}

const fileInput = document.getElementById('file-input');
const uploadZone = document.getElementById('upload-zone');
const filePreview = document.getElementById('file-preview');
const previewName = document.getElementById('preview-name');
const previewSize = document.getElementById('preview-size');

fileInput.addEventListener('change', () => {
  if (fileInput.files.length) showFilePreview(fileInput.files[0]);
});

uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragover'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    showFilePreview(e.dataTransfer.files[0]);
  }
});

function showFilePreview(file) {
  previewName.textContent = file.name;
  previewSize.textContent = (file.size / 1024 / 1024).toFixed(2) + ' MB';
  filePreview.classList.add('show');
}

function clearFile() {
  fileInput.value = '';
  filePreview.classList.remove('show');
}

async function guardarDocumento() {
  if (!pacienteSeleccionado) {
    showToast('Selecciona un paciente antes de subir el documento', 'warn');
    return;
  }

  const file = fileInput.files[0];
  const categoria = document.getElementById('doc-category').value;
  const visibilidad = document.getElementById('doc-visibility').value;
  const notas = document.getElementById('doc-notes').value;

  if (!file) { showToast('Selecciona un archivo primero', 'warn'); return; }
  if (!categoria) { showToast('Elige una categoría', 'warn'); return; }

  const formData = new FormData();
  formData.append('archivo', file);
  formData.append('categoria', categoria);
  formData.append('visibilidad', visibilidad);
  formData.append('notas', notas);

  try {
    const res = await fetch(`/api/profesional/paciente/${pacienteSeleccionado}/documentos`, {
      method: 'POST',
      body: formData,
    });

    let data = null;
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      data = await res.json();
    }

    if (!data || !data.success) {
      showToast(data?.message || 'Error al subir el documento', 'warn');
      return;
    }

    showToast('Documento guardado correctamente');
    clearFile();
    document.getElementById('doc-category').value = '';
    document.getElementById('doc-notes').value = '';
    document.getElementById('doc-visibility').value = 'privado';
    loadDocumentos();
  } catch (e) {
    console.error(e);
    showToast('Error de conexión', 'warn');
  }
}

function addFileToList(d, prepend) {
  const list = document.getElementById('my-docs-list');
  const ext = d.nombre.split('.').pop().toLowerCase();
  let faIcon = 'fa-file-alt';
  if (ext === 'pdf') faIcon = 'fa-file-pdf';
  else if (ext === 'docx' || ext === 'doc') faIcon = 'fa-file-word';
  else if (['jpg','jpeg','png','gif','webp'].includes(ext)) faIcon = 'fa-file-image';
  const tagClass = d.visibilidad === 'privado' ? 'privado' : 'compartido';
  const tagLabel = d.visibilidad === 'privado' ? 'Privado' : 'Compartido';
  const infoText = d.visibilidad === 'privado' ? 'Solo yo lo veo' : 'Visible para el paciente';

  const pacienteNombre = d.pacienteNombre || d.paciente || d.nombrePaciente || '';
  const pacientePart = pacienteNombre ? ` &nbsp;·&nbsp; Paciente: ${escapeHtml(pacienteNombre)}` : '';
  const row = document.createElement('div');
  row.className = 'file-row';
  row.dataset.id = d.id;
  row.dataset.visibilidad = d.visibilidad;
  row.innerHTML = `
    <div class="ficon ${ext}"><i class="fas ${faIcon}"></i></div>
    <div class="fmeta">
      <div class="fname">${d.nombre}</div>
      <div class="finfo">${d.fecha} &nbsp;·&nbsp; ${d.tamano} &nbsp;·&nbsp; ${infoText}${pacientePart}</div>
    </div>
    <span class="tag ${tagClass}">${tagLabel}</span>
    <div class="factions">
      <button class="faction-btn" title="Ver" onclick="viewDoc(this)"><i class="fas fa-eye"></i></button>
      <button class="faction-btn" title="Compartir con paciente" onclick="toggleShare(this)"><i class="fas fa-share"></i></button>
      <button class="faction-btn" title="Descargar" onclick="downloadDoc(this)"><i class="fas fa-download"></i></button>
      <button class="faction-btn danger" title="Eliminar" onclick="openDeleteModal(this)"><i class="fas fa-trash"></i></button>
    </div>`;
  if (prepend) { list.prepend(row); } else { list.appendChild(row); }
}

function viewDoc(btn) {
  const row = btn.closest('.file-row');
  const id = row.dataset.id;
  if (!id) { showToast('Documento no válido', 'warn'); return; }
  window.open(`/api/descargar/documento-profesional/${id}`, '_blank');
}

function downloadDoc(btn) {
  const row = btn.closest('.file-row');
  const id = row.dataset.id;
  if (!id) { showToast('Documento no válido', 'warn'); return; }
  const a = document.createElement('a');
  a.href = `/api/descargar/documento-profesional/${id}`;
  a.download = '';
  a.click();
}

function toggleShare(btn) {
  const row = btn.closest('.file-row');
  const id = row.dataset.id;
  if (!id) { showToast('Documento no válido', 'warn'); return; }
  const tag = row.querySelector('.tag');
  const info = row.querySelector('.finfo');

  // El servidor exige el campo "visibilidad": se envía el valor al que cambia el documento.
  const nuevaVisibilidad = row.dataset.visibilidad === 'compartido' ? 'privado' : 'compartido';
  fetch(`/api/profesional/documentos/${encodeURIComponent(id)}/visibilidad`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ visibilidad: nuevaVisibilidad })
  })
    .then(r => r.json())
    .then(data => {
      if (!data.success) { showToast(data.message || 'Error', 'warn'); return; }
      const isCompartido = data.visibilidad === 'compartido';
      tag.classList.replace(isCompartido ? 'privado' : 'compartido', isCompartido ? 'compartido' : 'privado');
      tag.textContent = isCompartido ? 'Compartido' : 'Privado';
      info.innerHTML = info.innerHTML.replace(
        isCompartido ? 'Solo yo lo veo' : 'Visible para el paciente',
        isCompartido ? 'Visible para el paciente' : 'Solo yo lo veo'
      );
      row.dataset.visibilidad = data.visibilidad;
      showToast(data.message);
    })
    .catch(() => showToast('Error de conexión', 'warn'));
}

let rowToDelete = null;

function openDeleteModal(btn) {
  const row = btn.closest('.file-row');
  if (!row.dataset.id) { showToast('Documento no válido', 'warn'); return; }
  rowToDelete = row;
  document.getElementById('delete-modal').classList.add('show');
}

function closeDeleteModal() {
  document.getElementById('delete-modal').classList.remove('show');
  rowToDelete = null;
}

function confirmDelete() {
  if (rowToDelete) {
    // Se guarda la fila en una constante: closeDeleteModal() pone rowToDelete en null
    // antes de que llegue la respuesta del servidor.
    const row = rowToDelete;
    const id = row.dataset.id;
    fetch(`/api/profesional/documentos/${encodeURIComponent(id)}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(data => {
        if (!data.success) { showToast(data.message || 'Error', 'warn'); return; }
        row.style.transition = 'opacity 0.2s';
        row.style.opacity = '0';
        setTimeout(() => row.remove(), 200);
        showToast('Documento eliminado');
      })
      .catch(() => showToast('Error de conexión', 'warn'));
  }
  closeDeleteModal();
}

document.getElementById('delete-modal').addEventListener('click', function(e) {
  if (e.target === this) closeDeleteModal();
});

let toastTimer;
function showToast(msg, type) {
  const toast = document.getElementById('toast');
  document.getElementById('toast-msg').textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}
