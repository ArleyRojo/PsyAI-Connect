// ============================================================
// js/login.js
// ============================================================

document.addEventListener('DOMContentLoaded', function () {
    const roleBtns = document.querySelectorAll('.role-btn');
    const form = document.querySelector('form');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');

    roleBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            roleBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });

    function redirigir(rol) {
        if (rol === 'admin') window.location.href = 'admin.dashboard.html';
        else if (rol === 'profesional') window.location.href = 'professional.dashboard.html';
        else window.location.href = 'patient.dashboard.html';
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
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password, rol })
            });

            const data = await res.json();

            if (data.success) {
                localStorage.setItem('usuario', JSON.stringify(data.usuario));
                localStorage.removeItem('sessionUser');
                const nombre = data.usuario.nombre || email;
                const saludo = nombre.endsWith('a') ? 'Bienvenida, ' : 'Bienvenid@, ';
                mostrarToast(saludo + nombre + '!', 'success');
                setTimeout(() => redirigir(data.usuario.rol || rol), 900);
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
        }
    });

    form.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            form.requestSubmit();
        }
    });
});
