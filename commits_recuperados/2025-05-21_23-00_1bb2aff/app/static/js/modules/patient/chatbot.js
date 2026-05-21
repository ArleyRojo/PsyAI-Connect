// ============================================================
// js/aside-patient/chatbot.js — Chatbot Emocional
// ============================================================

let historialChat = [];
const MAX_MENSAJES = 50;
let chatStorageKey = null;
let isFullscreen = false;
let chatbotConfigEventSource = null;

function obtenerFechaChatActual() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

document.addEventListener('DOMContentLoaded', async function () {
    await cargarConfiguracionChatbot();
    await inicializarChat();
    configurarFormulario();
    actualizarMensajesRestantes();
    configurarActualizacionConfigChatbot();
    configurarSelectorEmojis();
    configurarEliminarChat();
    configurarFullscreen();
});

// ── Config chatbot ─────────────────────────────────────────

async function cargarConfiguracionChatbot() {
    try {
        const res = await fetch('/api/chatbot/config', {
            credentials: 'include',
            signal: AbortSignal.timeout(3000)
        });
        if (!res.ok) return;
        await res.json();
    } catch (err) {
        console.warn('No se pudo cargar configuración del chatbot:', err.message);
    }
}

function aplicarMaxMensajesDesdeStorage() {}
function aplicarMaxMensajes(value) {}

// ── Inicialización del chat ────────────────────────────────

async function inicializarChat() {
    const chatContainer = document.querySelector('#chatbot-section .chat-area');
    if (!chatContainer) return;

    chatStorageKey = await obtenerClaveHistorial();

    const historialRemoto = await cargarHistorialRemoto();
    if (Array.isArray(historialRemoto) && historialRemoto.length > 0) {
        historialChat = historialRemoto;
        guardarHistorial();
        renderizarMensajes();
        actualizarMensajesRestantes();
        return;
    }

    const stored = chatStorageKey ? localStorage.getItem(chatStorageKey) : null;
    if (stored && chatStorageKey) {
        try {
            historialChat = obtenerHistorialLocalDelDia(stored);
            if (historialChat.length > 0) {
                renderizarMensajes();
                actualizarMensajesRestantes();
                return;
            }
        } catch (e) {
            console.error('Error parsing chat history:', e);
        }
    }

    mostrarSaludoInicial();
}

function mostrarSaludoInicial() {
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
                <div class="avatar"><i class="fas fa-robot"></i></div>
                <div class="bubble">
                    <strong>PsyAI</strong>
                    ${escapeHtml(m.mensaje)}
                </div>
            </div>`;
        }
    }).join('');

    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// ── Formulario ─────────────────────────────────────────────

function configurarFormulario() {
    const form = document.querySelector('#chatbot-section form');
    if (!form) return;

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const input = form.querySelector('input[name="mensaje"]');
        const mensaje = input.value.trim();
        if (!mensaje) return;
        agregarMensajeUsuario(mensaje);
        input.value = '';
        await enviarMensaje(mensaje);
    });
}

// ── Actualización de config en tiempo real ─────────────────

function configurarActualizacionConfigChatbot() {
    window.addEventListener('focus', cargarConfiguracionChatbot);
    window.addEventListener('storage', function (e) {
        if (e.key === 'chatbotConfigMaxTokens') aplicarMaxMensajes(e.newValue);
    });

    try {
        const channel = new BroadcastChannel('chatbot-config');
        channel.addEventListener('message', function (e) {
            aplicarMaxMensajes(e.data?.max_tokens);
        });
    } catch (e) {}

    configurarEventosConfigChatbot();

    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) cargarConfiguracionChatbot();
    });
}

function configurarEventosConfigChatbot() {
    if (!window.EventSource || chatbotConfigEventSource) return;
    chatbotConfigEventSource = new EventSource('/api/chatbot/config/events');
    chatbotConfigEventSource.addEventListener('chatbot-config', function (event) {
        try {
            const data = JSON.parse(event.data);
            aplicarMaxMensajes(data.max_tokens);
        } catch (e) {
            console.warn('No se pudo leer actualización de configuración:', e);
        }
    });
}

function actualizarMensajesRestantes() {
    const messageCount = document.getElementById('message-count');
    if (!messageCount) return;
    messageCount.textContent = '';
    messageCount.classList.remove('text-danger', 'fw-semibold');
    messageCount.hidden = true;
}

// ── Selector de emojis ─────────────────────────────────────

function configurarSelectorEmojis() {
    const btnEmoji = document.getElementById('btn-emoji-picker');
    const picker = document.getElementById('emoji-picker');
    const input = document.querySelector('#chatbot-section input[name="mensaje"]');

    if (!btnEmoji || !picker || !input) return;

    btnEmoji.addEventListener('click', function (e) {
        e.stopPropagation();
        const isOpen = picker.classList.toggle('active');
        btnEmoji.classList.toggle('active', isOpen);
        btnEmoji.setAttribute('aria-expanded', String(isOpen));
    });

    picker.querySelectorAll('button').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            insertarEmoji(input, btn.textContent);
            picker.classList.remove('active');
            btnEmoji.classList.remove('active');
            btnEmoji.setAttribute('aria-expanded', 'false');
        });
    });

    document.addEventListener('click', function (e) {
        if (picker.contains(e.target) || btnEmoji.contains(e.target)) return;
        picker.classList.remove('active');
        btnEmoji.classList.remove('active');
        btnEmoji.setAttribute('aria-expanded', 'false');
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            picker.classList.remove('active');
            btnEmoji.classList.remove('active');
            btnEmoji.setAttribute('aria-expanded', 'false');
        }
    });
}

// ── Helpers ────────────────────────────────────────────────

function insertarEmoji(input, emoji) {
    const start = input.selectionStart ?? input.value.length;
    const end = input.selectionEnd ?? input.value.length;
    input.value = input.value.slice(0, start) + emoji + input.value.slice(end);
    const cursor = start + emoji.length;
    input.focus();
    input.setSelectionRange(cursor, cursor);
}

function agregarMensajeUsuario(mensaje) {
    historialChat.push({ tipo: 'usuario', mensaje });
    guardarHistorial();
    renderizarMensajes();
}

function agregarMensajeBot(mensaje) {
    historialChat.push({ tipo: 'bot', mensaje });
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

// ── Envío de mensajes ──────────────────────────────────────

async function enviarMensaje(mensaje) {
    const chatContainer = document.querySelector('#chatbot-section .chat-area');
    if (chatContainer) {
        chatContainer.innerHTML += `
            <div class="message bot">
                <div class="avatar"><i class="fas fa-robot"></i></div>
                <div class="bubble">
                    <strong>PsyAI</strong>
                    <span class="typing-indicator">
                        <span></span><span></span><span></span>
                    </span>
                </div>
            </div>`;
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    try {
        const res = await fetch('/api/chatbot/enviar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ mensaje })
        });
        const data = await res.json();

        actualizarContadorDiario(data);

        if (!data.success && data.limit_reached) {
            agregarMensajeBot(data.message);
            bloquearFormularioPorLimiteDiario();
            return;
        }

        const botReply = data.respuesta || data.message || 'Disculpa, no pude procesar tu mensaje. Inténtalo de nuevo.';
        agregarMensajeBot(botReply);
    } catch (err) {
        console.error('Error chatbot:', err);
        agregarMensajeBot('No hay conexión con el asistente en este momento. Inténtalo de nuevo más tarde. Si es una emergencia o hay riesgo inmediato, llama al 123.');
    }
}

function actualizarContadorDiario(data) {
    if (data.used === undefined || data.limit === undefined) return;
    const counter = document.getElementById('msg-counter');
    if (!counter) return;
    const remaining = data.limit - data.used;
    counter.textContent = `Mensajes hoy: ${data.used} / ${data.limit}`;
    counter.className = remaining <= 3
        ? 'text-danger small me-3'
        : remaining <= 5
            ? 'text-warning small me-3'
            : 'text-muted small me-3';
}

function bloquearFormularioPorLimiteDiario() {
    const chatInput = document.querySelector('#chatbot-section input[name="mensaje"]');
    const submitButton = document.querySelector('#chatbot-section form button[type="submit"]');
    if (chatInput) {
        chatInput.disabled = true;
        chatInput.placeholder = 'Límite diario alcanzado. Vuelve mañana.';
    }
    if (submitButton) submitButton.disabled = true;
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ── Sesión e historial remoto ──────────────────────────────

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
        if (!res.ok) return null;
        const data = await res.json();
        if (data.success && Array.isArray(data.historial)) return data.historial;
        return null;
    } catch (err) {
        console.warn('No se pudo cargar historial remoto del chat:', err.message);
        return null;
    }
}

// ── Limpiar chat ───────────────────────────────────────────

async function limpiarChat() {
    try {
        await fetch('/api/chatbot/historial', {
            method: 'DELETE',
            credentials: 'include'
        });
    } catch (err) {
        console.warn('No se pudo eliminar historial remoto:', err);
    }
    historialChat = [];
    if (chatStorageKey) localStorage.removeItem(chatStorageKey);
    mostrarSaludoInicial();
    if (typeof showAlert === 'function') {
        showAlert('success', 'La conversación se eliminó correctamente.', 'Chat eliminado');
    }
}

function configurarEliminarChat() {
    const btnClearChat = document.getElementById('btn-clear-chat');
    if (!btnClearChat) return;
    btnClearChat.addEventListener('click', async function () {
        const hayMensajes = historialChat.length > 0 || (chatStorageKey && localStorage.getItem(chatStorageKey));
        if (!hayMensajes) {
            if (typeof showAlert === 'function') showAlert('info', 'No hay mensajes guardados para eliminar.', 'Chat vacío');
            return;
        }
        await limpiarChat();
    });
}

// ── Pantalla completa ──────────────────────────────────────

function configurarFullscreen() {
    const btnFullscreen = document.getElementById('btn-fullscreen');
    const chatbotSection = document.getElementById('chatbot-section');
    if (!btnFullscreen || !chatbotSection) return;

    btnFullscreen.addEventListener('click', function () {
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

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && isFullscreen) {
            isFullscreen = false;
            chatbotSection.classList.remove('fullscreen-active');
            btnFullscreen.innerHTML = '<i class="fas fa-expand"></i>';
            btnFullscreen.setAttribute('title', 'Pantalla completa');
        }
    });
}