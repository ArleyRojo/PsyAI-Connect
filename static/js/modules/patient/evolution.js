// ============================================================
// js/aside-patient/evolution.js — Mi Evolución Paciente
// ============================================================

function getEnergiaColor(nivel) {
    if (nivel <= 3) return 'danger';
    if (nivel <= 5) return 'warning';
    if (nivel <= 7) return 'info';
    return 'success';
}

function getEstadoColor(estado) {
    const colores = {
        'feliz': 'success',
        'tranquilo': 'info',
        'estresado': 'warning',
        'ansioso': 'secondary',
        'triste': 'danger'
    };
    return colores[estado] || 'primary';
}

function getEnergiaBarra(nivel) {
    const color = getEnergiaColor(nivel);
    return `<div class="d-flex align-items-center gap-2">
        <div class="progress" style="height: 6px; width: 50px;">
            <div class="progress-bar bg-${color}" style="width: ${nivel * 10}%"></div>
        </div>
        <small class="text-muted">${nivel}</small>
    </div>`;
}

function getHistorialLocal() {
    const stored = localStorage.getItem('historialEvolucion');
    return stored ? JSON.parse(stored) : [];
}

function guardarHistorialLocal(historial) {
    localStorage.setItem('historialEvolucion', JSON.stringify(historial));
}

async function cargarHistorialRemoto() {
    try {
        const res = await fetch("/api/evolucion", {
            credentials: "include"
        });
        if (!res.ok) return;
        const data = await res.json();
        if (Array.isArray(data.historial)) {
            guardarHistorialLocal(data.historial);
        }
    } catch (err) {
        console.error('No se pudo cargar historial de evolución:', err);
    }
}

function renderizarHistorial() {
    const historial = getHistorialLocal();
    const tbody = document.getElementById("tablaHistorialEvolucion");
    if (!tbody) return;
    
    if (historial.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No hay registros aún</td></tr>';
        const estadoActual = document.getElementById("estadoActual");
        if (estadoActual) estadoActual.textContent = "Aún no has registrado tu evolución.";
        return;
    }

    const ultimo = historial[0];
    const estadoActual = document.getElementById("estadoActual");
    if (estadoActual) {
        estadoActual.textContent = `Tu último estado: ${ultimo.estadoEmocional} — Energía: ${ultimo.nivelEnergia}/10`;
    }

    tbody.innerHTML = historial.map(h => `
        <tr>
            <td>${h.fecha}</td>
            <td><span class="badge bg-${getEstadoColor(h.estadoEmocional)}">${h.estadoEmocional}</span></td>
            <td>${getEnergiaBarra(h.nivelEnergia)}</td>
            <td>${h.notasPersonales || '—'}</td>
        </tr>
    `).join('');
}

function guardarEvolucion() {
    const estadoEmocional = document.getElementById("estado_emocional").value;
    const nivelEnergia    = document.getElementById("nivel_energia").value;
    const notasPersonales = document.getElementById("notas_personales").value;

    if (!estadoEmocional || !nivelEnergia) {
        let camposFaltantes = [];
        if (!estadoEmocional) camposFaltantes.push('Estado Emocional');
        if (!nivelEnergia) camposFaltantes.push('Nivel de Energía');
        PsyAIAlerts.warning('Campos Requeridos', `Falta: ${camposFaltantes.join(', ')}`);
        return;
    }

    fetch("/api/evolucion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ estadoEmocional, nivelEnergia, notasPersonales })
    })
    .then(res => res.json())
    .then(data => {
        const historial = getHistorialLocal();
        const nuevaEvolucion = {
            fecha: new Date().toLocaleDateString(),
            fechaRaw: new Date().toISOString(),
            estadoEmocional: estadoEmocional,
            nivelEnergia: parseInt(nivelEnergia),
            notasPersonales: notasPersonales
        };
        historial.unshift(nuevaEvolucion);
        guardarHistorialLocal(historial);
        
        PsyAIAlerts.success('Guardado', 'Tu evolución se ha registrado correctamente.');
        
        document.getElementById("estado_emocional").value = "";
        document.getElementById("nivel_energia").value = "";
        document.getElementById("notas_personales").value = "";
        
        renderizarHistorial();
    })
    .catch(err => {
        console.error(err);
        PsyAIAlerts.error('Error', 'No se pudo guardar en la base de datos.');
    });
}

document.addEventListener('DOMContentLoaded', async function() {
    await cargarHistorialRemoto();
    renderizarHistorial();

    const btnGuardar = document.getElementById("btnGuardarEvolucion");
    if (btnGuardar) {
        btnGuardar.addEventListener('click', guardarEvolucion);
    }
});
