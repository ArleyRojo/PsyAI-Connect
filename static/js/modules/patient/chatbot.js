// ============================================================
// js/aside-patient/chatbot.js — Chatbot Emocional (SaaS UI)
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

function formatearHora(fecha) {
    if (!fecha) return '';
    try {
        const d = new Date(fecha);
        if (isNaN(d.getTime())) return '';
        const h = d.getHours();
        const m = String(d.getMinutes()).padStart(2, '0');
        const ampm = h >= 12 ? 'PM' : 'AM';
        const h12 = h % 12 || 12;
        return `${h12}:${m} ${ampm}`;
    } catch (e) {
        return '';
    }
}

function ahoraTimestamp() {
    return new Date().toISOString();
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
    configurarFinalizarSesion();
    configurarWelcomeChips();
    configurarScrollToBottom();
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

// ── Welcome state ──────────────────────────────────────────

function mostrarWelcome() {
    const welcome = document.getElementById('chat-welcome');
    if (welcome) welcome.classList.remove('hidden');
}

function ocultarWelcome() {
    const welcome = document.getElementById('chat-welcome');
    if (welcome) welcome.classList.add('hidden');
}

function configurarWelcomeChips() {
    document.querySelectorAll('.chat-welcome__chip').forEach(function (chip) {
        chip.addEventListener('click', function () {
            const greeting = chip.getAttribute('data-greeting');
            if (!greeting) return;
            const input = document.querySelector('#chatbot-section input[name="mensaje"]');
            if (input) {
                input.value = greeting;
                input.focus();
            }
            ocultarWelcome();
        });
    });
}

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
    historialChat = [{
        tipo: 'bot',
        mensaje: 'Hola! Soy tu asistente emocional. Estoy aqui para escucharte y acompanarte. Como te sientes hoy?',
        timestamp: ahoraTimestamp()
    }];
    guardarHistorial();
    renderizarMensajes();
}

function renderizarMensajes() {
    const chatContainer = document.querySelector('#chatbot-section .chat-area');
    if (!chatContainer) return;

    if (historialChat.length === 0) {
        chatContainer.innerHTML = '';
        mostrarWelcome();
        return;
    }

    ocultarWelcome();

    let html = '';
    let lastSender = null;
    let lastDateKey = null;

    historialChat.forEach(function (m, idx) {
        const timeStr = formatearHora(m.timestamp);
        const timeHtml = timeStr ? '<div class="chat-msg-time">' + timeStr + '</div>' : '';
        const msgDate = m.timestamp ? new Date(m.timestamp) : null;
        const dateKey = msgDate ? msgDate.toISOString().slice(0, 10) : null;

        if (dateKey && dateKey !== lastDateKey) {
            const sepLabel = formatearFechaSeparador(msgDate);
            html += '<div class="chat-date-sep"><span>' + sepLabel + '</span></div>';
            lastSender = null;
            lastDateKey = dateKey;
        }

        const isGrouped = (m.tipo === lastSender);
        const groupedClass = isGrouped ? ' grouped' : '';

        if (m.tipo === 'usuario') {
            html += '<div class="message user' + groupedClass + '">' +
                '<div class="bubble">' +
                    '<strong>Tu</strong>' +
                    escapeHtml(m.mensaje) +
                    timeHtml +
                '</div>' +
            '</div>';
        } else {
            html += '<div class="message bot' + groupedClass + '">' +
                '<div class="avatar"><i class="fas fa-robot"></i></div>' +
                '<div class="bubble">' +
                    '<strong>PsyAI</strong>' +
                    escapeHtml(m.mensaje) +
                    timeHtml +
                '</div>' +
            '</div>';
        }

        lastSender = m.tipo;
    });

    chatContainer.innerHTML = html;
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function formatearFechaSeparador(date) {
    if (!date || isNaN(date.getTime())) return '';
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const msgDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const diffDays = Math.floor((today - msgDay) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Hoy';
    if (diffDays === 1) return 'Ayer';

    const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
    return date.getDate() + ' de ' + meses[date.getMonth()] + ' ' + date.getFullYear();
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
        ocultarWelcome();
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

async function configurarEventosConfigChatbot() {
    if (!window.EventSource || chatbotConfigEventSource) return;
    try {
        const check = await fetch('/api/chatbot/config', { credentials: 'include' });
        if (!check.ok) return;
    } catch (e) {
        console.warn('SSE config no disponible:', e);
        return;
    }
    chatbotConfigEventSource = new EventSource('/api/chatbot/config/events');
    chatbotConfigEventSource.addEventListener('chatbot-config', function (event) {
        try {
            const data = JSON.parse(event.data);
            aplicarMaxMensajes(data.max_tokens);
        } catch (e) {
            console.warn('No se pudo leer actualización de configuración:', e);
        }
    });
    chatbotConfigEventSource.addEventListener('auth-error', function () {
        chatbotConfigEventSource.close();
        chatbotConfigEventSource = null;
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
        var isOpen = picker.classList.toggle('active');
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
    var start = input.selectionStart ?? input.value.length;
    var end = input.selectionEnd ?? input.value.length;
    input.value = input.value.slice(0, start) + emoji + input.value.slice(end);
    var cursor = start + emoji.length;
    input.focus();
    input.setSelectionRange(cursor, cursor);
}

function agregarMensajeUsuario(mensaje) {
    historialChat.push({ tipo: 'usuario', mensaje: mensaje, timestamp: ahoraTimestamp() });
    guardarHistorial();
    renderizarMensajes();
}

function agregarMensajeBot(mensaje) {
    historialChat.push({ tipo: 'bot', mensaje: mensaje, timestamp: ahoraTimestamp() });
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
    var parsed = JSON.parse(stored);
    var fechaActual = obtenerFechaChatActual();
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
    var chatContainer = document.querySelector('#chatbot-section .chat-area');
    if (chatContainer) {
        chatContainer.insertAdjacentHTML('beforeend',
            '<div class="message bot typing-msg">' +
                '<div class="avatar"><i class="fas fa-robot"></i></div>' +
                '<div class="bubble"><div class="typing-indicator__dots"><span></span><span></span><span></span></div></div>' +
            '</div>'
        );
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Guardar mensaje para posible reintento
    window.__lastChatbotMessage = mensaje;

    try {
        // Usar fetchConTimeout del módulo de conexión (timeout 8s para chatbot)
        var res = await (window.PsyAIConnection?.fetchConTimeout
            ? window.PsyAIConnection.fetchConTimeout('/api/chatbot/enviar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ mensaje: mensaje })
              }, 8000)
            : fetch('/api/chatbot/enviar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ mensaje: mensaje })
              })
        );
        var data = await res.json();

        var typingMessage = chatContainer && chatContainer.querySelector('.typing-msg');
        if (typingMessage) typingMessage.remove();

        actualizarContadorDiario(data);

        if (!data.success && data.limit_reached) {
            agregarMensajeBot(data.message);
            bloquearFormularioPorLimiteDiario();
            return;
        }

        var botReply = data.respuesta || data.message || 'Disculpa, no pude procesar tu mensaje. Intentalo de nuevo.';
        agregarMensajeBot(botReply);
        // Limpiar mensaje guardado al éxito
        window.__lastChatbotMessage = null;
    } catch (err) {
        var typingMessage = chatContainer && chatContainer.querySelector('.typing-msg');
        if (typingMessage) typingMessage.remove();
        console.error('Error chatbot:', err);

        // Usar nuevo componente de error de chatbot con botón Reintentar
        if (window.PsyAIConnection?.showChatbotError) {
          window.PsyAIConnection.showChatbotError(mensaje, function(retryMsg) {
            // Reintentar con el mismo mensaje
            enviarMensaje(retryMsg);
          });
        } else {
          // Fallback al comportamiento original
          agregarMensajeBot('No hay conexion con el asistente en este momento. Intentalo de nuevo mas tarde. Si es una emergencia o hay riesgo inmediato, llama al 123.');
        }
    }
}

function actualizarContadorDiario(data) {
    if (data.used === undefined || data.limit === undefined) return;
    var counter = document.getElementById('msg-counter');
    if (!counter) return;
    var remaining = data.limit - data.used;
    counter.textContent = data.used + ' / ' + data.limit + ' mensajes hoy';
    counter.className = remaining <= 3
        ? 'chat-header__counter chat-header__counter--danger'
        : remaining <= 5
            ? 'chat-header__counter chat-header__counter--warning'
            : 'chat-header__counter';
}

function bloquearFormularioPorLimiteDiario() {
    var chatInput = document.querySelector('#chatbot-section input[name="mensaje"]');
    var submitButton = document.querySelector('#chatbot-section .chat-send-btn');
    if (chatInput) {
        chatInput.disabled = true;
        chatInput.placeholder = 'Limite diario alcanzado. Vuelve manana.';
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
        var res = await fetch('/api/session', {
            credentials: 'include',
            signal: AbortSignal.timeout(2500)
        });
        if (res.ok) {
            var data = await res.json();
            var usuario = data.usuario || {};
            var id = usuario.id || usuario.idUsuario || usuario.email;
            if (id) return 'chatbotHistorial:' + id;
        }
    } catch (err) {
        console.warn('No se pudo obtener usuario para historial del chat:', err);
    }
    return null;
}

async function cargarHistorialRemoto() {
    try {
        var res = await fetch('/api/chatbot/historial', {
            credentials: 'include',
            signal: AbortSignal.timeout(5000)
        });
        if (!res.ok) return null;
        var data = await res.json();
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
        showAlert('success', 'La conversacion se elimino correctamente.', 'Chat eliminado');
    }
}

function configurarEliminarChat() {
    var btnClearChat = document.getElementById('btn-clear-chat');
    if (!btnClearChat) return;
    btnClearChat.addEventListener('click', async function () {
        var hayMensajes = historialChat.length > 0 || (chatStorageKey && localStorage.getItem(chatStorageKey));
        if (!hayMensajes) {
            if (typeof showAlert === 'function') showAlert('info', 'No hay mensajes guardados para eliminar.', 'Chat vacio');
            return;
        }
        await limpiarChat();
    });
}

function configurarFinalizarSesion() {
    var btn = document.getElementById('btn-finalizar-sesion');
    if (!btn) return;
    btn.addEventListener('click', async function () {
        if (historialChat.length === 0) {
            if (typeof showAlert === 'function') showAlert('info', 'Todavía no hay conversación para analizar.', 'Sesión vacía');
            return;
        }
        btn.disabled = true;
        try {
            // La ruta del router de DRF termina en "/"; sin la barra cae en serve_pages y devuelve HTML.
            var res = await fetch('/api/chatbot/prediagnostico/', {
                method: 'POST',
                credentials: 'include'
            });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) {
                if (typeof showAlert === 'function') showAlert('warning', data.message || 'No se pudo generar el resumen.', 'Aviso');
                return;
            }
            document.getElementById('prediagnostico-resumen').textContent = data.resumen;
            var lista = document.getElementById('prediagnostico-recomendaciones');
            lista.innerHTML = '';
            (data.recomendaciones || []).forEach(function (r) {
                var li = document.createElement('li');
                li.textContent = r;
                lista.appendChild(li);
            });
            new bootstrap.Modal(document.getElementById('prediagnosticoModal')).show();
        } catch (err) {
            console.error('Error generando prediagnostico:', err);
            if (typeof showAlert === 'function') showAlert('danger', 'No se pudo conectar con el servidor.', 'Error');
        } finally {
            btn.disabled = false;
        }
    });
}

// ── Pantalla completa ──────────────────────────────────────

function configurarFullscreen() {
    var btnFullscreen = document.getElementById('btn-fullscreen');
    var chatbotSection = document.getElementById('chatbot-section');
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

// ── Scroll to bottom button ──────────────────────────────

function configurarScrollToBottom() {
    var chatContainer = document.querySelector('#chatbot-section .chat-area');
    var scrollBtn = document.getElementById('chat-scroll-btn');
    if (!chatContainer || !scrollBtn) return;

    chatContainer.addEventListener('scroll', function () {
        var distanceFromBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight;
        if (distanceFromBottom > 120) {
            scrollBtn.classList.add('visible');
        } else {
            scrollBtn.classList.remove('visible');
        }
    });

    scrollBtn.addEventListener('click', function () {
        chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
        scrollBtn.classList.remove('visible');
    });
}