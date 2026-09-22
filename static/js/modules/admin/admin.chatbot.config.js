let pacientesData = [];
let pacientesFiltrados = [];
let riskTerms = [];
let palabrasDetectadas = [];
let originalConfig = {};
let pacienteSeleccionado = null;
let riskFilterActual = 'all';
let configCargada = false;

document.addEventListener('DOMContentLoaded', function() {
    const btnGuardar = document.getElementById('btnGuardar');
    if (btnGuardar) btnGuardar.disabled = true;
    cargarEstadisticas();
    cargarConfig();
    cargarPalabrasDetectadas();
    cargarHistorial();
    configurarFormularioConfig();
    configurarFiltrosHistorial();
    configurarFiltroRiesgo();
    configurarAgregarPalabra();
    configurarLimpiarPalabras();
});

async function cargarPalabrasDetectadas() {
    try {
        const res = await fetch('/api/admin/chatbot-config/palabras-detectadas', {
            credentials: 'include'
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.success) {
            palabrasDetectadas = data.palabras || [];
        }
    } catch(e) {
        console.error('Error cargando palabras detectadas:', e);
    }
    renderizarRiskLevelCards();
}

async function cargarConfig() {
    try {
        const res = await fetch('/api/admin/chatbot-config', {
            credentials: 'include'
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        if (data.success && data.config) {
            const config = data.config;
            
            document.getElementById('systemPrompt').value = config.system_prompt || '';
            document.getElementById('tone').value = config.tone || '';
            document.getElementById('interactionRules').value = config.interaction_rules || '';
            try {
                riskTerms = JSON.parse(config.risk_terms || '[]');
            } catch(e) {
                riskTerms = [];
            }
            renderizarRiskTerms();
            document.getElementById('crisisResponse').value = config.crisis_response || '';
            document.getElementById('fallbackResponse').value = config.fallback_response || '';
            document.getElementById('temperature').value = config.temperature || 0.55;
            document.getElementById('topP').value = config.top_p || 0.9;
            document.getElementById('maxTokens').value = config.max_tokens || 600;
            document.getElementById('maxTokensUser').value = config.max_tokens_user || 1000;
            document.getElementById('dailyMessageLimit').value = config.daily_message_limit || 20;
            
            originalConfig = {
                system_prompt: config.system_prompt || '',
                tone: config.tone || '',
                interaction_rules: config.interaction_rules || '',
                risk_terms: config.risk_terms || '[]',
                crisis_response: config.crisis_response || '',
                fallback_response: config.fallback_response || '',
                temperature: config.temperature || 0.55,
                top_p: config.top_p || 0.9,
                max_tokens: config.max_tokens || 600,
                max_tokens_user: config.max_tokens_user || 1000,
                daily_message_limit: config.daily_message_limit || 20
            };
            
            actualizarSliderDisplays();
            
            if (config.fecha_actualizacion) {
                document.getElementById('fechaActualizacion').textContent = 'Última actualización: ' + config.fecha_actualizacion;
                document.getElementById('saveInfo').textContent = 'Última modificación: ' + config.fecha_actualizacion;
            }
            configCargada = true;
            const btnGuardar = document.getElementById('btnGuardar');
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = 'Guardar Configuraci&oacute;n';
            }
        }
    } catch(e) {
        console.error('Error cargando configuración:', e);
        PsyAIAlerts.error('Error de carga', 'No se pudo cargar la configuraci&oacute;n. Recarga la p&aacute;gina antes de guardar.');
        const btnGuardar = document.getElementById('btnGuardar');
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Recarga la p&aacute;gina';
        }
    }
    renderizarRiskLevelCards();
}

async function cargarEstadisticas() {
    try {
        const res = await fetch('/api/admin/chatbot-historial', {
            credentials: 'include'
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        if (data.success && data.stats) {
            const total = data.stats.total || 0;
            const alto = data.stats.alto || 0;
            const medio = data.stats.medio || 0;
            const bajo = data.stats.bajo || 0;
            
            document.getElementById('statTotal').textContent = total;
            document.getElementById('statAlto').textContent = alto;
            document.getElementById('statMedio').textContent = medio;
            document.getElementById('statBajo').textContent = bajo;
            
            document.getElementById('progressTotal').style.width = '100%';
            document.getElementById('progressAlto').style.width = total > 0 ? ((alto / total) * 100) + '%' : '0%';
            document.getElementById('progressMedio').style.width = total > 0 ? ((medio / total) * 100) + '%' : '0%';
            document.getElementById('progressBajo').style.width = total > 0 ? ((bajo / total) * 100) + '%' : '0%';
        }
    } catch(e) {
        console.error('Error cargando estadísticas:', e);
    }
}

function actualizarSliderDisplays() {
    document.getElementById('tempValue').textContent = parseFloat(document.getElementById('temperature').value).toFixed(2);
    document.getElementById('topPValue').textContent = parseFloat(document.getElementById('topP').value).toFixed(2);
    const maxTokens = document.getElementById('maxTokens');
    const maxTokensUser = document.getElementById('maxTokensUser');
    maxTokens.max = '1000';
    maxTokensUser.max = '1000';
    document.getElementById('maxTokensValue').textContent = maxTokens.value;
    document.getElementById('maxTokensUserValue').textContent = maxTokensUser.value;
}

function configurarFormularioConfig() {
    const form = document.getElementById('formConfigChatbot');
    const btn = document.getElementById('btnGuardar');
    
    document.getElementById('temperature').addEventListener('input', function() {
        document.getElementById('tempValue').textContent = parseFloat(this.value).toFixed(2);
    });
    
    document.getElementById('topP').addEventListener('input', function() {
        document.getElementById('topPValue').textContent = parseFloat(this.value).toFixed(2);
    });
    
    document.getElementById('maxTokens').addEventListener('input', function() {
        document.getElementById('maxTokensValue').textContent = this.value;
    });
    
    document.getElementById('maxTokensUser').addEventListener('input', function() {
        document.getElementById('maxTokensUserValue').textContent = this.value;
    });
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        if (!configCargada) {
            PsyAIAlerts.error('Configuraci&oacute;n no cargada', 'Espera a que la configuraci&oacute;n termine de cargar antes de guardar, o recarga la p&aacute;gina.');
            return;
        }

        const currentData = {
            system_prompt: document.getElementById('systemPrompt').value.trim(),
            tone: document.getElementById('tone').value.trim(),
            interaction_rules: document.getElementById('interactionRules').value.trim(),
            risk_terms: JSON.stringify(riskTerms),
            crisis_response: document.getElementById('crisisResponse').value.trim(),
            fallback_response: document.getElementById('fallbackResponse').value.trim(),
            temperature: parseFloat(document.getElementById('temperature').value),
            top_p: parseFloat(document.getElementById('topP').value),
            max_tokens: parseInt(document.getElementById('maxTokens').value),
            max_tokens_user: parseInt(document.getElementById('maxTokensUser').value),
            daily_message_limit: parseInt(document.getElementById('dailyMessageLimit').value)
        };
        
        const hayCambios = Object.keys(currentData).some(key => {
            if (key === 'temperature' || key === 'top_p') {
                return Math.abs(currentData[key] - originalConfig[key]) > 0.001;
            }
            return currentData[key] !== originalConfig[key];
        });
        
        if (!hayCambios) {
            PsyAIAlerts.info('Sin cambios', 'No hay modificaciones para guardar.');
            return;
        }
        
        const btnText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
        btn.disabled = true;
        
        try {
            const res = await fetch('/api/admin/chatbot-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(currentData)
            });
            if (!res.ok) {
                const text = await res.text().catch(() => '');
                let msg;
                try { msg = JSON.parse(text).message; } catch(_) {}
                throw new Error(msg || `Error del servidor (${res.status})`);
            }
            const result = await res.json();
            
            if (result.success) {
                PsyAIAlerts.success('Configuración Guardada', 'La configuración del chatbot se ha guardado correctamente.');
                notificarCambioConfigChatbot(currentData.max_tokens, currentData.max_tokens_user, currentData.daily_message_limit);
                if (result.message) {
                    document.getElementById('saveInfo').textContent = 'Última modificación: ' + result.message;
                    document.getElementById('fechaActualizacion').textContent = 'Última actualización: ' + result.message;
                }
                originalConfig = { ...currentData };
            } else {
                PsyAIAlerts.error('Error', result.message || 'No se pudo guardar la configuración.');
            }
        } catch(e) {
            console.error('Error guardando configuración:', e);
            const isNetwork = e instanceof TypeError && e.message.includes('fetch');
            const msg = isNetwork
                ? 'Sin conexión a la red. Verifica tu conexión a internet.'
                : `Error al guardar: ${e.message}`;
            PsyAIAlerts.error('Error al guardar', msg);
        } finally {
            btn.innerHTML = btnText;
            btn.disabled = false;
        }
    });
}

function notificarCambioConfigChatbot(maxTokens, maxTokensUser, dailyMessageLimit) {
    const payload = {
        max_tokens: maxTokens,
        max_tokens_user: maxTokensUser,
        daily_message_limit: dailyMessageLimit,
        updated_at: Date.now()
    };

    try {
        localStorage.setItem('chatbotConfigMaxTokens', String(maxTokens));
        localStorage.setItem('chatbotConfigUpdatedAt', String(payload.updated_at));
    } catch(e) {}

    try {
        const channel = new BroadcastChannel('chatbot-config');
        channel.postMessage(payload);
        channel.close();
    } catch(e) {}
}

async function cargarHistorial() {
    const container = document.getElementById('patientsList');
    if (!container) return;
    container.innerHTML = '<div class="text-center text-muted py-5"><i class="fas fa-spinner fa-spin fa-2x mb-2 d-block"></i>Cargando...</div>';
    
    const nivel = document.getElementById('filtroNivel')?.value || '';
    const search = document.getElementById('buscarHistorial')?.value?.trim() || '';
    
    try {
        const params = new URLSearchParams();
        if (nivel) params.set('nivel', nivel);
        if (search) params.set('q', search);
        const qs = params.toString();
        const url = qs ? `/api/admin/chatbot-historial?${qs}` : '/api/admin/chatbot-historial';
        
        const res = await fetch(url, { credentials: 'include' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        if (data.success && data.pacientes) {
            pacientesData = data.pacientes;
            pacientesFiltrados = pacientesData;
        } else {
            pacientesData = [];
            pacientesFiltrados = [];
        }
        renderizarListaPacientes();
    } catch(e) {
        console.error('Error cargando historial:', e);
        container.innerHTML = '<div class="text-center text-muted py-5"><i class="fas fa-exclamation-triangle fa-2x mb-2 d-block"></i>Error al cargar</div>';
    }
}

function getNivelBadge(nivel) {
    if (nivel === 'Alto') {
        return '<span class="badge-riesgo badge-riesgo-alto"><i class="fas fa-exclamation-triangle"></i> Alto</span>';
    } else if (nivel === 'Medio') {
        return '<span class="badge-riesgo badge-riesgo-medio"><i class="fas fa-exclamation-circle"></i> Medio</span>';
    } else if (nivel === 'Bajo') {
        return '<span class="badge-riesgo badge-riesgo-bajo"><i class="fas fa-check-circle"></i> Bajo</span>';
    }
    return '<span class="badge-riesgo">-</span>';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFecha(fecha) {
    if (!fecha) return '-';
    try {
        const d = new Date(fecha);
        return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch(e) {
        return fecha;
    }
}

function configurarFiltrosHistorial() {
    const filtro = document.getElementById('filtroNivel');
    const buscar = document.getElementById('buscarHistorial');
    const btnActualizar = document.getElementById('btnActualizarHistorial');

    if (filtro) {
        filtro.addEventListener('change', function() {
            cargarHistorial();
        });
    }

    if (buscar) {
        let timer = null;
        buscar.addEventListener('input', function() {
            clearTimeout(timer);
            timer = setTimeout(cargarHistorial, 300);
        });
    }

    if (btnActualizar) {
        btnActualizar.addEventListener('click', function() {
            cargarHistorial();
            cargarEstadisticas();
        });
    }
}

function renderizarListaPacientes() {
    const container = document.getElementById('patientsList');
    if (!container) return;

    if (pacientesFiltrados.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-5"><i class="fas fa-inbox fa-2x mb-2 d-block"></i>No hay conversaciones</div>';
        return;
    }

    container.innerHTML = pacientesFiltrados.map(p => {
        const initials = p.nombre.split(' ').map(w => w[0]).filter(Boolean).join('').toUpperCase().substring(0, 2) || '?';
        const color = p.nivel_max === 'Alto' ? 'var(--mood-critical)' : p.nivel_max === 'Medio' ? 'var(--mood-neutral)' : 'var(--mood-excellent)';
        const active = pacienteSeleccionado && pacienteSeleccionado.nombre === p.nombre ? 'active' : '';
        const lastMsg = p.mensajes && p.mensajes.length > 0
            ? (p.mensajes[p.mensajes.length - 1].mensajeUsuario || '').substring(0, 50)
            : '';
        return `
            <div class="patient-card ${active}" onclick="seleccionarPaciente('${escapeHtml(p.nombre).replace(/'/g, "\\'")}')" style="border-left: 3px solid ${color};">
                <div class="patient-avatar" style="background:${color};">${initials}</div>
                <div class="patient-info">
                    <div class="patient-name">${escapeHtml(p.nombre)}</div>
                    <div class="patient-preview">${escapeHtml(lastMsg)}${lastMsg.length >= 50 ? '...' : ''}</div>
                </div>
                <div class="patient-meta">
                    <span class="patient-time">${formatFechaRelativa(p.ultimo_mensaje)}</span>
                    <span class="patient-count badge-riesgo ${p.nivel_max === 'Alto' ? 'badge-riesgo-alto' : p.nivel_max === 'Medio' ? 'badge-riesgo-medio' : 'badge-riesgo-bajo'}">${p.total_mensajes}</span>
                </div>
            </div>
        `;
    }).join('');
}

function seleccionarPaciente(nombre) {
    const paciente = pacientesFiltrados.find(p => p.nombre === nombre);
    if (!paciente) return;
    pacienteSeleccionado = paciente;

    renderizarListaPacientes();

    const header = document.getElementById('conversationHeader');
    const messages = document.getElementById('conversationMessages');
    const footer = document.getElementById('conversationFooter');

    const initials = paciente.nombre.split(' ').map(w => w[0]).filter(Boolean).join('').toUpperCase().substring(0, 2) || '?';
    const color = paciente.nivel_max === 'Alto' ? 'var(--mood-critical)' : paciente.nivel_max === 'Medio' ? 'var(--mood-neutral)' : 'var(--mood-excellent)';

    header.style.display = '';
    header.innerHTML = `
        <div class="d-flex align-items-center gap-3">
            <div class="patient-avatar" style="background:${color};width:38px;height:38px;font-size:.85rem;">${initials}</div>
            <div>
                <div class="fw-bold" style="color:var(--dm-heading);">${escapeHtml(paciente.nombre)}</div>
                <small class="text-muted">${paciente.total_mensajes} mensajes · ${getNivelBadge(paciente.nivel_max)}</small>
            </div>
        </div>
    `;

    messages.innerHTML = paciente.mensajes.map(m => {
        const necesidadNivel = m.nivelEmocionalDetectado && (m.nivelEmocionalDetectado === 'Alto' || m.nivelEmocionalDetectado === 'Medio');
        const nivelBadge = necesidadNivel
            ? `<div class="msg-level-badge">${getNivelBadge(m.nivelEmocionalDetectado)}</div>`
            : '';
        const nivelClass = necesidadNivel ? `msg-nivel-${m.nivelEmocionalDetectado.toLowerCase()}` : '';
        return `
            <div class="msg-pair ${nivelClass}">
                <div class="msg-row user">
                    <div class="msg-avatar user-avatar">${initials}</div>
                    <div>
                        <div class="msg-bubble user-bubble">${escapeHtml(m.mensajeUsuario || '')}</div>
                        <span class="msg-timestamp">${formatFechaRelativa(m.fecha)}</span>
                        ${nivelBadge}
                    </div>
                </div>
                <div class="msg-row bot">
                    <div class="msg-avatar bot-avatar"><i class="fas fa-robot" style="font-size:0.85rem"></i></div>
                    <div>
                        <div class="msg-bubble bot-bubble">${escapeHtml(m.respuestaChatbot || '')}</div>
                        <span class="msg-timestamp">${formatFechaRelativa(m.fecha)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    header.style.display = '';
    footer.style.display = '';

    setTimeout(() => { messages.scrollTop = messages.scrollHeight; }, 50);
}

function formatFechaRelativa(fecha) {
    if (!fecha) return '';
    try {
        const ahora = new Date();
        const d = new Date(fecha);
        const diffMs = ahora - d;
        const diffMin = Math.floor(diffMs / 60000);
        const diffHoras = Math.floor(diffMs / 3600000);
        const diffDias = Math.floor(diffMs / 86400000);
        if (diffMin < 1) return 'Ahora';
        if (diffMin < 60) return `hace ${diffMin} min`;
        if (diffHoras < 24) return `hace ${diffHoras}h`;
        if (diffDias === 1) return 'Ayer';
        if (diffDias < 7) return `hace ${diffDias} d\u00edas`;
        return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short' });
    } catch(e) {
        return fecha;
    }
}

function exportarConversacion(nombre) {
    const paciente = pacientesData.find(p => p.nombre === nombre);
    if (!paciente) {
        PsyAIAlerts.warning('Sin datos', 'No se encontró la conversación para exportar.');
        return;
    }
    const lines = [];
    lines.push('\u2550'.repeat(47));
    lines.push('  PsyAI Connect \u2014 Conversaci\u00f3n Completa');
    lines.push('\u2550'.repeat(47));
    lines.push('');
    lines.push(`Paciente: ${paciente.nombre}`);
    lines.push(`Nivel maximo: ${paciente.nivel_max}`);
    lines.push(`Total mensajes: ${paciente.total_mensajes}`);
    lines.push('');
    lines.push('\u2500'.repeat(47));
    lines.push('');
    paciente.mensajes.forEach(m => {
        lines.push(`[Paciente] ${m.mensajeUsuario || ''}`);
        lines.push('');
        lines.push(`[PsyAI]    ${m.respuestaChatbot || ''}`);
        lines.push(`          (${m.nivelEmocionalDetectado || '-'} \u2022 ${formatFecha(m.fecha)})`);
        lines.push('');
        lines.push('\u2500'.repeat(47));
        lines.push('');
    });
    lines.push(`  Generado por PsyAI Connect \u2022 ${new Date().toLocaleString('es-CO')}`);
    lines.push('\u2550'.repeat(47));
    const content = lines.join('\r\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `conversacion_${nombre.replace(/\s+/g,'_')}_${new Date().toISOString().split('T')[0]}.txt`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function exportarConversacionPaciente() {
    if (!pacienteSeleccionado) {
        PsyAIAlerts.warning('Sin selección', 'Selecciona un paciente primero.');
        return;
    }
    exportarConversacion(pacienteSeleccionado.nombre);
}

window.seleccionarPaciente = seleccionarPaciente;
window.exportarConversacion = exportarConversacion;
window.exportarConversacionPaciente = exportarConversacionPaciente;

function renderizarRiskTerms() {
    const container = document.getElementById('riskTermsContainer');
    if (!container) return;

    const estilos = {
        'Alto': {
            icono: 'fa-exclamation-triangle',
            color: 'var(--mood-critical)',
            bg: 'rgba(239,68,68,0.08)',
            border: 'rgba(239,68,68,0.25)',
            badgeBg: 'var(--mood-critical)'
        },
        'Medio': {
            icono: 'fa-exclamation-circle',
            color: 'var(--mood-neutral)',
            bg: 'rgba(245,183,0,0.08)',
            border: 'rgba(245,183,0,0.25)',
            badgeBg: 'var(--mood-neutral)'
        },
        'Bajo': {
            icono: 'fa-check-circle',
            color: 'var(--mood-excellent)',
            bg: 'rgba(34,197,94,0.08)',
            border: 'rgba(34,197,94,0.25)',
            badgeBg: 'var(--mood-excellent)'
        }
    };

    container.innerHTML = riskTerms.length === 0
        ? '<span class="text-muted small">No hay palabras configuradas</span>'
        : riskTerms.map((item, index) => {
            const estilo = estilos[item.nivel] || { icono: 'fa-circle', color: 'var(--dm-muted)', bg: 'var(--dm-elevated)', border: 'var(--dm-border)', badgeBg: 'var(--dm-muted)' };
            return `
                <div class="risk-term-badge" style="
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px 12px;
                    border-radius: 8px;
                    background: ${estilo.bg};
                    border: 1px solid ${estilo.border};
                    font-size: 0.875rem;
                    font-weight: 500;
                    color: ${estilo.color};
                    margin: 4px;
                    transition: all 0.2s ease;
                ">
                    <i class="fas ${estilo.icono}" style="font-size: 0.9rem;"></i>
                    <span>${escapeHtml(item.palabra)}</span>
                    <span class="badge-riesgo ${item.nivel === 'Alto' ? 'badge-riesgo-alto' : item.nivel === 'Medio' ? 'badge-riesgo-medio' : 'badge-riesgo-bajo'}" style="font-size:0.65rem; padding:2px 8px;">${item.nivel}</span>
                    <button type="button" 
                        onclick="eliminarPalabra(${index})" 
                        aria-label="Eliminar"
                        style="
                            background: none;
                            border: none;
                            color: ${estilo.color};
                            cursor: pointer;
                            padding: 2px 6px;
                            font-size: 1rem;
                            line-height: 1;
                            opacity: 0.7;
                            transition: opacity 0.2s;
                        "
                        onmouseover="this.style.opacity=1"
                        onmouseout="this.style.opacity=0.7"
                    >&times;</button>
                </div>
            `;
        }).join('');

    renderizarRiskLevelCards();
}

function renderizarRiskLevelCards() {
    const list = document.getElementById('riskFilteredList');
    if (!list) return;

    const hasWords = palabrasDetectadas.length > 0;
    if (!hasWords) {
        list.innerHTML = '<span class="text-muted small py-3 d-block text-center">No hay palabras detectadas. Cuando los pacientes usen palabras de riesgo en el chat, aparecer&aacute;n aqu&iacute;.</span>';
        return;
    }

    const filtered = riskFilterActual === 'all'
        ? palabrasDetectadas
        : palabrasDetectadas.filter(w => w.nivel === riskFilterActual);

    if (filtered.length === 0) {
        list.innerHTML = '<span class="text-muted small py-3 d-block text-center">Sin palabras en este nivel</span>';
        return;
    }

    list.innerHTML = filtered.map((w) => {
        const nivel = w.nivel || 'Bajo';
        return `<span class="risk-word-chip ${nivel.toLowerCase()} detected" title="Pacientes: ${(w.pacientes || []).join(', ')}">
            ${escapeHtml(w.palabra)}
            <span class="level-badge">${nivel}</span>
            <span class="usage-badge">${w.count} vez${w.count !== 1 ? 'es' : ''}</span>
        </span>`;
    }).join('');
}

function configurarFiltroRiesgo() {
    const tabs = document.querySelectorAll('.risk-filter-btn');
    tabs.forEach(btn => {
        btn.addEventListener('click', function() {
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            riskFilterActual = this.getAttribute('data-filter');
            renderizarRiskLevelCards();
        });
    });
}

async function guardarRiskTerms() {
    try {
        const res = await fetch('/api/admin/chatbot-config', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ risk_terms: JSON.stringify(riskTerms) })
        });
        if (!res.ok) {
            const text = await res.text().catch(() => '');
            let msg;
            try { msg = JSON.parse(text).message; } catch(_) {}
            throw new Error(msg || `Error del servidor (${res.status})`);
        }
        const data = await res.json();
        if (!data.success) {
            console.error('Error guardando palabras de riesgo:', data.message);
            PsyAIAlerts.error('Error al guardar', data.message || 'No se pudieron guardar las palabras de riesgo.');
        }
    } catch(e) {
        console.error('Error guardando palabras de riesgo:', e);
        const isNetwork = e instanceof TypeError && e.message.includes('fetch');
        const msg = isNetwork
            ? 'Sin conexión a la red. Verifica tu conexión a internet.'
            : `Error al guardar: ${e.message}`;
        PsyAIAlerts.error('Error al guardar', msg);
    }
}

async function agregarPalabra() {
    const input = document.getElementById('riskTermsInput');
    const select = document.getElementById('riskLevelSelect');
    const palabra = input.value.trim().toLowerCase();
    const nivel = select.value;

    if (!palabra) {
        PsyAIAlerts.warning('Campo vacío', 'Escribe una palabra para agregar.');
        return;
    }

    if (riskTerms.some(p => p.palabra.toLowerCase() === palabra)) {
        PsyAIAlerts.warning('Duplicado', 'Esta palabra ya existe.');
        return;
    }

    riskTerms.push({ palabra, nivel });
    input.value = '';
    renderizarRiskTerms();
    await guardarRiskTerms();
    PsyAIAlerts.success('Agregada', `Palabra "${palabra}" agregada como ${nivel}.`);
}

async function eliminarPalabra(index) {
    const palabraEliminada = riskTerms[index].palabra;
    riskTerms.splice(index, 1);
    renderizarRiskTerms();
    await guardarRiskTerms();
    PsyAIAlerts.info('Eliminada', `Palabra "${palabraEliminada}" removida.`);
}

function configurarAgregarPalabra() {
    const btnAgregar = document.getElementById('btnAgregarPalabra');
    const input = document.getElementById('riskTermsInput');
    const select = document.getElementById('riskLevelSelect');
    
    if (select) {
        const actualizarSelect = () => {
            select.setAttribute('data-selected', select.value);
        };
        select.addEventListener('change', actualizarSelect);
        actualizarSelect();
    }
    
    if (btnAgregar) {
        btnAgregar.addEventListener('click', agregarPalabra);
    }
    
    if (input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                agregarPalabra();
            }
        });
    }
}

async function configurarLimpiarPalabras() {
    const btnLimpiar = document.getElementById('btnLimpiarPalabras');
    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', async function() {
            if (!confirm('¿Estás seguro de eliminar todas las palabras de riesgo?')) return;
            
            try {
                const res = await fetch('/api/admin/chatbot-config', {
                    method: 'DELETE',
                    credentials: 'include'
                });
                if (!res.ok) {
                    const text = await res.text().catch(() => '');
                    let msg;
                    try { msg = JSON.parse(text).message; } catch(_) {}
                    throw new Error(msg || `Error del servidor (${res.status})`);
                }
                const result = await res.json();
                
                if (result.success) {
                    riskTerms = [];
                    renderizarRiskTerms();
                    PsyAIAlerts.success('Limpiado', 'Todas las palabras de riesgo han sido eliminadas.');
                } else {
                    PsyAIAlerts.error('Error', result.message || 'No se pudieron eliminar las palabras.');
                }
            } catch(e) {
                console.error('Error al limpiar:', e);
                const isNetwork = e instanceof TypeError && e.message.includes('fetch');
                const msg = isNetwork
                    ? 'Sin conexión a la red. Verifica tu conexión a internet.'
                    : `Error al eliminar: ${e.message}`;
                PsyAIAlerts.error('Error al eliminar', msg);
            }
        });
    }
}

window.agregarPalabra = agregarPalabra;
window.eliminarPalabra = eliminarPalabra;
