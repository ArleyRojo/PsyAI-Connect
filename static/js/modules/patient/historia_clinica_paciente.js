loadDocumentos();

function loadDocumentos() {
  fetch('/api/paciente/documentos')
    .then(r => r.json())
    .then(data => {
      if (!data.success) return;
      renderCompartidos(data.compartidos || []);
      renderPropios(data.propios || []);
    })
    .catch(() => showToast('Error al cargar documentos', 'warn'));
}

function renderCompartidos(docs) {
  const list = document.getElementById('shared-list');
  list.innerHTML = '';
  docs.forEach(d => {
    const row = document.createElement('div');
    row.className = 'share-row';
    row.dataset.id = d.id;
    row.innerHTML = `
      <div class="ficon shared"><i class="ti ti-file-description"></i></div>
      <div class="share-row-info">
        <strong>${d.nombre}</strong><br>
        ${d.profesional} &nbsp;·&nbsp; ${d.fecha} &nbsp;·&nbsp; ${d.tamano}
      </div>
      <div class="factions">
        <button class="faction-btn" title="Ver" onclick="viewShared(this)"><i class="ti ti-eye"></i></button>
        <button class="faction-btn" title="Descargar" onclick="downloadShared(this)"><i class="ti ti-download"></i></button>
      </div>`;
    list.appendChild(row);
  });
  document.getElementById('shared-count').textContent = docs.length + ' archivo' + (docs.length !== 1 ? 's' : '');
}

function renderPropios(docs) {
  const list = document.getElementById('prev-list');
  list.innerHTML = '';
  docs.forEach(d => {
    const row = document.createElement('div');
    row.className = 'share-row';
    row.dataset.id = d.id;
    row.innerHTML = `
      <div class="ficon prev"><i class="ti ti-file-upload"></i></div>
      <div class="share-row-info">
        <strong>${d.nombre}</strong><br>
        Subido por mí &nbsp;·&nbsp; ${d.fecha} &nbsp;·&nbsp; ${d.tamano}
      </div>
      <div class="factions">
        <button class="faction-btn" title="Ver" onclick="viewOwn(this)"><i class="ti ti-eye"></i></button>
        <button class="faction-btn" title="Descargar" onclick="downloadOwn(this)"><i class="ti ti-download"></i></button>
        <button class="faction-btn danger" title="Eliminar" onclick="openDeleteModal(this)"><i class="ti ti-trash"></i></button>
      </div>`;
    list.appendChild(row);
  });
  document.getElementById('prev-count').textContent = docs.length + ' archivo' + (docs.length !== 1 ? 's' : '');
}

const prevFileInput = document.getElementById('prev-file-input');
const prevUploadZone = document.getElementById('prev-upload-zone');
const prevFilePreview = document.getElementById('prev-file-preview');
const shareConfirm = document.getElementById('share-confirm');

prevFileInput.addEventListener('change', () => {
  if (prevFileInput.files.length) showPrevFilePreview(prevFileInput.files[0]);
});

prevUploadZone.addEventListener('dragover', e => { e.preventDefault(); prevUploadZone.classList.add('dragover'); });
prevUploadZone.addEventListener('dragleave', () => prevUploadZone.classList.remove('dragover'));
prevUploadZone.addEventListener('drop', e => {
  e.preventDefault();
  prevUploadZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) {
    prevFileInput.files = e.dataTransfer.files;
    showPrevFilePreview(e.dataTransfer.files[0]);
  }
});

function showPrevFilePreview(file) {
  document.getElementById('prev-preview-name').textContent = file.name;
  document.getElementById('prev-preview-size').textContent = (file.size / 1024 / 1024).toFixed(2) + ' MB';
  prevFilePreview.classList.add('show');
  shareConfirm.style.display = 'block';
}

function clearPrevFile() {
  prevFileInput.value = '';
  prevFilePreview.classList.remove('show');
  shareConfirm.style.display = 'none';
}

function guardarHistorialPrevio() {
  const file = prevFileInput.files[0];
  if (!file) return;
  const descripcion = document.getElementById('new-doc-descripcion')?.value || '';

  const formData = new FormData();
  formData.append('archivo', file);
  formData.append('descripcion', descripcion);

  fetch('/api/paciente/documentos/subir', {
    method: 'POST',
    body: formData,
  })
    .then(r => r.json())
    .then(data => {
      if (!data.success) { showToast(data.message || 'Error al subir', 'warn'); return; }
      showToast('Documento guardado correctamente');
      clearPrevFile();
      loadDocumentos();
    })
    .catch(() => showToast('Error de conexión', 'warn'));
}

function viewShared(btn) {
  const id = btn.closest('.share-row').dataset.id;
  window.open(`/api/descargar/documento-paciente/${id}`, '_blank');
}

function downloadShared(btn) {
  const id = btn.closest('.share-row').dataset.id;
  const a = document.createElement('a');
  a.href = `/api/descargar/documento-paciente/${id}`;
  a.download = '';
  a.click();
}

function viewOwn(btn) {
  const id = btn.closest('.share-row').dataset.id;
  window.open(`/api/descargar/documento-paciente/${id}`, '_blank');
}

function downloadOwn(btn) {
  const id = btn.closest('.share-row').dataset.id;
  const a = document.createElement('a');
  a.href = `/api/descargar/documento-paciente/${id}`;
  a.download = '';
  a.click();
}

let rowToDelete = null;

function openDeleteModal(btn) {
  rowToDelete = btn.closest('.share-row');
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
    fetch(`/api/documentos/paciente/doc/${encodeURIComponent(id)}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(data => {
        if (!data.success) { showToast(data.message || 'Error', 'warn'); return; }
        row.style.transition = 'opacity 0.2s';
        row.style.opacity = '0';
        setTimeout(() => { row.remove(); loadDocumentos(); }, 200);
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
function showToast(msg) {
  const toast = document.getElementById('toast');
  document.getElementById('toast-msg').textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}
