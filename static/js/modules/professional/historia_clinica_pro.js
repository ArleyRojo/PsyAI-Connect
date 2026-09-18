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
      if (!data.success) return;
      const paciente = data.pacientes.find(p => p.idUsuario == pacienteSeleccionado);
      if (!paciente) { mostrarSelector(); return; }
      actualizarBanner(paciente);
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

function cargarSelectorPacientes() {
  const select = document.getElementById('selector-paciente');
  if (!select) return;
  fetch('/api/profesional/pacientes')
    .then(r => r.json())
    .then(data => {
      const pacientes = (data.success && data.pacientes) ? data.pacientes : [];
      select.innerHTML = '<option value="">Selecciona un paciente...</option>' +
        pacientes.map(p => {
          const nombre = escapeHtml(p.nombre || 'Paciente');
          const email = escapeHtml(p.contacto || p.email || '');
          return '<option value="' + p.idUsuario + '" data-email="' + email + '">' + nombre + '</option>';
        }).join('');
    })
    .catch(() => { select.innerHTML = '<option value="">No se pudieron cargar los pacientes</option>'; });
}

function elegirPaciente() {
  const select = document.getElementById('selector-paciente');
  if (!select || !select.value) return;
  const option = select.options[select.selectedIndex];
  pacienteSeleccionado = select.value;
  actualizarBanner({
    nombre: option ? option.text : 'Paciente',
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

  const row = document.createElement('div');
  row.className = 'file-row';
  row.dataset.id = d.id;
  row.dataset.visibilidad = d.visibilidad;
  row.innerHTML = `
    <div class="ficon ${ext}"><i class="fas ${faIcon}"></i></div>
    <div class="fmeta">
      <div class="fname">${d.nombre}</div>
      <div class="finfo">${d.fecha} &nbsp;·&nbsp; ${d.tamano} &nbsp;·&nbsp; ${infoText}</div>
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

  fetch(`/api/profesional/documentos/${id}/visibilidad`, { method: 'PUT' })
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
    const id = rowToDelete.dataset.id;
    fetch(`/api/profesional/documentos/${id}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(data => {
        if (!data.success) { showToast(data.message || 'Error', 'warn'); return; }
        rowToDelete.style.transition = 'opacity 0.2s';
        rowToDelete.style.opacity = '0';
        setTimeout(() => rowToDelete.remove(), 200);
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
