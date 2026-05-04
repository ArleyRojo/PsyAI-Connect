// Chatbot Emocional - Manejo de mensajes y detección de palabras de riesgo

let riskWords = [];
let totalTokens = 0;
let MAX_TOKENS = 1000; // Valor por defecto, se actualizará desde la configuración

// Función para estimar el número de tokens en un texto
function estimateTokens(text) {
    // Aproximación simple: dividir por 0.75 (promedio de caracteres por token en inglés)
    // En español podría ser similar, pero esto es una estimación básica
    if (!text) return 0;
    
    // Eliminar espacios extra y dividir por palabras
    const words = text.trim().split(/\s+/);
    // Estimación: ~0.75 palabras por token en promedio
    return Math.ceil(words.length / 0.75);
}

// Función para actualizar el contador de tokens en la interfaz
function updateTokenCount() {
    const tokenCountElement = document.getElementById('token-count');
    if (tokenCountElement) {
        tokenCountElement.textContent = `${totalTokens}/${MAX_TOKENS} tokens`;
        
        // Cambiar color si se acerca al límite
        if (totalTokens > MAX_TOKENS * 0.8) {
            tokenCountElement.classList.add('text-warning');
        } else {
            tokenCountElement.classList.remove('text-warning');
        }
        
        // Bloquear si se excede el límite
        if (totalTokens >= MAX_TOKENS) {
            tokenCountElement.classList.add('text-danger');
            bloquearChatbotPorTokens();
        } else {
            tokenCountElement.classList.remove('text-danger');
        }
    }
}

// Función para bloquear el chatbot cuando se excede el límite de tokens
function bloquearChatbotPorTokens() {
    const chatbotSection = document.getElementById('chatbot-section');
    if (!chatbotSection) return;
    
    chatbotSection.classList.add('chatbot-consent-blocked');
    chatbotSection.setAttribute('aria-disabled', 'true');
    
    const formControls = chatbotSection.querySelectorAll('input, button, textarea, select');
    formControls.forEach(function(control) {
        control.disabled = true;
    });
    
    // Mostrar mensaje de límite alcanzado
    const chatArea = document.querySelector('.chat-area');
    if (chatArea) {
        const limitMessage = document.createElement('div');
        limitMessage.classList.add('message', 'bot-message', 'text-center', 'mt-3');
        limitMessage.innerHTML = `<small class="text-danger"><i class="fas fa-exclamation-triangle me-2"></i>Has alcanzado el límite máximo de ${MAX_TOKENS} tokens. Por favor, elimina el historial para continuar.</small>`;
        chatArea.appendChild(limitMessage);
        chatArea.scrollTop = chatArea.scrollHeight;
    }
}

// Función para cargar la configuración del chatbot desde el administrador
async function cargarChatbotConfig() {
    try {
        const res = await fetch('/api/admin/chatbot-config', { credentials: 'include' });
        const data = await res.json();
        if (data.success && data.config) {
            // Actualizar palabras de riesgo
            if (data.config.risk_terms) {
                riskWords = data.config.risk_terms.split(',').map(p => p.trim().toLowerCase()).filter(p => p);
            }
            
            // Actualizar límite de tokens
            if (data.config.token_limit !== undefined && data.config.token_limit !== null) {
                MAX_TOKENS = parseInt(data.config.token_limit) || 1000;
                // Actualizar la visualización inmediatamente
                updateTokenCount();
            }
        }
    } catch (e) {
        console.error('Error al cargar la configuración del chatbot:', e);
        // Mantener valores por defecto
        riskWords = [];
        MAX_TOKENS = 1000;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Cargar configuración completa del chatbot (incluyendo límite de tokens y palabras de riesgo)
    cargarChatbotConfig().then(() => {
        const chatForm = document.querySelector('.chat-input-area');
        const chatInput = chatForm.querySelector('input[name="mensaje"]');
        const chatArea = document.querySelector('.chat-area');
        const btnClearChat = document.getElementById('btn-clear-chat');
        const btnEmojiPicker = document.getElementById('btn-emoji-picker');
        const emojiPicker = document.getElementById('emoji-picker');
        const btnQuickResponses = document.getElementById('btn-quick-responses');
        const quickResponsesPicker = document.getElementById('quick-responses-picker');
        
        // Inicializar contador de tokens
        updateTokenCount();
    
    // Las palabras de riesgo se cargan dinámicamente desde la configuración del admin
    
    // Respuestas automáticas para crisis (fallback)
    const crisisResponses = [
        "Lamento mucho que te sientas así. Tu vida es importante y hay personas que quieren ayudarte.",
        "Entiendo que estás pasando por un momento difícil. No estás solo/a, hay apoyo disponible.",
        "Es valiente de tu parte compartir estos sentimientos. Hay profesionales preparados para ayudarte.",
        "Tu dolor es real y merece atención. Hay recursos y personas que pueden apoyarte en este momento."
    ];
    
    // Opciones de respuesta rápida para crisis
    const crisisQuickReplies = [
        { text: "Quiero hablar con un profesional ahora", action: "professional" },
        { text: "Necesito información de líneas de ayuda", action: "hotlines" },
        { text: "Me siento un poco mejor, gracias", action: "better" },
        { text: "Solo necesitaba expresarlo", action: "expressed" }
    ];
    
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
         
         // Actualizar contador de tokens
         totalTokens += estimateTokens(content);
         updateTokenCount();
     }
    
    // Función para mostrar opciones de respuesta rápida en crisis
    function showCrisisQuickReplies() {
        const quickReplyContainer = document.createElement('div');
        quickReplyContainer.classList.add('quick-reply-container', 'mt-3');
        
        crisisQuickReplies.forEach(option => {
            const btn = document.createElement('button');
            btn.classList.add('btn', 'btn-outline-primary', 'btn-sm', 'me-2', 'mb-2');
            btn.textContent = option.text;
            btn.dataset.action = option.action;
            
            btn.addEventListener('click', function() {
                // Simular que el usuario envió esta respuesta
                addMessage(this.textContent, 'user');
                // Deshabilitar todos los botones
                document.querySelectorAll('.quick-reply-container button').forEach(b => {
                    b.disabled = true;
                    b.classList.remove('btn-outline-primary');
                    b.classList.add('btn-secondary');
                });
                // Aquí podrías agregar lógica adicional según la acción seleccionada
                if (this.dataset.action === 'professional') {
                    setTimeout(() => {
                        addMessage("Entiendo que deseas hablar con un profesional. Te recomiendo contactar con tu terapeuta o buscar servicios de salud mental en tu área. Si necesitas ayuda inmediata, considera llamar a una línea de emergencia.", 'bot');
                    }, 500);
                } else if (this.dataset.action === 'hotlines') {
                    setTimeout(() => {
                        addMessage("Algunas líneas de ayuda disponibles:\n• Línea Nacional de Prevención del Suicidio: ****\n• Servicio de Atención Psicológica de Emergencia: ****\n• Chat de apoyo emocional: ****\n\nRecuerda que en caso de emergencia inmediata, llama al 911 o al número de emergencias de tu país.", 'bot');
                    }, 500);
                } else {
                    setTimeout(() => {
                        addMessage("Gracias por compartir. Estoy aquí para apoyarte en lo que necesites.", 'bot');
                    }, 500);
                }
            });
            
            quickReplyContainer.appendChild(btn);
        });
        
        chatArea.appendChild(quickReplyContainer);
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
    
    // Función para detectar palabras de riesgo en el texto
    function containsRiskWords(text) {
        const lowerText = text.toLowerCase();
        return riskWords.some(word => lowerText.includes(word));
    }
    
    // Manejar el envío del formulario
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = chatInput.value.trim();
        if (message === '') return;
        
        // Agregar mensaje del usuario
        addMessage(message, 'user');
        chatInput.value = '';
        
        // Verificar palabras de riesgo
        if (containsRiskWords(message)) {
            // Respuesta de crisis
            const crisisResponse = crisisResponses[Math.floor(Math.random() * crisisResponses.length)];
            setTimeout(() => {
                addMessage(crisisResponse, 'bot');
                // Mostrar opciones de respuesta rápida
                showCrisisQuickReplies();
            }, 800);
        } else {
            // Respuesta normal (puedes reemplazar esto con integración a una API de IA)
            const normalResponses = [
                "Gracias por compartir eso conmigo. ¿Te gustaría profundizar en cómo te sientes?",
                "Entiendo. ¿Ha estado sintiéndote así por mucho tiempo?",
                "Gracias por confiar en mí. ¿Hay algo específico que quieras hablar?",
                "Aprecio que te abras conmigo. ¿Qué te haría sentir mejor en este momento?"
            ];
            const normalResponse = normalResponses[Math.floor(Math.random() * normalResponses.length)];
            setTimeout(() => {
                addMessage(normalResponse, 'bot');
            }, 800);
        }
    });
    
// Limpiar chat
      btnClearChat.addEventListener('click', async function() {
          if (confirm('¿Estás seguro de que quieres eliminar todo el chat?')) {
              if (confirm('El historial se eliminará permanentemente. ¿Continuar?')) {
                  try {
                      await fetch('/api/chatbot/historial', {
                          method: 'DELETE',
                          credentials: 'include'
                      });
                  } catch(err) {
                      console.warn('No se pudo eliminar historial remoto:', err);
                  }
                  chatArea.innerHTML = '';
                  // Reset token count
                  totalTokens = 0;
                  updateTokenCount();
              }
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