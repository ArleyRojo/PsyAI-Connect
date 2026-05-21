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
            document.getElementById('editEdad').value     = localStorage.getItem('perfil_edad')     || '';
            document.getElementById('editTelefono').value = localStorage.getItem('perfil_telefono') || '';
            const generoGuardado = localStorage.getItem('perfil_genero') || '';
            const selectGenero   = document.getElementById('editGenero');
            if (selectGenero) selectGenero.value = generoGuardado;
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
            setField('edad',     p.edad                || 'No especificada');
            setField('genero',   p.genero              || localStorage.getItem('perfil_genero') || 'No especificado');
            setField('email',    p.email               || 'Sin correo');
            setField('telefono', p.numeroTelefonico     || 'Sin teléfono');
            setField('rol',      getRolLabel(p.rol));

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
    setField('edad',     localStorage.getItem('perfil_edad')     || 'No especificada');
    setField('genero',   localStorage.getItem('perfil_genero')   || 'No especificado');
    setField('telefono', localStorage.getItem('perfil_telefono') || 'Sin teléfono');

    const headerSpan = document.querySelector('.user-info span');
    if (headerSpan) headerSpan.textContent = nombre;
}

// ── Guardar perfil ────────────────────────────────────────────
async function guardarPerfil() {
    const usuario = JSON.parse(localStorage.getItem('usuario'))
                 || JSON.parse(localStorage.getItem('sessionUser'));

    const edadNueva     = document.getElementById('editEdad').value.trim();
    const generoNuevo   = document.getElementById('editGenero').value;
    const telefonoNuevo = document.getElementById('editTelefono').value.trim();

    // ── Valores actuales guardados ────────────────────────────
    const edadActual     = localStorage.getItem('perfil_edad')     || '';
    const generoActual   = localStorage.getItem('perfil_genero')   || '';
    const telefonoActual = localStorage.getItem('perfil_telefono') || '';

    // ── Detectar si algo cambió ───────────────────────────────
    const sinCambios =
        edadNueva     === edadActual &&
        generoNuevo   === generoActual &&
        telefonoNuevo === telefonoActual;

    if (sinCambios) {
        mostrarToast('No se detectaron cambios. La información ingresada es idéntica a la registrada actualmente.', 'warning');
        return;
    }

    // ── Guardar solo los campos que cambiaron ─────────────────
    if (edadNueva     !== edadActual)     localStorage.setItem('perfil_edad',     edadNueva);
    if (generoNuevo   !== generoActual)   localStorage.setItem('perfil_genero',   generoNuevo);
    if (telefonoNuevo !== telefonoActual) localStorage.setItem('perfil_telefono', telefonoNuevo);

    // ── Actualizar vista con los nuevos valores ───────────────
    if (edadNueva)     setField('edad',     edadNueva);
    if (generoNuevo)   setField('genero',   generoNuevo);
    if (telefonoNuevo) setField('telefono', telefonoNuevo);

    // ── Intentar sincronizar con Flask ────────────────────────
    if (usuario?.id) {
        try {
            const res = await fetch('/api/perfil/paciente', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    idUsuario:        usuario.id,
                    edad:             edadNueva,
                    genero:           generoNuevo,
                    numeroTelefonico: telefonoNuevo
                })
            });
            const data = await res.json();
            if (!data.success) console.warn('Flask:', data.message);
        } catch {
            // Sin Flask — cambios ya guardados en localStorage
        }
    }

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
