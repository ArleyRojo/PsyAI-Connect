// ============================================================
// js/my.profile.js — Perfil Paciente
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {

    // ── Cargar sesión desde localStorage ─────────────────────
    const usuario = JSON.parse(localStorage.getItem('usuario'))
                 || JSON.parse(localStorage.getItem('sessionUser'));

    // Nombre y rol en el header
    const headerSpan = document.querySelector('.user-info span[data-field="nombre"]');
    if (headerSpan && usuario) {
        const nombre = usuario.nombre || usuario.email?.split('@')[0] || 'Paciente';
        headerSpan.textContent = nombre;
    }

    // Rol visible en información personal
    const rolSpan = document.querySelector('[data-field="rol"]');
    if (rolSpan && usuario) {
        const rol = usuario.rol || usuario.role || 'paciente';
        const rolLabel = {
            paciente:      'Paciente',
            profesional:   'Profesional',
            professional:  'Profesional',
            admin:         'Administrador',
            administrador: 'Administrador'
        }[rol.toLowerCase()] || 'Paciente';
        rolSpan.textContent = rolLabel;
    }

    // ── Intentar cargar desde Flask ───────────────────────────
    if (usuario?.id) {
        await cargarPerfil(usuario.id);
    } else {
        // Sin Flask: rellenar con lo que hay en localStorage
        cargarDesdeLocal(usuario);
    }

    // ── Pre-poblar modal Editar Perfil al abrirse ─────────────
    const modalEditar = document.getElementById('modalEditarPerfil');
    if (modalEditar) {
        modalEditar.addEventListener('show.bs.modal', () => {
            document.getElementById('editGenero').value   = document.querySelector('[data-field="genero"]')?.textContent?.trim() || 'No especificado';
            document.getElementById('editTelefono').value = localStorage.getItem('perfil_telefono') || '';
        });
    }

    // ── Pre-poblar modal Preferencias al abrirse ──────────────
    const modalPrefs = document.getElementById('modalEditarPreferencias');
    if (modalPrefs) {
        modalPrefs.addEventListener('show.bs.modal', () => {
            document.getElementById('prefNotificaciones').value = localStorage.getItem('pref_notificaciones') || 'Activadas';
            document.getElementById('prefRecordatorios').value  = localStorage.getItem('pref_recordatorios')  || 'Activados';
            document.getElementById('prefContacto').value       = localStorage.getItem('pref_contacto')       || 'Correo';
        });
    }

    // ── Inicializar subida de foto ────────────────────────────
    inicializarUploadFoto();

    // ── Cargar preferencias guardadas en localStorage ─────────
    cargarPreferencias();
});

// ── Cargar desde Flask ────────────────────────────────────────
async function cargarPerfil(idUsuario) {
    try {
        const res = await fetch(`/api/perfil/paciente/${idUsuario}`, {
            credentials: 'include'
        });
        const data = await res.json();

        if (data.success) {
            const p = data.perfil;
            setField('nombre',   p.nombre              || 'Sin nombre');
            setField('genero',   p.genero              || 'No especificado');
            setField('email',    p.email               || 'Sin correo');
            setField('telefono', p.numeroTelefonico     || 'Sin teléfono');
            setField('rol',      getRolLabel(p.rol));

            if (p.genero) localStorage.setItem('perfil_genero', p.genero);

            const headerSpan = document.querySelector('.user-info span');
            if (headerSpan) headerSpan.textContent = p.nombre || 'Paciente';

        }
    } catch {
        // Flask no disponible — usar localStorage
        const usuario = JSON.parse(localStorage.getItem('usuario'))
                     || JSON.parse(localStorage.getItem('sessionUser'));
        cargarDesdeLocal(usuario);
    }
}

// ── Cargar desde localStorage (sin Flask) ────────────────────
function cargarDesdeLocal(usuario) {
    if (!usuario) return;
    const nombre = usuario.nombre || usuario.email?.split('@')[0] || 'Paciente';
    const email  = usuario.email  || 'Sin correo';
    const rol    = usuario.rol    || usuario.role || 'paciente';

    setField('nombre',   nombre);
    setField('email',    email);
    setField('rol',      getRolLabel(rol));
    setField('genero',   localStorage.getItem('perfil_genero')   || 'No especificado');
    setField('telefono', localStorage.getItem('perfil_telefono') || 'Sin teléfono');

    const headerSpan = document.querySelector('.user-info span');
    if (headerSpan) headerSpan.textContent = nombre;
}

// ── Guardar perfil ────────────────────────────────────────────
async function guardarPerfil() {
    const usuario = JSON.parse(localStorage.getItem('usuario'))
                 || JSON.parse(localStorage.getItem('sessionUser'));

    const telefonoNuevo = document.getElementById('editTelefono').value.trim();
    const telefonoActual = localStorage.getItem('perfil_telefono') || '';

    if (telefonoNuevo === telefonoActual) {
        mostrarToast('No se detectaron cambios. La información ingresada es idéntica a la registrada actualmente.', 'warning');
        return;
    }

    if (!usuario?.id) {
        mostrarToast('Tu sesión expiró. Vuelve a iniciar sesión.', 'error');
        return;
    }

    try {
        // El servidor toma el id del paciente de la sesión; el de la URL solo identifica el recurso.
        const res = await fetch(`/api/perfil/paciente/${encodeURIComponent(usuario.id)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ numeroTelefonico: telefonoNuevo })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) {
            mostrarToast(data.message || 'No se pudo guardar el teléfono. Intenta de nuevo.', 'error');
            return;
        }
    } catch {
        mostrarToast('No se pudo conectar con el servidor.', 'error');
        return;
    }

    // Solo se actualiza la vista cuando el servidor confirmó el cambio.
    localStorage.setItem('perfil_telefono', telefonoNuevo);
    if (telefonoNuevo) setField('telefono', telefonoNuevo);

    mostrarToast('Perfil actualizado correctamente.', 'success');
    const modal = bootstrap.Modal.getInstance(document.getElementById('modalEditarPerfil'));
    if (modal) modal.hide();
}

// ── Guardar preferencias ──────────────────────────────────────
function guardarPreferencias() {
    const notifNueva    = document.getElementById('prefNotificaciones').value;
    const recordatNuevo = document.getElementById('prefRecordatorios').value;
    const contactoNuevo = document.getElementById('prefContacto').value;

    // ── Valores actuales ──────────────────────────────────────
    const notifActual    = localStorage.getItem('pref_notificaciones') || 'Activadas';
    const recordatActual = localStorage.getItem('pref_recordatorios')  || 'Activados';
    const contactoActual = localStorage.getItem('pref_contacto')       || 'Correo';

    // ── Detectar si algo cambió ───────────────────────────────
    const sinCambios =
        notifNueva    === notifActual &&
        recordatNuevo === recordatActual &&
        contactoNuevo === contactoActual;

    if (sinCambios) {
        mostrarToast('No se detectaron cambios. Las preferencias ya se encuentran configuradas de esa manera.', 'warning');
        return;
    }

    // ── Guardar y actualizar vista ────────────────────────────
    localStorage.setItem('pref_notificaciones', notifNueva);
    localStorage.setItem('pref_recordatorios',  recordatNuevo);
    localStorage.setItem('pref_contacto',       contactoNuevo);

    setField('pref_notificaciones', notifNueva);
    setField('pref_recordatorios',  recordatNuevo);
    setField('pref_contacto',       contactoNuevo);

    mostrarToast('Preferencias actualizadas correctamente.', 'success');
    const modal = bootstrap.Modal.getInstance(document.getElementById('modalEditarPreferencias'));
    if (modal) modal.hide();
}

function cargarPreferencias() {
    const notif    = localStorage.getItem('pref_notificaciones') || 'Activadas';
    const recordat = localStorage.getItem('pref_recordatorios')  || 'Activados';
    const contacto = localStorage.getItem('pref_contacto')       || 'Correo';

    setField('pref_notificaciones', notif);
    setField('pref_recordatorios',  recordat);
    setField('pref_contacto',       contacto);
}

// ── Foto de perfil ────────────────────────────────────────────
function inicializarUploadFoto() {
    const input = document.getElementById('inputFoto');
    const btn = document.getElementById('btnCambiarFoto');
    const img = document.getElementById('fotoPerfilPreview');
    const avatarDiv = document.getElementById('avatarInicialPreview');
    const btnGuardar = document.getElementById('btnGuardarFoto');
    const btnCancelar = document.getElementById('btnCancelarFoto');
    const actions = document.getElementById('avatarActions');
    const statusText = document.getElementById('avatarStatusText');

    if (!input || !btn) return;

    let pendingFile = null;

    cargarFotoDesdeSession(img, avatarDiv);

    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        input.click();
    });

    input.addEventListener('change', function() {
        const file = this.files[0];
        if (!file) return;

        if (file.size > 5 * 1024 * 1024) {
            mostrarToast('La imagen no puede superar los 5 MB', 'warning');
            this.value = '';
            return;
        }

        pendingFile = file;
        const reader = new FileReader();
        reader.onload = function(e) {
            img.src = e.target.result;
            img.style.display = 'block';
            avatarDiv.style.display = 'none';
            statusText.textContent = 'Previsualizando foto nueva';
            actions.style.display = 'flex';
        };
        reader.readAsDataURL(file);
    });

    btnGuardar.addEventListener('click', async function() {
        if (!pendingFile) return;
        statusText.textContent = 'Subiendo foto...';
        actions.style.display = 'none';

        try {
            const formData = new FormData();
            formData.append('foto', pendingFile);
            const res = await fetch('/api/perfil/foto', {
                method: 'POST',
                credentials: 'include',
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                mostrarToast('Foto de perfil actualizada correctamente', 'success');
                statusText.textContent = 'Haz clic en el icono de la c\u00e1mara para cambiar tu foto de perfil';
                const usuario = JSON.parse(localStorage.getItem('usuario') || '{}');
                usuario.fotoPerfil = data.fotoPerfil;
                localStorage.setItem('usuario', JSON.stringify(usuario));
                actualizarAvataresEnPagina(data.fotoPerfil);
                pendingFile = null;
            } else {
                mostrarToast(data.message || 'Error al subir la foto', 'error');
                recargarFotoActual(img, avatarDiv);
                statusText.textContent = 'Haz clic en el icono de la c\u00e1mara para cambiar tu foto de perfil';
                pendingFile = null;
            }
        } catch(e) {
            mostrarToast('Error de conexi\u00f3n al subir la foto', 'error');
            recargarFotoActual(img, avatarDiv);
            statusText.textContent = 'Haz clic en el icono de la c\u00e1mara para cambiar tu foto de perfil';
            pendingFile = null;
        }
        input.value = '';
    });

    btnCancelar.addEventListener('click', function() {
        pendingFile = null;
        recargarFotoActual(img, avatarDiv);
        statusText.textContent = 'Haz clic en el icono de la c\u00e1mara para cambiar tu foto de perfil';
        actions.style.display = 'none';
        input.value = '';
    });
}

async function cargarFotoDesdeSession(img, avatarDiv) {
    try {
        const res = await fetch('/api/session', { credentials: 'include' });
        const data = await res.json();
        if (data.fotoPerfil) {
            const testImg = new Image();
            testImg.onload = function() {
                img.src = '/uploads/' + data.fotoPerfil;
                img.style.display = 'block';
                if (avatarDiv) avatarDiv.style.display = 'none';
            };
            testImg.onerror = function() {
                img.style.display = 'none';
                if (avatarDiv) avatarDiv.style.display = 'block';
            };
            testImg.src = '/uploads/' + data.fotoPerfil;
            const usuario = JSON.parse(localStorage.getItem('usuario') || '{}');
            usuario.fotoPerfil = data.fotoPerfil;
            localStorage.setItem('usuario', JSON.stringify(usuario));
        }
    } catch(e) {
        console.error('Error cargando foto:', e);
    }
}

function recargarFotoActual(img, avatarDiv) {
    const usuario = JSON.parse(localStorage.getItem('usuario') || '{}');
    if (usuario.fotoPerfil) {
        img.src = '/uploads/' + usuario.fotoPerfil;
        img.style.display = 'block';
        if (avatarDiv) avatarDiv.style.display = 'none';
    } else {
        img.style.display = 'none';
        if (avatarDiv) avatarDiv.style.display = 'block';
    }
}

function actualizarAvataresEnPagina(fotoPerfil) {
    document.querySelectorAll('[data-avatar="inicial"]').forEach(el => {
        const nombre = el.dataset.nombre || getNombreUsuario();
        const parent = el.parentNode;
        if (!parent) return;
        if (fotoPerfil) {
            const preview = parent.querySelector('#fotoPerfilPreview');
            if (preview) {
                preview.src = '/uploads/' + fotoPerfil;
                preview.style.display = 'block';
                preview.style.borderRadius = '50%';
                preview.style.objectFit = 'cover';
                el.style.display = 'none';
                return;
            }
            const img = document.createElement('img');
            img.src = '/uploads/' + fotoPerfil;
            img.alt = 'Foto de perfil';
            const w = el.style.width || el.offsetWidth || 40;
            const h = el.style.height || el.offsetHeight || 40;
            img.style.width = (typeof w === 'string' && w.includes('px') ? w : w + 'px');
            img.style.height = (typeof h === 'string' && h.includes('px') ? h : h + 'px');
            img.style.borderRadius = '50%';
            img.style.objectFit = 'cover';
            img.style.display = 'block';
            img.onerror = function() {
                this.style.display = 'none';
                if (el.parentNode) {
                    generarAvatarFallback(nombre, el);
                }
            };
            parent.replaceChild(img, el);
        }
    });
}

function generarAvatarFallback(nombre, elemento) {
    const inicial = nombre ? nombre.charAt(0).toUpperCase() : '?';
    const colores = {
        'A':'#1D9E75','B':'#378ADD','C':'#D85A30','D':'#534AB7','E':'#BA7517',
        'F':'#639922','G':'#D4537E','H':'#1D9E75','I':'#378ADD','J':'#D85A30',
        'K':'#534AB7','L':'#BA7517','M':'#639922','N':'#D4537E','O':'#1D9E75',
        'P':'#378ADD','Q':'#D85A30','R':'#534AB7','S':'#BA7517','T':'#639922',
        'U':'#D4537E','V':'#1D9E75','W':'#378ADD','X':'#D85A30','Y':'#534AB7',
        'Z':'#BA7517'
    };
    const colorFondo = colores[inicial.toUpperCase()] || '#6c757d';
    const w = elemento.style.width || elemento.offsetWidth || 40;
    const h = elemento.style.height || elemento.offsetHeight || 40;
    const div = document.createElement('div');
    div.style.width = (typeof w === 'string' && w.includes('px') ? w : w + 'px');
    div.style.height = (typeof h === 'string' && h.includes('px') ? h : h + 'px');
    div.style.borderRadius = '50%';
    div.style.backgroundColor = colorFondo;
    div.style.color = 'white';
    div.style.fontWeight = '500';
    div.style.display = 'flex';
    div.style.alignItems = 'center';
    div.style.justifyContent = 'center';
    div.style.fontSize = Math.floor(parseInt(w) * 0.4) + 'px';
    div.textContent = inicial;
    if (elemento.parentNode) elemento.parentNode.replaceChild(div, elemento);
}

// ── Helpers ───────────────────────────────────────────────────
function setField(field, value) {
    document.querySelectorAll(`[data-field="${field}"]`)
        .forEach(el => el.textContent = value);
}

function getRolLabel(rol) {
    if (!rol) return 'Paciente';
    return {
        paciente:      'Paciente',
        profesional:   'Profesional',
        professional:  'Profesional',
        admin:         'Administrador',
        administrador: 'Administrador'
    }[rol.toLowerCase()] || 'Paciente';
}

/* ---------- Notificaciones ---------- */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('notif-prefs-form');
    if (!form) return;

    const canalRadios = form.querySelectorAll('input[name="canalNotificacion"]');
    const telWrap = document.getElementById('tel-wrap');
    const consentWrap = document.getElementById('consent-wrap');
    const telInput = document.getElementById('numeroTelefonico');
    const consentChk = document.getElementById('whatsappConsentimiento');
    const btnGuardar = document.getElementById('btnGuardarNotif');
    const btnProbar = document.getElementById('btnProbarNotif');

    function updateVisibility() {
        const checked = form.querySelector('input[name="canalNotificacion"]:checked');
        const val = checked ? checked.value : 'email';
        const showTel = val === 'whatsapp' || val === 'ambos';
        telWrap.style.display = showTel ? 'block' : 'none';
        consentWrap.style.display = showTel ? 'block' : 'none';
        telInput.required = showTel;
        consentChk.required = showTel;
    }
    canalRadios.forEach(r => r.addEventListener('change', updateVisibility));
    updateVisibility();

    /* ---- Guardar ---- */
    form.addEventListener('submit', async e => {
        e.preventDefault();
        btnGuardar.disabled = true;
        btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando…';

        const checkedCanal = form.querySelector('input[name="canalNotificacion"]:checked');
        const payload = {
            canalNotificacion: checkedCanal ? checkedCanal.value : 'email',
            numeroTelefonico: telInput.value.trim(),
            whatsappConsentimiento: consentChk.checked,
            recibirRecordatorioCita: form.recibirRecordatorioCita.checked,
            recibirConfirmacion: form.recibirConfirmacion.checked,
            recibirMensajePro: form.recibirMensajePro.checked,
        };

        try {
            const usuario = JSON.parse(localStorage.getItem('usuario'))
                         || JSON.parse(localStorage.getItem('sessionUser'));
            const resp = await fetch(`/api/perfil/paciente/${usuario.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(payload),
                credentials: 'same-origin',
            });
            const data = await resp.json();
            if (data.success) {
                showAlert('success', data.message || 'Preferencias guardadas');
            } else {
                showAlert('danger', data.message || 'Error al guardar');
                if (data.errors) {
                    Object.entries(data.errors).forEach(([k, msgs]) => {
                        const el = form.querySelector(`[name="${k}"]`);
                        if (el) el.classList.add('is-invalid');
                    });
                }
            }
        } catch (err) {
            console.error(err);
            showAlert('danger', 'Error de conexión');
        } finally {
            btnGuardar.disabled = false;
            btnGuardar.innerHTML = '<i class="fas fa-save me-1"></i> Guardar preferencias';
        }
    });

    /* ---- Probar canal ---- */
    btnProbar.addEventListener('click', async () => {
        const checkedCanal = form.querySelector('input[name="canalNotificacion"]:checked');
        const canal = checkedCanal ? checkedCanal.value : 'email';
        if (canal === 'ninguno') return showAlert('warning','Canal “Ninguno” no envía pruebas');
        btnProbar.disabled = true;
        btnProbar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando…';
        try {
            const body = { canal };
            // For WhatsApp test, also send the phone number so backend can send real message
            if (canal === 'whatsapp') {
                const telInput = document.getElementById('numeroTelefonico');
                const numero = telInput ? telInput.value.trim() : '';
                if (!numero) return showAlert('warning','Ingresa un número de teléfono');
                body.numero = numero;
            }
            const resp = await fetch('/api/notificaciones/probar/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(body),
                credentials: 'same-origin',
            });
            const data = await resp.json();
            showAlert(data.success ? 'success' : 'danger', data.message);
        } catch (_) { showAlert('danger','Error de conexión'); }
        finally {
            btnProbar.disabled = false;
            btnProbar.innerHTML = '<i class="fas fa-paper-plane me-1"></i> Enviar prueba';
        }
    });
});

/* tiny helpers (already present in project) */
function getCookie(name){
    let v=null; if(document.cookie){ document.cookie.split(';').forEach(c=>{c=c.trim(); if(c.startsWith(name+'=')) v=decodeURIComponent(c.slice(name.length+1));}); } return v;
}

/* ──────────────────────────────────────────────────────────────
   Mis datos y privacidad (Derechos ARCO - Ley 1581/2012)
   ────────────────────────────────────────────────────────────── */

async function cargarMisDatos() {
    try {
        const res = await fetch('/api/paciente/mis-datos', { credentials: 'include' });
        const data = await res.json();
        if (data.success) {
            // Descargar JSON
            const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `mis-datos-${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            mostrarToast('Datos descargados correctamente', 'success');
        } else {
            mostrarToast(data.message || 'Error al descargar datos', 'danger');
        }
    } catch (e) {
        console.error(e);
        mostrarToast('Error de conexión al descargar datos', 'danger');
    }
}

async function cargarConsentimientos() {
    try {
        const res = await fetch('/api/paciente/consentimientos', { credentials: 'include' });
        const data = await res.json();
        if (data.success) {
            renderConsentimientos(data.consentimientos);
        } else {
            document.getElementById('listaConsentimientos').innerHTML = '<p class="text-muted text-center">Error al cargar consentimientos</p>';
        }
    } catch (e) {
        console.error(e);
        document.getElementById('listaConsentimientos').innerHTML = '<p class="text-danger text-center">Error de conexión</p>';
    }
}

function renderConsentimientos(consentimientos) {
    const container = document.getElementById('listaConsentimientos');
    if (!consentimientos || consentimientos.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">No hay consentimientos registrados</p>';
        return;
    }
    container.innerHTML = consentimientos.map(c => `
        <div class="card mb-3">
            <div class="card-body d-flex align-items-center justify-content-between flex-wrap gap-2">
                <div>
                    <strong>${c.tipo === 'terminos_privacidad' ? 'Términos y Privacidad' : c.tipo === 'datos_sensibles_ia' ? 'Datos Sensibles e IA' : c.tipo === 'whatsapp' ? 'WhatsApp' : c.tipo}</strong>
                    <div class="text-muted small">v${c.version} · ${c.aceptado ? '<span class="text-success">Activo</span>' : '<span class="text-danger">Revocado</span>'} · ${c.fecha ? new Date(c.fecha).toLocaleDateString('es-CO') : ''}</div>
                </div>
                <div class="d-flex gap-2">
                    ${c.aceptado && (c.tipo === 'datos_sensibles_ia' || c.tipo === 'whatsapp') ? `
                        <button type="button" class="btn btn-sm btn-outline-danger" onclick="revocarConsentimiento('${c.tipo}')">
                            <i class="fas fa-user-slash me-1"></i> Revocar
                        </button>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

async function revocarConsentimiento(tipo) {
    if (!confirm(`¿Estás seguro de revocar el consentimiento de ${tipo === 'datos_sensibles_ia' ? 'Datos Sensibles e IA' : 'WhatsApp'}?`)) return;
    try {
        const res = await fetch('/api/paciente/consentimientos/revocar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            credentials: 'include',
            body: JSON.stringify({ tipo, confirmar: true })
        });
        const data = await res.json();
        if (data.success) {
            mostrarToast(data.message, 'success');
            cargarConsentimientos();
            // Si se revoca datos_sensibles_ia, actualizar estado del chatbot
            if (tipo === 'datos_sensibles_ia') {
                const chatSection = document.getElementById('chatbot-section');
                if (chatSection) chatSection.classList.add('chatbot-consent-blocked');
            }
        } else {
            mostrarToast(data.message, 'danger');
        }
    } catch (e) {
        console.error(e);
        mostrarToast('Error de conexión', 'danger');
    }
}

async function cargarSolicitudesDerechos() {
    try {
        const res = await fetch('/api/paciente/solicitudes-derechos', { credentials: 'include' });
        const data = await res.json();
        if (data.success) {
            renderSolicitudesDerechos(data.solicitudes);
        } else {
            document.getElementById('tbodySolicitudesDerechos').innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error al cargar</td></tr>';
        }
    } catch (e) {
        console.error(e);
        document.getElementById('tbodySolicitudesDerechos').innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error de conexión</td></tr>';
    }
}

function renderSolicitudesDerechos(solicitudes) {
    const tbody = document.getElementById('tbodySolicitudesDerechos');
    if (!solicitudes || solicitudes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No hay solicitudes registradas</td></tr>';
        return;
    }
    const labels = {
        acceso: 'Acceso / Consulta',
        rectificacion: 'Rectificación',
        supresion: 'Supresión',
        revocatoria: 'Revocatoria',
        reclamo: 'Reclamo'
    };
    const estadoLabels = {
        recibida: 'badge bg-secondary',
        en_proceso: 'badge bg-info',
        respondida: 'badge bg-success',
        prorrogada: 'badge bg-warning',
        cerrada: 'badge bg-secondary'
    };
    tbody.innerHTML = solicitudes.map(s => `
        <tr>
            <td>${s.fecha ? new Date(s.fecha).toLocaleDateString('es-CO', {day:'2-digit',month:'short',year:'numeric'}) : '—'}</td>
            <td>${labels[s.tipo] || s.tipo}</td>
            <td><span class="${estadoLabels[s.estado] || 'bg-secondary'}">${s.estado}</span></td>
            <td>${s.fechaLimite ? new Date(s.fechaLimite).toLocaleDateString('es-CO') : '—'}</td>
            <td>${s.fechaRespuesta ? new Date(s.fechaRespuesta).toLocaleDateString('es-CO') : '—'}</td>
        </tr>
    `).join('');
}

async function eliminarCuenta() {
    const password = document.getElementById('eliminarCuentaPassword').value;
    const confirmado = document.getElementById('confirmarEliminacion').checked;
    if (!password || !confirmado) {
        mostrarToast('Completa la contraseña y marca la confirmación', 'warning');
        return;
    }
    const btn = document.getElementById('btnConfirmarEliminarCuenta');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Eliminando…';
    try {
        const res = await fetch('/api/cuenta/eliminar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            credentials: 'include',
            body: JSON.stringify({ password, confirmar: true })
        });
        const data = await res.json();
        if (data.success) {
            mostrarToast(data.message, 'success');
            // Redirigir al login después de un breve delay
            setTimeout(() => { window.location.href = '/login.html'; }, 2000);
        } else {
            mostrarToast(data.message, 'danger');
        }
    } catch (e) {
        console.error(e);
        mostrarToast('Error de conexión', 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-trash-alt me-1"></i> Eliminar mi cuenta';
    }
}

function initMisDatosPrivacidad() {
    // Descargar datos
    const btnDescargar = document.getElementById('btnDescargarDatos');
    if (btnDescargar) btnDescargar.addEventListener('click', cargarMisDatos);

    // Gestionar consentimientos
    const btnGestionar = document.getElementById('btnGestionarConsentimientos');
    if (btnGestionar) {
        btnGestionar.addEventListener('click', () => {
            cargarConsentimientos();
            const modal = new bootstrap.Modal(document.getElementById('modalConsentimientos'));
            modal.show();
        });
    }

    // Eliminar cuenta
    const btnEliminar = document.getElementById('btnEliminarCuenta');
    if (btnEliminar) {
        btnEliminar.addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('modalEliminarCuenta'));
            modal.show();
        });
    }
    const btnConfirmar = document.getElementById('btnConfirmarEliminarCuenta');
    if (btnConfirmar) btnConfirmar.addEventListener('click', eliminarCuenta);

    // Actualizar solicitudes
    const btnActualizar = document.getElementById('btnActualizarSolicitudes');
    if (btnActualizar) {
        btnActualizar.addEventListener('click', cargarSolicitudesDerechos);
    }

    // Cargar solicitudes al cargar la página
    cargarSolicitudesDerechos();
}

// Inicializar al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    initMisDatosPrivacidad();
});
