// ============================================================
// js/recover.js — Recuperación de contraseña
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('form');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value.trim();

        if (!email) {
            mostrarToast('Por favor ingresa tu correo electrónico.', 'warning');
            return;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            mostrarToast('El formato del correo no es válido.', 'warning');
            return;
        }

        try {
            const res  = await fetch('/api/recover', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email })
            });
            const data = await res.json();

            if (data.success) {
                mostrarToast('Si el correo existe, recibirás instrucciones de recuperación.', 'success');
                setTimeout(() => { window.location.href = 'login.html'; }, 2500);
            } else {
                mostrarToast(data.message || 'No se encontró ese correo.', 'danger');
            }
        } catch {
            mostrarToast('No se pudo conectar con el servidor.', 'danger');
        }
    });
});
