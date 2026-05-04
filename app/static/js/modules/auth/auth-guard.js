const API = '';

function limpiarSesionLocal() {
    try {
        localStorage.removeItem('usuario');
        localStorage.removeItem('sessionUser');
    } catch {
        // Ignorar errores de almacenamiento local.
    }
}

async function obtenerUsuarioActual() {
    try {
        const res = await fetch(`${API}/api/session`, {
            credentials: 'include',
            signal: AbortSignal.timeout(2000)
        });

        if (!res.ok) {
            limpiarSesionLocal();
            return null;
        }

        const data = await res.json();
        if (data.logged_in) {
            localStorage.setItem('usuario', JSON.stringify(data.usuario));
            return data.usuario;
        }

        limpiarSesionLocal();
    } catch (error) {
        console.log('API no disponible');
        limpiarSesionLocal();
    }

    return null;
}

function construirIniciales(nombre) {
    return (nombre || '').split(' ').filter(Boolean).map(p => p[0]).join('').substring(0, 2).toUpperCase();
}

function actualizarInfoUsuario(usuario) {
    if (!usuario) return;
    localStorage.setItem('usuario', JSON.stringify(usuario));

    document.querySelectorAll('.user-info').forEach(el => {
        const slot = el.querySelector('[data-user-name]');
        if (slot) slot.textContent = usuario.nombre;
        else el.innerHTML = `<i class="fas fa-bell me-2 text-secondary"></i><span>Hola, <span data-user-name>${usuario.nombre}</span></span>`;
    });

    const sidebarUser = document.querySelector('[data-sidebar-user-name]');
    if (sidebarUser) sidebarUser.textContent = usuario.nombre;

    const sidebarAvatar = document.querySelector('.sidebar .user-avatar');
    if (sidebarAvatar) sidebarAvatar.textContent = construirIniciales(usuario.nombre);
}

function redirigirALogin() {
    const p = window.location.pathname;
    let base = p.includes('/aside-patient/') || p.includes('/aside-professional/') ? '../../' : '../';
    window.location.href = base + 'login.html';
}

async function initAuthGuard(opt = {}) {
    const redirect = opt.redirect !== false;
    const usuario = await obtenerUsuarioActual();

    if (usuario) {
        actualizarInfoUsuario(usuario);
        return usuario;
    }

    if (redirect) redirigirALogin();
    return null;
}

document.addEventListener('DOMContentLoaded', () => {
    initAuthGuard();
});
