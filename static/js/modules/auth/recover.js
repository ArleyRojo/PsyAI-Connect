// Password recovery and reset flow.

function showRecoverMessage(elementId, message, type) {
    const alert = document.getElementById(elementId);
    if (!alert) {
        if (typeof mostrarToast === 'function') {
            mostrarToast(message, type === 'success' ? 'success' : 'danger');
        }
        return;
    }

    alert.className = `alert-box ${type}`;
    alert.textContent = message;
    alert.style.display = 'block';
}

function setSubmitState(form, loading) {
    const button = form ? form.querySelector('button[type="submit"]') : null;
    if (!button) return;

    if (!button.dataset.originalHtml) {
        button.dataset.originalHtml = button.innerHTML;
    }
    button.disabled = loading;
    button.innerHTML = loading
        ? '<i class="fas fa-spinner fa-spin me-1"></i> Enviando...'
        : button.dataset.originalHtml;
}

async function handleForgotPassword(form) {
    const emailInput = document.getElementById('email');
    const email = emailInput ? emailInput.value.trim() : '';

    if (!email) {
        mostrarToast('Ingresa tu correo electr\u00f3nico.', 'warning');
        return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        mostrarToast('El formato del correo no es v\u00e1lido.', 'warning');
        return;
    }

    setSubmitState(form, true);
    try {
        const res = await fetch('/api/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email })
        });
        const data = await res.json().catch(() => ({}));

        if (!res.ok || data.success === false) {
            mostrarToast(data.message || 'No se pudo enviar el enlace.', 'danger');
            return;
        }

        mostrarToast(data.message || 'Fue enviado al correo.', 'success');
        if (data.recovery_link) {
            console.log('Enlace de recuperaci\u00f3n:', data.recovery_link);
        }
    } catch (error) {
        mostrarToast('No se pudo conectar con el servidor.', 'danger');
    } finally {
        setSubmitState(form, false);
    }
}

async function handleResetPassword(form) {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token') || '';
    const password = document.getElementById('new_password')?.value || '';
    const confirm = document.getElementById('confirm_password')?.value || '';

    if (!token) {
        document.getElementById('tokenError')?.classList.remove('d-none');
        showRecoverMessage('resetAlert', 'El enlace de recuperacion no tiene token.', 'error');
        return;
    }
    if (!password || !confirm) {
        showRecoverMessage('resetAlert', 'Completa la nueva contrasena y su confirmacion.', 'error');
        return;
    }
    if (password !== confirm) {
        showRecoverMessage('resetAlert', 'Las contrasenas no coinciden.', 'error');
        return;
    }

    setSubmitState(form, true);
    try {
        const res = await fetch('/api/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                token,
                new_password: password,
                confirm_password: confirm
            })
        });
        const data = await res.json().catch(() => ({}));

        if (!res.ok || data.success === false) {
            showRecoverMessage('resetAlert', data.message || 'No se pudo restablecer la contrasena.', 'error');
            return;
        }

        showRecoverMessage('resetAlert', data.message || 'Contrasena actualizada correctamente.', 'success');
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 1800);
    } catch (error) {
        showRecoverMessage('resetAlert', 'No se pudo conectar con el servidor.', 'error');
    } finally {
        setSubmitState(form, false);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const recoverForm = document.getElementById('recoverForm');
    if (recoverForm) {
        recoverForm.addEventListener('submit', (event) => {
            event.preventDefault();
            handleForgotPassword(recoverForm);
        });
    }

    const resetForm = document.getElementById('resetForm');
    if (resetForm) {
        const token = new URLSearchParams(window.location.search).get('token');
        if (!token) {
            document.getElementById('tokenError')?.classList.remove('d-none');
            resetForm.classList.add('d-none');
        }
        resetForm.addEventListener('submit', (event) => {
            event.preventDefault();
            handleResetPassword(resetForm);
        });
    }
});

/* ──────────────────────────────
   FONDO ANIMADO — PARTÍCULAS
   ────────────────────────────── */
(function () {
    const canvas = document.getElementById('bgCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W = 0, H = 0;

    const LIGHT = [[144,202,249],[100,181,246],[179,229,252],[33,150,243],[207,226,255],[66,165,245],[21,101,192]];
    const DARK  = [[74,134,240],[30,80,160],[15,52,120],[100,160,255],[50,110,210],[20,70,180],[10,40,100]];

    function isDark() { return document.documentElement.classList.contains('dark-mode'); }
    function resize() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }

    function mkParticle(startY) {
        const pal = isDark() ? DARK : LIGHT;
        const c   = pal[Math.floor(Math.random() * pal.length)];
        const op  = isDark() ? (0.22 + Math.random() * 0.32) : (0.30 + Math.random() * 0.38);
        const r   = 5 + Math.random() * 18;
        return {
            x: 10 + Math.random() * Math.max(W - 20, 100),
            y: startY !== undefined ? startY : H + r,
            r,
            vx: (Math.random() - 0.5) * 0.5,
            vy: -(0.35 + Math.random() * 0.65),
            color: `rgba(${c[0]},${c[1]},${c[2]},${op.toFixed(2)})`
        };
    }

    let particles = [];
    function init() {
        resize();
        particles = [];
        for (let i = 0; i < 45; i++) {
            particles.push(mkParticle(Math.random() * H));
        }
    }

    function draw() {
        ctx.clearRect(0, 0, W, H);
        for (let p of particles) {
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.fill();
        }
    }

    function update() {
        for (let p of particles) {
            p.x += p.vx;
            p.y += p.vy;
            if (p.y + p.r < 0 || p.x + p.r < 0 || p.x - p.r > W) {
                Object.assign(p, mkParticle());
            }
        }
    }

    function loop() {
        update();
        draw();
        requestAnimationFrame(loop);
    }

    window.addEventListener('resize', () => { resize(); });
    init();
    loop();
})();
