// ============================================================
// js/aside-patient/chatbot.js — Chatbot Emocional
// ============================================================

let historialChat = [];
const MAX_MENSAJES = 50;
const DEFAULT_MAX_MENSAJES = 420;
let chatStorageKey = null;
let isFullscreen = false;
let maxMensajesChatbot = DEFAULT_MAX_MENSAJES;
let chatbotConfigEventSource = null;

function obtenerFechaChatActual() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

document.addEventListener('DOMContentLoaded', async function() {
    await cargarConfiguracionChatbot();
    await inicializarChat();
    configurarFormulario();
    actualizarMensajesRestantes();
    configurarActualizacionConfigChatbot();
    configurarSelectorEmojis();
    configurarEliminarChat();
    configurarFullscreen();
});

async function cargarConfiguracionChatbot() {
    aplicarMaxMensajesDesdeStorage();

    try {
        const res = await fetch('/api/chatbot/config', {
            credentials: 'include',
            signal: AbortSignal.timeout(3000)
        });

        if (!res.ok) {
            actualizarMensajesRestantes();
            return;
        }

        const data = await res.json();
        const maxMensajes = Number(data.config?.max_tokens);

        if (Number.isFinite(maxMensajes) && maxMensajes > 0) {
            maxMensajesChatbot = maxMensajes;
        }
    } catch(err) {
        console.warn('No se pudo cargar configuración del chatbot:', err.message);
    }

    actualizarMensajesRestantes();
}

function aplicarMaxMensajesDesdeStorage() {
    try {
        aplicarMaxMensajes(localStorage.getItem('chatbotConfigMaxTokens'));
    } catch(e) {}
}

function aplicarMaxMensajes(value) {
    const maxMensajes = Number(value);
    if (Number.isFinite(maxMensajes) && maxMensajes > 0 && maxMensajes !== maxMensajesChatbot) {
        maxMensajesChatbot = maxMensajes;
        actualizarMensajesRestantes();
    }
}

async function inicializarChat() {
    const chatContainer = document.querySelector('#chatbot-section .chat-area');
    if (!chatContainer) return;

    chatStorageKey = await obtenerClaveHistorial();
    
    const historialRemoto = await cargarHistorialRemoto();
    console.log('Historial remoto:', historialRemoto);
    
    if (Array.isArray(historialRemoto) && historialRemoto.length > 0) {
        historialChat = historialRemoto;
        guardarHistorial();
        renderizarMensajes();
        actualizarMensajesRestantes();
        console.log('Cargado desde historial remoto, mensajes:', historialChat.length);
        return;
    }

    const stored = chatStorageKey ? localStorage.getItem(chatStorageKey) : null;
    if (stored && chatStorageKey) {
        try {
            historialChat = obtenerHistorialLocalDelDia(stored);
            if (historialChat.length > 0) {
                renderizarMensajes();
                actualizarMensajesRestantes();
                console.log('Cargado desde localStorage, mensajes:', historialChat.length);
                return;
            }
        } catch(e) {
            console.error('Error parsing chat history:', e);
        }
    }

    console.log('No hay historial, mostrando saludo inicial');
    mostrarSaludoInicial();
}

function mostrarSaludoInicial() {
    const chatContainer = document.querySelector('#chatbot-section .chat-area');
    if (!chatContainer) return;

    historialChat = [{ tipo: 'bot', mensaje: '¡Hola! Soy tu asistente emocional. ¿Cómo te sientes hoy?' }];
    guardarHistorial();
    renderizarMensajes();
}

function renderizarMensajes() {
    const chatContainer = document.querySelector('#chatbot-section .chat-area');
    if (!chatContainer) return;

    chatContainer.innerHTML = historialChat.map(m => {
        if (m.tipo === 'usuario') {
            return `<div class="message user">
                <div class="bubble">
                    <strong>Tú</strong>
                    ${escapeHtml(m.mensaje)}
                </div>
            </div>`;
        } else {
            return `<div class="message bot">
                <div class="avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="bubble">
                    <strong>PsyAI</strong>
                    ${escapeHtml(m.mensaje)}
                </div>
            </div>`;
        }
    }).join('');

    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function configurarFormulario() {
    const form = document.querySelector('#chatbot-section form');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const input = form.querySelector('input[name="mensaje"]');
        const mensaje = input.value.trim();
        
        if (!mensaje) return;
        if (calcularMensajesRestantes() <= 0) {
            if (typeof showAlert === 'function') {
                showAlert('warning', 'No tienes mensajes restantes disponibles.', 'Limite alcanzado');
            }
            return;
        }

        agregarMensajeUsuario(mensaje);
        input.value = '';
        actualizarMensajesRestantes();

        await enviarMensaje(mensaje);
    });
}

function configurarActualizacionConfigChatbot() {
    window.addEventListener('focus', cargarConfiguracionChatbot);
    window.addEventListener('storage', function(e) {
        if (e.key === 'chatbotConfigMaxTokens') {
            aplicarMaxMensajes(e.newValue);
        }
    });

    try {
        const channel = new BroadcastChannel('chatbot-config');
        channel.addEventListener('message', function(e) {
            aplicarMaxMensajes(e.data?.max_tokens);
        });
    } catch(e) {}

    configurarEventosConfigChatbot();

    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            cargarConfiguracionChatbot();
        }
    });
}

function configurarEventosConfigChatbot() {
    if (!window.EventSource || chatbotConfigEventSource) return;

    chatbotConfigEventSource = new EventSource('/api/chatbot/config/events');
    chatbotConfigEventSource.addEventListener('chatbot-config', function(event) {
        try {
            const data = JSON.parse(event.data);
            aplicarMaxMensajes(data.max_tokens);
        } catch(e) {
            console.warn('No se pudo leer actualizacion de configuracion:', e);
        }
    });
}

function contarMensajesUsuario() {
    return historialChat.filter(m => m.tipo === 'usuario').length;
}

function calcularMensajesRestantes() {
    return Math.max(maxMensajesChatbot - contarMensajesUsuario(), 0);
}

function actualizarMensajesRestantes() {
    const messageCount = document.getElementById('message-count');
    if (!messageCount) return;

    const restantes = calcularMensajesRestantes();
    messageCount.textContent = `${restantes} mensajes restantes`;
    messageCount.classList.toggle('text-danger', restantes === 0);
    messageCount.classList.toggle('fw-semibold', restantes <= 5);
}
function configurarSelectorEmojis() {
    const btnEmoji = document.getElementById('btn-emoji-picker');
    const picker = document.getElementById('emoji-picker');
    const input = document.querySelector('#chatbot-section input[name="mensaje"]');

    if (!btnEmoji || !picker || !input) return;

    btnEmoji.addEventListener('click', function(e) {
        e.stopPropagation();
        const isOpen = picker.classList.toggle('active');
        btnEmoji.classList.toggle('active', isOpen);
        btnEmoji.setAttribute('aria-expanded', String(isOpen));
    });

    picker.querySelectorAll('button').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            insertarEmoji(input, btn.textContent);
            picker.classList.remove('active');
            btnEmoji.classList.remove('active');
            btnEmoji.setAttribute('aria-expanded', 'false');
        });
    });

    document.addEventListener('click', function(e) {
        if (picker.contains(e.target) || btnEmoji.contains(e.target)) return;
        picker.classList.remove('active');
        btnEmoji.classList.remove('active');
        btnEmoji.setAttribute('aria-expanded', 'false');
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            picker.classList.remove('active');
            btnEmoji.classList.remove('active');
            btnEmoji.setAttribute('aria-expanded', 'false');
        }
    });
}

function insertarEmoji(input, emoji) {
    const start = input.selectionStart ?? input.value.length;
    const end = input.selectionEnd ?? input.value.length;
    input.value = input.value.slice(0, start) + emoji + input.value.slice(end);
    const cursor = start + emoji.length;
    input.focus();
    input.setSelectionRange(cursor, cursor);
}

function agregarMensajeUsuario(mensaje) {
    historialChat.push({ tipo: 'usuario', mensaje: mensaje });
    guardarHistorial();
    renderizarMensajes();
}

function agregarMensajeBot(mensaje) {
    historialChat.push({ tipo: 'bot', mensaje: mensaje });
    guardarHistorial();
    renderizarMensajes();
}

function guardarHistorial() {
    if (historialChat.length > MAX_MENSAJES) {
        historialChat = historialChat.slice(-MAX_MENSAJES);
    }
    if (!chatStorageKey) return;
    localStorage.setItem(chatStorageKey, JSON.stringify({
        fecha: obtenerFechaChatActual(),
        mensajes: historialChat
    }));
}

function obtenerHistorialLocalDelDia(stored) {
    const parsed = JSON.parse(stored);
    const fechaActual = obtenerFechaChatActual();

    if (Array.isArray(parsed)) {
        localStorage.removeItem(chatStorageKey);
        return [];
    }

    if (!parsed || parsed.fecha !== fechaActual || !Array.isArray(parsed.mensajes)) {
        localStorage.removeItem(chatStorageKey);
        return [];
    }

    return parsed.mensajes;
}

async function enviarMensaje(mensaje) {
    const chatContainer = document.querySelector('#chatbot-section .chat-area');
    if (chatContainer) {
        chatContainer.innerHTML += `
            <div class="message bot">
                <div class="avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="bubble">
                    <strong>PsyAI</strong>
                    <span class="typing-indicator">
                        <span></span><span></span><span></span>
                    </span>
                </div>
            </div>
        `;
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    try {
        const res = await fetch("/api/chatbot/enviar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ mensaje: mensaje })
        });
        const data = await res.json();

        if (data.respuesta) {
            agregarMensajeBot(data.respuesta);
        } else {
            agregarMensajeBot("Disculpa, no pude procesar tu mensaje. ¿Podrías intentarlo de nuevo?");
        }
    } catch(err) {
        console.error("Error chatbot:", err);
        agregarMensajeBot("No hay conexión con el asistente en este momento. Intenta de nuevo más tarde. Si es una emergencia o hay riesgo inmediato, llama al 123.");
    }
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function obtenerClaveHistorial() {
    try {
        const res = await fetch('/api/session', {
            credentials: 'include',
            signal: AbortSignal.timeout(2500)
        });
        if (res.ok) {
            const data = await res.json();
            const usuario = data.usuario || {};
            const id = usuario.id || usuario.idUsuario || usuario.email;
            if (id) return `chatbotHistorial:${id}`;
        }
    } catch (err) {
        console.warn('No se pudo obtener usuario para historial del chat:', err);
    }

    return null;
}

async function cargarHistorialRemoto() {
    try {
        const res = await fetch('/api/chatbot/historial', {
            credentials: 'include',
            signal: AbortSignal.timeout(5000)
        });
        if (!res.ok) {
            console.warn('Respuesta no OK del servidor:', res.status);
            return null;
        }
        const data = await res.json();
        console.log('Respuesta API historial:', data);
        if (data.success && Array.isArray(data.historial)) {
            return data.historial;
        } else {
            console.warn('Respuesta de historial no válida:', data);
            return null;
        }
    } catch (err) {
        console.warn('No se pudo cargar historial remoto del chat:', err.message);
        return null;
    }
}

async function limpiarChat() {
    try {
        await fetch('/api/chatbot/historial', {
            method: 'DELETE',
            credentials: 'include'
        });
    } catch(err) {
        console.warn('No se pudo eliminar historial remoto:', err);
    }

    historialChat = [];
    if (chatStorageKey) {
        localStorage.removeItem(chatStorageKey);
    }
    mostrarSaludoInicial();
    if (typeof showAlert === 'function') {
        showAlert('success', 'La conversación se eliminó correctamente.', 'Chat eliminado');
    }
}

function configurarEliminarChat() {
    const btnClearChat = document.getElementById('btn-clear-chat');
    if (!btnClearChat) return;

    btnClearChat.addEventListener('click', async function() {
        const hayMensajes = historialChat.length > 0 || (chatStorageKey && localStorage.getItem(chatStorageKey));
        if (!hayMensajes) {
            if (typeof showAlert === 'function') {
                showAlert('info', 'No hay mensajes guardados para eliminar.', 'Chat vacío');
            }
            return;
        }

        await limpiarChat();
    });
}

function configurarFullscreen() {
    const btnFullscreen = document.getElementById('btn-fullscreen');
    const chatbotSection = document.getElementById('chatbot-section');
    
    if (!btnFullscreen || !chatbotSection) return;
    
    btnFullscreen.addEventListener('click', function() {
        isFullscreen = !isFullscreen;
        
        if (isFullscreen) {
            chatbotSection.classList.add('fullscreen-active');
            btnFullscreen.innerHTML = '<i class="fas fa-compress"></i>';
            btnFullscreen.setAttribute('title', 'Salir de pantalla completa');
        } else {
            chatbotSection.classList.remove('fullscreen-active');
            btnFullscreen.innerHTML = '<i class="fas fa-expand"></i>';
            btnFullscreen.setAttribute('title', 'Pantalla completa');
        }
    });
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && isFullscreen) {
            isFullscreen = false;
            chatbotSection.classList.remove('fullscreen-active');
            btnFullscreen.innerHTML = '<i class="fas fa-expand"></i>';
            btnFullscreen.setAttribute('title', 'Pantalla completa');
        }
    });
}
