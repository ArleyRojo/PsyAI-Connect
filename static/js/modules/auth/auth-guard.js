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
    // Intentar desde localStorage primero (respuesta instantánea)
    try {
        const cached = localStorage.getItem('usuario');
        if (cached) {
            const parsed = JSON.parse(cached);
            if (parsed && parsed.idUsuario) return parsed;
        }
    } catch {
        /* ignorar */
    }

    try {
        const res = await fetch(`${API}/api/session`, {
            credentials: 'include',
            signal: AbortSignal.timeout(5000)
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
        // No limpiar sesión local — podríamos estar offline momentáneamente
    }

    // Último recurso: si tenemos datos locales, usarlos aunque la API falló
    try {
        const cached = localStorage.getItem('usuario');
        if (cached) {
            const parsed = JSON.parse(cached);
            if (parsed && parsed.idUsuario) return parsed;
        }
    } catch {
        /* ignorar */
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
        else el.innerHTML = `
            <div class="user-avatar-sm">
                <i class="fas fa-user"></i>
            </div>
            <span class="fw-semibold">Hola, <span data-user-name>${usuario.nombre}</span></span>`;
    });

    const sidebarUser = document.querySelector('[data-sidebar-user-name]');
    if (sidebarUser) sidebarUser.textContent = usuario.nombre;

    const sidebarAvatar = document.querySelector('.sidebar .user-avatar');
    if (sidebarAvatar) {
        const iniciales = construirIniciales(usuario.nombre);
        sidebarAvatar.innerHTML = `<span style="font-weight:700;font-size:0.85rem;color:#1565C0;">${iniciales}</span>`;
    }
}

function redirigirALogin() {
    window.location.href = '/login.html';
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
