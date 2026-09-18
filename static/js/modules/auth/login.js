// ============================================================
// js/login.js
// ============================================================

document.addEventListener('DOMContentLoaded', function () {
    const roleBtns = document.querySelectorAll('.role-btn');
    const form = document.querySelector('form');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    let isSubmitting = false;
    let redirectingActiveSession = false;
    let transitionBackGuardInstalled = false;

    function bloquearAtrasDuranteTransicion() {
        if (transitionBackGuardInstalled) return;
        transitionBackGuardInstalled = true;

        const guardState = { psyaiLoginTransitionGuard: true };
        history.pushState(guardState, '', window.location.href);
        window.addEventListener('popstate', function () {
            history.pushState(guardState, '', window.location.href);
        });
    }

    async function redirigirSiSesionActiva() {
        if (redirectingActiveSession) return;

        try {
            const res = await fetch('/api/session', {
                credentials: 'include',
                cache: 'no-store'
            });
            if (!res.ok) return;

            const data = await res.json();
            if (!data.logged_in || !data.usuario) return;

            redirectingActiveSession = true;
            localStorage.setItem('usuario', JSON.stringify(data.usuario));
            const rol = data.usuario.rol;
            bloquearAtrasDuranteTransicion();
            mostrarOverlayCierreSesion('Volviendo a tu sesión...');
            setTimeout(() => redirigir(rol), 900);
        } catch (_) {
            // El formulario sigue disponible si la API no responde.
        }
    }

    redirigirSiSesionActiva();
    window.addEventListener('pageshow', function () {
        redirigirSiSesionActiva();
    });

    roleBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            roleBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });

    const submitBtn = form.querySelector('button[type="submit"]');
    const submitText = submitBtn ? submitBtn.querySelector('.btn-text') : null;
    const originalBtnText = submitText ? submitText.textContent : 'Entrar';

    function setLoading(loading) {
        if (!submitBtn || !submitText) return;
        submitBtn.disabled = loading;
        if (loading) {
            submitText.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Iniciando sesión...';
        } else {
            submitText.textContent = originalBtnText;
        }
    }

    const savedEmail = localStorage.getItem('savedEmail');
    const savedPassword = localStorage.getItem('savedPassword');
    const recordarLogin = document.getElementById('recordar-login');
    if (savedEmail) {
        emailInput.value = savedEmail;
        if (recordarLogin) recordarLogin.checked = true;
    }
    if (savedPassword) {
        passwordInput.value = savedPassword;
    }

    function redirigir(rol) {
        if (rol === 'admin') window.location.replace('admin.dashboard.html');
        else if (rol === 'profesional') window.location.replace('professional.dashboard.html');
        else window.location.replace('patient.dashboard.html');
    }

    function validar(email, password, activeRoleBtn) {
        if (!email && !password) {
            return { ok: false, msg: 'Por favor completa todos los campos.', tipo: 'warning' };
        }
        if (!email) {
            return { ok: false, msg: 'El correo electronico es obligatorio.', tipo: 'warning' };
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            return { ok: false, msg: 'El formato del correo no es valido.', tipo: 'warning' };
        }
        if (!password) {
            return { ok: false, msg: 'La contrasena es obligatoria.', tipo: 'warning' };
        }
        if (password.length < 6) {
            return { ok: false, msg: 'La contrasena debe tener al menos 6 caracteres.', tipo: 'warning' };
        }
        if (!activeRoleBtn) {
            return { ok: false, msg: 'Por favor selecciona un rol.', tipo: 'warning' };
        }
        return { ok: true };
    }

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        if (isSubmitting) return;

        const email = emailInput.value.trim();
        const password = passwordInput.value.trim();
        const activeRoleBtn = document.querySelector('.role-btn.active');
        const rol = activeRoleBtn ? activeRoleBtn.dataset.role : 'paciente';

        const v = validar(email, password, activeRoleBtn);
        if (!v.ok) {
            mostrarToast(v.msg, v.tipo);
            return;
        }

        try {
            setLoading(true);
            await new Promise(resolve => setTimeout(resolve, 2000));
            isSubmitting = true;
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password, rol })
            });

            const data = await res.json();

            if (data.success) {
                if (recordarLogin && recordarLogin.checked) {
                    localStorage.setItem('savedEmail', email);
                    localStorage.setItem('savedPassword', password);
                } else {
                    localStorage.removeItem('savedEmail');
                    localStorage.removeItem('savedPassword');
                }
                localStorage.setItem('usuario', JSON.stringify(data.usuario));
                localStorage.removeItem('sessionUser');
                sessionStorage.setItem('psyai_login_return_guard', '1');
                const nombre = data.usuario.nombre || email;
                const saludo = nombre.endsWith('a') ? 'Bienvenida, ' : 'Bienvenid@, ';
                bloquearAtrasDuranteTransicion();
                if (typeof mostrarOverlayCierreSesion === 'function') {
                    mostrarOverlayCierreSesion('Iniciando sesión...');
                } else {
                    mostrarToast(saludo + nombre + '!', 'success');
                }
                setTimeout(() => redirigir(data.usuario.rol || rol), 1800);
            } else if (res.status === 401) {
                mostrarToast('Credenciales incorrectas. Verifica tu correo y contrasena.', 'danger');
            } else if (res.status === 403) {
                mostrarToast('Tu cuenta esta inactiva o suspendida. Contacta al soporte.', 'danger');
            } else if (res.status === 400) {
                mostrarToast('Datos incompletos. Por favor completa todos los campos.', 'warning');
            } else {
                mostrarToast(data.message || 'Error al iniciar sesion.', 'danger');
            }
        } catch {
            localStorage.removeItem('usuario');
            localStorage.removeItem('sessionUser');
            mostrarToast('No fue posible iniciar sesion. Verifica que el servidor este disponible e intenta nuevamente.', 'danger');
        } finally {
            isSubmitting = false;
            setLoading(false);
        }
    });

    form.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            form.requestSubmit();
        }
    });
});
