// chatbot.js - Lógica del chatbot emocional con consentimiento

document.addEventListener('DOMContentLoaded', function() {
    // Verificar consentimiento al cargar la página
    verificarConsentimiento();

    // Inicializar el chat
    inicializarChat();
});

async function verificarConsentimiento() {
    // Mostrar modal la primera vez que abre el chatbot
    console.log('Verificando consentimiento...');
    if (!localStorage.getItem('chatbot_modal_shown')) {
        console.log('Primera vez, mostrando modal');
        mostrarModalConsentimiento();
        return;
    }

    // Si ya vio el modal, verificar si dio consentimiento
    try {
        const response = await fetch('/api/paciente/consentimiento-chatbot', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();
        console.log('Consentimiento actual:', data);

        if (!data.consentimiento_chatbot) {
            // Si no dio consentimiento, mostrar modal de nuevo
            console.log('No tiene consentimiento, mostrando modal');
            mostrarModalConsentimiento();
        } else {
            console.log('Tiene consentimiento, no mostrar modal');
        }
    } catch (error) {
        console.error('Error verificando consentimiento:', error);
        // Si hay error, mostrar modal por seguridad
        mostrarModalConsentimiento();
    }
}

function mostrarModalConsentimiento() {
    const modalElement = document.getElementById('modalConsentimientoChatbot');
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement, {
            backdrop: 'static', // No cerrar al hacer clic fuera
            keyboard: false // No cerrar con ESC
        });
        modal.show();
    }
}

async function aceptarConsentimiento() {
    try {
        const response = await fetch('/api/paciente/consentimiento-chatbot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ consentimiento_chatbot: true }),
        });

        const data = await response.json();
        if (data.success) {
            localStorage.setItem('chatbot_modal_shown', 'true');
            cerrarModal();
        } else {
            alert('Error al guardar consentimiento');
        }
    } catch (error) {
        console.error('Error guardando consentimiento:', error);
        alert('Error al guardar consentimiento');
    }
}

function rechazarConsentimiento() {
    localStorage.setItem('chatbot_modal_shown', 'true');
    cerrarModal();
    // El chat funcionará pero con guardar=false
}

function cerrarModal() {
    const modalElement = document.getElementById('modalConsentimientoChatbot');
    if (modalElement) {
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    }
}

function inicializarChat() {
    const form = document.querySelector('.chat-form');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const input = form.querySelector('input[name="mensaje"]');
            const mensaje = input.value.trim();

            if (!mensaje) return;

            // Verificar consentimiento antes de enviar
            const tieneConsentimiento = await obtenerConsentimiento();
            const guardar = tieneConsentimiento;

            // Enviar mensaje
            await enviarMensaje(mensaje, guardar);

            input.value = '';
        });
    }
}

async function obtenerConsentimiento() {
    try {
        const response = await fetch('/api/paciente/consentimiento-chatbot');
        const data = await response.json();
        return data.consentimiento_chatbot || false;
    } catch (error) {
        console.error('Error obteniendo consentimiento:', error);
        return false;
    }
}

async function enviarMensaje(mensaje, guardar) {
    try {
        const response = await fetch('/api/chatbot/enviar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mensaje: mensaje,
                guardar: guardar
            }),
        });

        const data = await response.json();

        if (data.success) {
            // Mostrar respuesta en el chat
            mostrarRespuesta(data.respuesta);
        } else {
            alert('Error: ' + (data.message || 'Error desconocido'));
        }
    } catch (error) {
        console.error('Error enviando mensaje:', error);
        alert('Error al enviar mensaje');
    }
}

function mostrarRespuesta(respuesta) {
    // Implementar lógica para mostrar la respuesta en la interfaz
    // Esto depende de cómo esté estructurado el HTML del chat
    console.log('Respuesta del chatbot:', respuesta);
    // Aquí iría el código para agregar el mensaje al chat
}