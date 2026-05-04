let historialData = [];
let riskTerms = [];
let originalConfig = {};

document.addEventListener('DOMContentLoaded', function() {
    cargarEstadisticas();
    cargarConfig();
    cargarHistorial();
    configurarFormularioConfig();
    configurarFiltro();
    configurarExportarCSV();
    configurarAgregarPalabra();
    configurarLimpiarPalabras();
});

async function cargarConfig() {
    try {
        const res = await fetch('/api/admin/chatbot-config', {
            credentials: 'include'
        });
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
            document.getElementById('maxTokens').value = config.max_tokens || 420;
            
            originalConfig = {
                system_prompt: config.system_prompt || '',
                tone: config.tone || '',
                interaction_rules: config.interaction_rules || '',
                risk_terms: config.risk_terms || '[]',
                crisis_response: config.crisis_response || '',
                fallback_response: config.fallback_response || '',
                temperature: config.temperature || 0.55,
                top_p: config.top_p || 0.9,
                max_tokens: config.max_tokens || 420
            };
            
            actualizarSliderDisplays();
            
            if (config.fecha_actualizacion) {
                document.getElementById('fechaActualizacion').textContent = 'Última actualización: ' + config.fecha_actualizacion;
                document.getElementById('saveInfo').textContent = 'Última modificación: ' + config.fecha_actualizacion;
            }
        }
    } catch(e) {
        console.error('Error cargando configuración:', e);
    }
}

async function cargarEstadisticas() {
    try {
        const res = await fetch('/api/admin/chatbot-historial', {
            credentials: 'include'
        });
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
    document.getElementById('maxTokensValue').textContent = document.getElementById('maxTokens').value;
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
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const currentData = {
            system_prompt: document.getElementById('systemPrompt').value.trim(),
            tone: document.getElementById('tone').value.trim(),
            interaction_rules: document.getElementById('interactionRules').value.trim(),
            risk_terms: JSON.stringify(riskTerms),
            crisis_response: document.getElementById('crisisResponse').value.trim(),
            fallback_response: document.getElementById('fallbackResponse').value.trim(),
            temperature: parseFloat(document.getElementById('temperature').value),
            top_p: parseFloat(document.getElementById('topP').value),
            max_tokens: parseInt(document.getElementById('maxTokens').value)
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
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(currentData)
            });
            const result = await res.json();
            
            if (result.success) {
                PsyAIAlerts.success('Configuración Guardada', 'La configuración del chatbot se ha guardado correctamente.');
                notificarCambioConfigChatbot(currentData.max_tokens);
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
            PsyAIAlerts.error('Error', 'Error de conexión al guardar.');
        } finally {
            btn.innerHTML = btnText;
            btn.disabled = false;
        }
    });
}

function notificarCambioConfigChatbot(maxTokens) {
    const payload = {
        max_tokens: maxTokens,
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

async function cargarHistorial(filtroNivel = '') {
    const tbody = document.querySelector('#tablaHistorial tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4"><i class="fas fa-spinner fa-spin"></i> Cargando...</td></tr>';
    
    try {
        const url = filtroNivel 
            ? `/api/admin/chatbot-historial?nivel=${encodeURIComponent(filtroNivel)}`
            : '/api/admin/chatbot-historial';
        
        const res = await fetch(url, {
            credentials: 'include'
        });
        const data = await res.json();
        
        if (data.success && data.historial && data.historial.length > 0) {
            historialData = data.historial;
            tbody.innerHTML = data.historial.map((item, index) => {
                const nivelBadge = getNivelBadge(item.nivelEmocionalDetectado);
                const mensajeCorto = (item.mensajeUsuario || '').substring(0, 35) + ((item.mensajeUsuario || '').length > 35 ? '...' : '');
                const respuestaCorta = (item.respuestaChatbot || '').substring(0, 35) + ((item.respuestaChatbot || '').length > 35 ? '...' : '');
                
                return `
                    <tr>
                        <td class="fw-semibold">${escapeHtml(item.nombre || 'Paciente')}</td>
                        <td><small>${escapeHtml(mensajeCorto)}</small></td>
                        <td><small>${escapeHtml(respuestaCorta)}</small></td>
                        <td>${nivelBadge}</td>
                        <td><small class="text-muted">${formatFecha(item.fecha)}</small></td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary" onclick="verDetalle(${index})" title="Ver detalle">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        } else {
            historialData = [];
            tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No hay conversaciones registradas</td></tr>';
        }
    } catch(e) {
        console.error('Error cargando historial:', e);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Error al cargar el historial</td></tr>';
    }
}

function getNivelBadge(nivel) {
    if (nivel === 'Alto') {
        return '<span class="badge bg-danger">Alto</span>';
    } else if (nivel === 'Medio') {
        return '<span class="badge bg-warning text-dark">Medio</span>';
    } else if (nivel === 'Bajo') {
        return '<span class="badge bg-success">Bajo</span>';
    }
    return '<span class="badge bg-secondary">-</span>';
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

function configurarFiltro() {
    const filtro = document.getElementById('filtroNivel');
    const btnActualizar = document.getElementById('btnActualizarHistorial');
    
    if (filtro) {
        filtro.addEventListener('change', function() {
            cargarHistorial(this.value);
        });
    }
    
    if (btnActualizar) {
        btnActualizar.addEventListener('click', function() {
            const nivel = filtro ? filtro.value : '';
            cargarHistorial(nivel);
            cargarEstadisticas();
        });
    }
}

function verDetalle(index) {
    const item = historialData[index];
    if (!item) return;
    
    document.getElementById('detallePaciente').textContent = item.nombre || 'Paciente';
    document.getElementById('detalleNivel').innerHTML = getNivelBadge(item.nivelEmocionalDetectado);
    document.getElementById('detalleFecha').textContent = formatFecha(item.fecha);
    document.getElementById('detalleMensaje').textContent = item.mensajeUsuario || '-';
    document.getElementById('detalleRespuesta').textContent = item.respuestaChatbot || '-';
    
    document.getElementById('chatContainer').innerHTML = `
        <div class="chat-bubble-custom user-custom">
            <div class="chat-label-custom">Paciente</div>
            <div>${escapeHtml(item.mensajeUsuario || '-')}</div>
        </div>
        <div class="chat-bubble-custom bot-custom">
            <div class="chat-label-custom">PsyAI</div>
            <div>${escapeHtml(item.respuestaChatbot || '-')}</div>
        </div>
    `;
    
    const modal = new bootstrap.Modal(document.getElementById('modalDetalleConversacion'));
    modal.show();
}

function configurarExportarCSV() {
    const btn = document.getElementById('btnExportarCSV');
    if (!btn) return;
    
    btn.addEventListener('click', function() {
        if (historialData.length === 0) {
            PsyAIAlerts.warning('Sin datos', 'No hay datos para exportar.');
            return;
        }
        
        const headers = ['Paciente', 'Mensaje', 'Respuesta', 'Nivel Emocional', 'Fecha'];
        const rows = historialData.map(item => [
            item.nombre || 'Paciente',
            (item.mensajeUsuario || '').replace(/"/g, '""'),
            (item.respuestaChatbot || '').replace(/"/g, '""'),
            item.nivelEmocionalDetectado || '-',
            formatFecha(item.fecha)
        ]);
        
        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `historial_chatbot_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        PsyAIAlerts.success('Exportado', 'El historial se ha exportado correctamente a CSV.');
    });
}

window.verDetalle = verDetalle;

function renderizarRiskTerms() {
    const container = document.getElementById('riskTermsContainer');
    if (!container) return;

    const isDark = document.documentElement.classList.contains('dark-mode');

    const estilos = {
        'Alto': {
            icono: 'fa-exclamation-triangle',
            color: isDark ? '#f87171' : '#dc3545',
            bg: isDark ? 'rgba(220, 53, 69, 0.15)' : '#fef2f2',
            border: isDark ? '#f87171' : '#dc3545',
            badge: isDark ? '#dc3545' : '#dc3545'
        },
        'Medio': {
            icono: 'fa-exclamation-circle',
            color: isDark ? '#fbbf24' : '#f59e0b',
            bg: isDark ? 'rgba(245, 158, 11, 0.15)' : '#fffbeb',
            border: isDark ? '#fbbf24' : '#f59e0b',
            badge: isDark ? '#f59e0b' : '#f59e0b'
        },
        'Bajo': {
            icono: 'fa-check-circle',
            color: isDark ? '#34d399' : '#10b981',
            bg: isDark ? 'rgba(16, 185, 129, 0.15)' : '#ecfdf5',
            border: isDark ? '#34d399' : '#10b981',
            badge: isDark ? '#10b981' : '#10b981'
        }
    };

    container.innerHTML = riskTerms.length === 0
        ? '<span class="text-muted small">No hay palabras configuradas</span>'
        : riskTerms.map((item, index) => {
            const estilo = estilos[item.nivel] || { icono: 'fa-circle', color: '#9ca3af', bg: '#374151', border: '#4b5563', badge: '#6b7280' };
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
                    box-shadow: ${isDark ? '0 2px 8px rgba(0,0,0,0.3)' : '0 1px 3px rgba(0,0,0,0.1)'};
                ">
                    <i class="fas ${estilo.icono}" style="font-size: 0.9rem;"></i>
                    <span style="color: ${isDark ? '#e5e7eb' : '#1f2937'};">${escapeHtml(item.palabra)}</span>
                    <span style="
                        font-size: 0.7rem;
                        padding: 2px 8px;
                        border-radius: 12px;
                        background: ${estilo.badge};
                        color: white;
                        font-weight: 600;
                    ">${item.nivel}</span>
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
}

function agregarPalabra() {
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
    PsyAIAlerts.success('Agregada', `Palabra "${palabra}" agregada como ${nivel}.`);
}

function eliminarPalabra(index) {
    const palabraEliminada = riskTerms[index].palabra;
    riskTerms.splice(index, 1);
    renderizarRiskTerms();
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
                const res = await fetch('/api/admin/chatbot-config/clear-risk-terms', {
                    method: 'DELETE',
                    credentials: 'include'
                });
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
                PsyAIAlerts.error('Error', 'Error de conexión.');
            }
        });
    }
}

window.agregarPalabra = agregarPalabra;
window.eliminarPalabra = eliminarPalabra;
