// Chatbot Emocional - Manejo de mensajes y detección de palabras de riesgo

// Cambio: el frontend ya no detecta palabras de riesgo; el backend se encarga.

// Cambio: usa el endpoint de paciente y no parsea risk_terms en el frontend.
async function cargarChatbotConfig() {
    try {
        const res = await fetch('/api/chatbot/config', { credentials: 'include' });
        if (!res.ok) {
            console.warn('No se pudo cargar la configuración del chatbot:', res.status);
            return null;
        }
        const data = await res.json();
        return data.success ? data.config : null;
    } catch (e) {
        console.error('Error al cargar la configuración del chatbot:', e);
        return null;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    cargarChatbotConfig();
        const chatForm = document.querySelector('.chat-input-area');
        const chatInput = chatForm.querySelector('input[name="mensaje"]');
        const chatArea = document.querySelector('.chat-area');
        const btnClearChat = document.getElementById('btn-clear-chat');
        const btnEmojiPicker = document.getElementById('btn-emoji-picker');
        const emojiPicker = document.getElementById('emoji-picker');
        const btnQuickResponses = document.getElementById('btn-quick-responses');
        const quickResponsesPicker = document.getElementById('quick-responses-picker');
    
    // Respuestas rápidas comunes (para usar en cualquier momento)
    const commonQuickReplies = [
        { text: "Estoy ansioso/a", action: "anxious" },
        { text: "Estoy triste", action: "sad" },
        { text: "Estoy enfadado/a", action: "angry" },
        { text: "Me siento solo/a", action: "lonely" },
        { text: "Necesito hablar", action: "talk" },
        { text: "Gracias por escucharme", action: "thanks" }
    ];
    
     // Función para agregar un mensaje al chat
    function addMessage(content, sender = 'bot') {
         const messageDiv = document.createElement('div');
         messageDiv.classList.add('message', `${sender}-message`);
         
         // Si es una respuesta rápida, mostrarla como botón deshabilitado después de hacer clic
         if (sender === 'quick-reply') {
             messageDiv.innerHTML = `<span class="quick-reply">${content}</span>`;
             messageDiv.style.opacity = '0.7';
             messageDiv.style.cursor = 'default';
         } else {
             messageDiv.textContent = content;
         }
         
         chatArea.appendChild(messageDiv);
         // Scroll al final
         chatArea.scrollTop = chatArea.scrollHeight;
     }

    // Función para mostrar respuestas rápidas comunes
    function showCommonQuickReplies() {
        // Limpiar contenido previo
        quickResponsesPicker.innerHTML = '';
        quickResponsesPicker.style.display = 'block';
        
        commonQuickReplies.forEach(option => {
            const btn = document.createElement('button');
            btn.classList.add('btn', 'btn-outline-secondary', 'btn-sm', 'me-1', 'mb-1');
            btn.textContent = option.text;
            btn.dataset.action = option.action;
            
            btn.addEventListener('click', function() {
                // Simular que el usuario envió esta respuesta
                addMessage(this.textContent, 'user');
                // Ocultar el picker
                quickResponsesPicker.style.display = 'none';
                // Deshabilitar brevemente el botón para evitar doble clic
                btn.disabled = true;
                setTimeout(() => btn.disabled = false, 1000);
                
                // Respuesta del bot según la acción
                setTimeout(() => {
                    let botResponse = "";
                    switch (this.dataset.action) {
                        case "anxious":
                            botResponse = "Entiendo que estás sintiendo ansiedad. ¿Te gustaría que te enseñe algunas técnicas de respiración para calmarte?";
                            break;
                        case "sad":
                            botResponse = "Lamento que te sientas triste. Recuerda que está bien sentir estas emociones. ¿Hay algo específico que esté causando esta tristeza?";
                            break;
                        case "angry":
                            botResponse = "La ira es una emoción válida. ¿Quieres contarme qué te hizo sentir así? A veces expresarlo ayuda a procesarlo.";
                            break;
                        case "lonely":
                            botResponse = "Sentirse solo/a puede ser muy difícil. Recuerda que estoy aquí para escucharte. ¿Te gustaría sugerirte algunas actividades que podrían ayudarte a sentirte más conectado/a?";
                            break;
                        case "talk":
                            botResponse = "Claro que sí, estoy aquí para escucharte. ¿De qué te gustaría hablar? Puedes contarme lo que sea, sin juicios.";
                            break;
                        case "thanks":
                            botResponse = "De nada. Estoy aquí para apoyarte siempre que lo necesites. ¿Hay algo más en lo que pueda ayudarte?";
                            break;
                        default:
                            botResponse = "Gracias por compartir. Estoy aquí para apoyarte.";
                    }
                    addMessage(botResponse, 'bot');
                }, 500);
            });
            
            quickResponsesPicker.appendChild(btn);
        });
        
        // Añadir botón para cerrar el picker
        const closeBtn = document.createElement('button');
        closeBtn.classList.add('btn', 'btn-link', 'p-0', 'mt-2');
        closeBtn.innerHTML = '<i class="fas fa-times"></i> Cerrar';
        closeBtn.addEventListener('click', function() {
            quickResponsesPicker.style.display = 'none';
        });
        quickResponsesPicker.appendChild(closeBtn);
    }
    // Manejar el envío del formulario
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = chatInput.value.trim();
        if (message === '') return;
        
        // Agregar mensaje del usuario
        addMessage(message, 'user');
        chatInput.value = '';

        // Cambio: siempre se envía al backend para que detecte riesgo, guarde en BD y notifique.
        try {
            const res = await fetch('/api/chatbot/enviar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ mensaje: message })
            });
            const data = await res.json();

            // Cambio: se actualiza el contador diario con la respuesta real del backend.
            if (data.used !== undefined && data.limit !== undefined) {
                const counter = document.getElementById('msg-counter');
                if (counter) {
                    const remaining = data.limit - data.used;
                    counter.textContent = `Mensajes hoy: ${data.used} / ${data.limit}`;
                    counter.className = remaining <= 3
                        ? 'text-danger small'
                        : remaining <= 5
                            ? 'text-warning small'
                            : 'text-muted small';
                }
            }

            if (!data.success && data.limit_reached) {
                setTimeout(() => addMessage(data.message, 'bot'), 300);
                chatInput.disabled = true;
                chatInput.placeholder = 'Limite diario alcanzado. Vuelve manana.';
                chatForm.querySelector('button[type="submit"]').disabled = true;
                return;
            }

            const botReply = data.respuesta || data.message || "No pude procesar tu mensaje.";
            setTimeout(() => addMessage(botReply, 'bot'), 300);
        } catch (err) {
            setTimeout(() => addMessage("Hubo un error al conectar con el servidor.", 'bot'), 300);
        }
    });
    
// Limpiar chat
      btnClearChat.addEventListener('click', async function() {
          // Cambio: un solo confirm claro, sin reset de contador de tokens en frontend.
          if (confirm('¿Eliminar todo el historial? Esta acción no se puede deshacer.')) {
              try {
                  await fetch('/api/chatbot/historial', {
                      method: 'DELETE',
                      credentials: 'include'
                  });
              } catch(err) {
                  console.warn('No se pudo eliminar historial remoto:', err);
              }
              chatArea.innerHTML = '';
          }
      });
    
    // Alternar selector de emojis
    btnEmojiPicker.addEventListener('click', function() {
        const isVisible = emojiPicker.style.display === 'block' || emojiPicker.style.display === '';
        emojiPicker.style.display = isVisible ? 'none' : 'block';
        // Ocultar picker de respuestas rápidas si está abierto
        quickResponsesPicker.style.display = 'none';
    });
    
    // Alternar selector de respuestas rápidas
    btnQuickResponses.addEventListener('click', function() {
        const isVisible = quickResponsesPicker.style.display === 'block';
        quickResponsesPicker.style.display = isVisible ? 'none' : 'block';
        if (!isVisible) {
            showCommonQuickReplies(); // Mostrar las respuestas rápidas comunes
        }
        // Ocultar picker de emojis si está abierto
        emojiPicker.style.display = 'none';
    });
    
    // Cerrar pickers al hacer clic fuera de ellos
    document.addEventListener('click', function(e) {
        if (!chatForm.contains(e.target) && !emojiPicker.contains(e.target) && !quickResponsesPicker.contains(e.target)) {
            emojiPicker.style.display = 'none';
            quickResponsesPicker.style.display = 'none';
        }
    });
});

// Para evitar que el formulario se envíe al presionar Enter en el campo de emojis (si lo hubiera)
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.target.classList.contains('emoji-picker')) {
        e.preventDefault();
    }
});
