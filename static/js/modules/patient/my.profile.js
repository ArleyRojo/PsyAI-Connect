// my.profile.js - Lógica para la página de perfil del paciente

document.addEventListener('DOMContentLoaded', function() {
    cargarPerfil();
    cargarConsentimientoChatbot();
});

async function cargarPerfil() {
    try {
        // Cargar datos del perfil
        // Implementar según la lógica existente
    } catch (error) {
        console.error('Error cargando perfil:', error);
    }
}

async function cargarConsentimientoChatbot() {
    try {
        const response = await fetch('/api/paciente/consentimiento-chatbot');
        const data = await response.json();
        const span = document.getElementById('consentimiento-chatbot');
        if (span) {
            span.textContent = data.consentimiento_chatbot ? 'Concedido' : 'No concedido';
        }
    } catch (error) {
        console.error('Error cargando consentimiento chatbot:', error);
        const span = document.getElementById('consentimiento-chatbot');
        if (span) {
            span.textContent = 'Error al cargar';
        }
    }
}

async function revocarConsentimientoChatbot() {
    if (confirm('¿Estás seguro de que quieres revocar el consentimiento para almacenar tus conversaciones del chatbot?')) {
        try {
            const response = await fetch('/api/paciente/consentimiento-chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ consentimiento_chatbot: false }),
            });

            const data = await response.json();
            if (data.success) {
                alert('Consentimiento revocado exitosamente');
                cargarConsentimientoChatbot();
            } else {
                alert('Error al revocar consentimiento');
            }
        } catch (error) {
            console.error('Error revocando consentimiento:', error);
            alert('Error al revocar consentimiento');
        }
    }
}

// Funciones existentes para guardar perfil y preferencias
function guardarPerfil() {
    // Implementar
}

function guardarPreferencias() {
    // Implementar
}