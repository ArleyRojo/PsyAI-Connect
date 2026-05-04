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
            setField('email',        p.email        || 'Sin correo');
            setField('licencia',     p.licencia     || 'Sin licencia');
            setField('experiencia',  p.experiencia  || 'Sin experiencia registrada');

            const headerSpan = document.querySelector('.user-info span');
            if (headerSpan) headerSpan.textContent = 'Dr(a). ' + (p.nombre || '');

            // Pre-llenar modal
            document.getElementById('editEspecialidad').value = p.especialidad || '';
            document.getElementById('editLicencia').value     = p.licencia     || '';
            document.getElementById('editExperiencia').value  = p.experiencia  || '';

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