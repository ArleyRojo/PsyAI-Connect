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
