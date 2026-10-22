// ============================================================
// js/my.profile2.js — Perfil Profesional
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {

    const usuario = JSON.parse(localStorage.getItem('usuario'));
    if (!usuario) {
        window.location.href = '/PsyAI%20connect/login.html';
        return;
    }

    await cargarPerfil(usuario.id);
    await cargarPagoInfo();
    inicializarUploadFoto();

    const modalEditar = document.getElementById('modalEditarPerfil');
    if (modalEditar) {
        modalEditar.addEventListener('show.bs.modal', () => {
            document.getElementById('editGeneroProf').value = document.querySelector('[data-field="genero"]')?.textContent?.trim() || 'No especificado';
        });
    }
});

function setField(campo, valor) {
    document.querySelectorAll(`[data-field="${campo}"]`).forEach(el => {
        el.textContent = valor || '';
    });
}

async function cargarPerfil(idUsuario) {
    try {
        const res  = await fetch(`/api/perfil/profesional/${idUsuario}`, {
            credentials: 'include'
        });
        const data = await res.json();

        if (data.success) {
            const p = data.perfil;
            setField('nombre',       p.nombre       || 'Sin nombre');
            setField('especialidad', p.especialidad || 'No especificada');
            setField('genero',       p.genero       || 'No especificado');
            setField('email',        p.email        || 'Sin correo');
            setField('licencia',     p.licencia     || 'Sin licencia');
            setField('experiencia',  p.experiencia  || 'Sin experiencia registrada');

            const headerSpan = document.querySelector('.user-info span');
            if (headerSpan) headerSpan.textContent = 'Dr(a). ' + (p.nombre || '');

            document.getElementById('editEspecialidad').value = p.especialidad || '';
            document.getElementById('editLicencia').value     = p.licencia     || '';
            document.getElementById('editExperiencia').value  = p.experiencia  || '';
            document.getElementById('editGeneroProf').value   = p.genero       || 'No especificado';

        } else {
            console.error('Error perfil:', data.message);
        }
    } catch (err) {
        console.error('Error cargando perfil:', err);
        // Fallback a localStorage
        document.getElementById('editEspecialidad').value = localStorage.getItem('perfil2_especialidad') || '';
        document.getElementById('editLicencia').value     = localStorage.getItem('perfil2_licencia')     || '';
        setField('especialidad', localStorage.getItem('perfil2_especialidad') || 'No especificada');
        setField('licencia',     localStorage.getItem('perfil2_licencia')     || 'Sin licencia');
        setField('experiencia',  localStorage.getItem('perfil2_experiencia')  || 'Sin experiencia registrada');
    }
}

async function guardarPerfil() {
    const usuario = JSON.parse(localStorage.getItem('usuario'))
                 || JSON.parse(localStorage.getItem('sessionUser'));

    const especialidad = document.getElementById('editEspecialidad').value.trim();
    const licencia     = document.getElementById('editLicencia').value.trim();
    const experiencia  = document.getElementById('editExperiencia').value.trim();

    // Guardar siempre en localStorage
    if (especialidad) localStorage.setItem('perfil2_especialidad', especialidad);
    if (licencia)     localStorage.setItem('perfil2_licencia',     licencia);
    if (experiencia)  localStorage.setItem('perfil2_experiencia',  experiencia);

    // Actualizar vista inmediatamente
    if (especialidad) setField('especialidad', especialidad);
    if (licencia)     setField('licencia',     licencia);
    if (experiencia)  setField('experiencia',  experiencia);

    // Intentar guardar en Flask también
    if (usuario?.id) {
        try {
            const res = await fetch('/api/perfil/profesional', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    idUsuario:    usuario.id,
                    especialidad, licencia, experiencia
                })
            });
            const data = await res.json();
            if (!data.success) console.warn('Flask:', data.message);
        } catch {
            // Sin Flask, datos ya en localStorage
        }
    }

    mostrarToast('Perfil actualizado correctamente.', 'success');
    localStorage.setItem('psyai_dashboard_update', Date.now());
    const modal = bootstrap.Modal.getInstance(document.getElementById('modalEditarPerfil'));
    if (modal) modal.hide();
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

function getNombreUsuario() {
    const storedUser = localStorage.getItem('usuario') || localStorage.getItem('sessionUser');
    if (storedUser) {
        try {
            const usuario = JSON.parse(storedUser);
            return usuario.nombre || usuario.email?.split('@')[0] || 'Usuario';
        } catch(e) {
            return 'Usuario';
        }
    }
    return 'Usuario';
}

// ── Datos de Pago y Cobro ──────────────────────────────────────
async function cargarPagoInfo() {
    try {
        const res = await fetch('/api/profesional/payment-info', { credentials: 'include' });
        const data = await res.json();
        if (data.success && data.data) {
            const info = data.data;
            const img = document.getElementById('profQrPreview');
            const empty = document.getElementById('profQrEmpty');
            const pre = document.getElementById('profMensajeTextoPreview');
            const textarea = document.getElementById('editMensajeTexto');

            if (info.qr_image) {
                if (img) { img.src = info.qr_image; img.classList.remove('d-none'); }
                if (empty) empty.classList.add('d-none');
            } else {
                if (img) img.classList.add('d-none');
                if (empty) empty.classList.remove('d-none');
            }

            if (info.mensaje_texto) {
                if (pre) pre.textContent = info.mensaje_texto;
                if (textarea) textarea.value = info.mensaje_texto;
            } else {
                if (pre) pre.textContent = 'No has registrado instrucciones de cuenta o llaves Bre-B / Nequi.';
                if (textarea) textarea.value = '';
            }
        }
    } catch(e) {
        console.error('Error cargando payment info:', e);
    }
}

async function guardarPagoInfo() {
    const btn = document.getElementById('btnGuardarPagoInfo');
    const qrInput = document.getElementById('editQrImage');
    const mensajeTexto = (document.getElementById('editMensajeTexto')?.value || '').trim();

    const fd = new FormData();
    if (qrInput && qrInput.files && qrInput.files[0]) {
        fd.append('qr_image', qrInput.files[0]);
    }
    fd.append('mensaje_texto', mensajeTexto);

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Guardando...';
    }

    try {
        const res = await fetch('/api/profesional/payment-info', {
            method: 'PUT',
            credentials: 'include',
            body: fd
        });
        const data = await res.json();
        if (data.success) {
            if (typeof PsyAIAlerts !== 'undefined' && PsyAIAlerts.success) {
                PsyAIAlerts.success('Éxito', 'Datos de cobro actualizados correctamente');
            } else if (typeof mostrarToast === 'function') {
                mostrarToast('Datos de cobro actualizados correctamente', 'success');
            }
            const modalEl = document.getElementById('modalEditarPagoInfo');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            if (qrInput) qrInput.value = '';
            await cargarPagoInfo();
        } else {
            const err = data.message || 'Error al guardar datos de cobro';
            if (typeof PsyAIAlerts !== 'undefined' && PsyAIAlerts.error) {
                PsyAIAlerts.error('Error', err);
            } else if (typeof mostrarToast === 'function') {
                mostrarToast(err, 'error');
            }
        }
    } catch(e) {
        console.error(e);
        if (typeof PsyAIAlerts !== 'undefined' && PsyAIAlerts.error) {
            PsyAIAlerts.error('Error', 'Error de conexión al guardar datos de cobro');
        } else if (typeof mostrarToast === 'function') {
            mostrarToast('Error de conexión al guardar datos de cobro', 'error');
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-save me-1"></i> Guardar Datos';
        }
    }
}