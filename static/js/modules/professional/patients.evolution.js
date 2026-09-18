var pacientesEvolucionData = window.pacientesEvolucionData || [];
var evolucionData = window.evolucionData || [];
var riesgoBajoPorPaciente = {};

function getRiesgoBajoCount(patientId) {
    if (!patientId) return 0;
    return Number(riesgoBajoPorPaciente[String(patientId)] || 0);
}

function renderRiesgoBajoBadge(patientId) {
    var count = getRiesgoBajoCount(patientId);
    if (!count) return '';
    return (
        ' <span class="riesgo-bajo-badge" title="Señales de riesgo bajo en chatbot (últimos 7 días)">' +
        '<span class="riesgo-bajo-dot"></span>' + count + '</span>'
    );
}

function actualizarResumenRiesgoBajo() {
    var card = document.querySelector('#pestana-evolucion .card');
    if (!card) return;

    var container = document.getElementById('riesgoBajoResumenEvolucion');
    if (!container) {
        container = document.createElement('div');
        container.id = 'riesgoBajoResumenEvolucion';
        container.className = 'riesgo-bajo-resumen mb-3';
        var row = card.querySelector('.row.mb-3');
        if (row) {
            card.insertBefore(container, row);
        } else {
            card.appendChild(container);
        }
    }

    var select = document.getElementById('selectPacienteEvolucion');
    var filtro = select?.value || '';
    var selectedId = filtro.startsWith('id:') ? filtro.slice(3) : '';
    var totalPacientes = Object.keys(riesgoBajoPorPaciente).length;
    var totalMensajes = Object.values(riesgoBajoPorPaciente).reduce(function (sum, n) {
        return sum + Number(n || 0);
    }, 0);

    if (!totalMensajes) {
        container.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    if (selectedId) {
        var count = getRiesgoBajoCount(selectedId);
        if (!count) {
            container.style.display = 'none';
            container.innerHTML = '';
            return;
        }
        container.style.display = '';
        container.innerHTML =
            '<span class="riesgo-bajo-dot"></span>' +
            '<span>Este paciente tuvo <strong>' + count + '</strong> mensaje(s) con señales de riesgo bajo en el chatbot durante los últimos 7 días.</span>';
        return;
    }

    container.style.display = '';
    container.innerHTML =
        '<span class="riesgo-bajo-dot"></span>' +
        '<span><strong>' + totalPacientes + '</strong> paciente(s) con señales de riesgo bajo en chatbot (últimos 7 días): ' +
        '<strong>' + totalMensajes + '</strong> mensaje(s) en total.</span>';
}

function escapeHtmlEvolucion(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function normalizarTextoEvolucion(value) {
    return String(value ?? '')
        .trim()
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
}

async function cargarPacientesSelectEvolucion(historial) {
    var select = document.getElementById("selectPacienteEvolucion");
    if (!select) return;

    var currentValue = select.value;
    var opciones = new Map();

    // First try to fetch the patients assigned to this professional
    try {
        var resProfesional = await fetch("/api/profesional/pacientes", { credentials: "include" });
        if (resProfesional.ok) {
            var dataProfesional = await resProfesional.json();
            pacientesEvolucionData = dataProfesional.success ? (dataProfesional.pacientes || []) : [];
        } else {
            pacientesEvolucionData = [];
        }
    } catch (e) {
        console.error("Error cargando pacientes para evolucion:", e);
        pacientesEvolucionData = [];
    }

    // Add patients from the professional's patient list
    pacientesEvolucionData.forEach(function (p) {
        var nombre = p.nombre || p.paciente;
        var id = p.idPaciente || p.idUsuario;
        if (!nombre) return;
        var value = id ? 'id:' + id : 'name:' + normalizarTextoEvolucion(nombre);
        opciones.set(value, { value: value, label: nombre });
    });

    // Add patients from the existing history (in case they are not in the patient list)
    (historial || window.evolucionData || []).forEach(function (h) {
        var nombre = h.paciente || h.nombre;
        var id = h.idPaciente || h.idUsuario;
        if (!nombre) return;
        var value = id ? 'id:' + id : 'name:' + normalizarTextoEvolucion(nombre);
        opciones.set(value, { value: value, label: nombre });
    });

    var ordered = Array.from(opciones.values()).sort(function (a, b) {
        return a.label.localeCompare(b.label, 'es');
    });

    select.innerHTML = '<option value="">Todos los pacientes</option>' +
        ordered.map(function (option) {
            var patientId = option.value.startsWith('id:') ? option.value.slice(3) : '';
            var count = getRiesgoBajoCount(patientId);
            var suffix = count ? ' (' + count + ' riesgo bajo)' : '';
            return '<option value="' + escapeHtmlEvolucion(option.value) + '">' +
                escapeHtmlEvolucion(option.label + suffix) + '</option>';
        }).join('');

    // Restore selected value if it still exists
    if (Array.from(select.options).some(function (option) { return option.value === currentValue; })) {
        select.value = currentValue;
    }
}

async function cargarEvolucion() {
    var tbody = document.getElementById("tablaEvolucion");
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3"><i class="fas fa-spinner fa-spin me-2"></i>Cargando...</td></tr>';

    try {
        var res = await fetch("/api/evolucion/profesional", { credentials: "include" });
        var data = await res.json();
        
        window.evolucionData = evolucionData = (data.success && data.historial ? data.historial : []).sort(function (a, b) {
            return new Date(b.fechaRaw || b.fecha || 0) - new Date(a.fechaRaw || a.fecha || 0);
        });
        riesgoBajoPorPaciente = data.riesgo_bajo_chatbot || {};

        await cargarPacientesSelectEvolucion(evolucionData);
        actualizarBadgeEvolucion();
        actualizarResumenRiesgoBajo();
        filtrarEvolucionPorPaciente(); // Re-apply filter and render
    } catch (e) {
        console.error(e);
        evolucionData = [];
        riesgoBajoPorPaciente = {};
        await cargarPacientesSelectEvolucion([]);
        actualizarBadgeEvolucion();
        actualizarResumenRiesgoBajo();
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error al cargar la evolución</td></tr>';
    }
}

function filtrarEvolucionPorPaciente() {
    var select = document.getElementById("selectPacienteEvolucion");
    var filtro = select?.value || "";
    
    if (!filtro) {
        renderEvolucion(evolucionData);
        actualizarResumenRiesgoBajo();
        return;
    }

    var selectedOption = select?.selectedOptions?.[0];
    var selectedName = normalizarTextoEvolucion(selectedOption?.textContent || '');
    var selectedId = filtro.startsWith('id:') ? filtro.slice(3) : '';
    var selectedFilterName = filtro.startsWith('name:') ? filtro.slice(5) : '';

    var filteredData = evolucionData.filter(function (h) {
        var itemId = h.idPaciente || h.idUsuario || '';
        var itemName = normalizarTextoEvolucion(h.paciente || h.nombre || '');
        
        if (selectedId && String(itemId) === selectedId) return true;
        if (selectedFilterName && itemName === selectedFilterName) return true;
        if (selectedName && itemName === selectedName) return true;
        return false;
    });

    renderEvolucion(filteredData);
    actualizarResumenRiesgoBajo();
}

function renderEvolucion(lista) {
    var tbody = document.getElementById("tablaEvolucion");
    if (!tbody) return;

    if (!lista || !lista.length) {
        var filtro = document.getElementById("selectPacienteEvolucion")?.value || "";
        var mensaje = filtro ? 'Este paciente aun no tiene registros de evolucion' : 'No hay registros de evolucion';
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">' + mensaje + '</td></tr>';
        return;
    }

    tbody.innerHTML = lista.map(function (h) {
        var fecha = (typeof formatearFecha === 'function' ? formatearFecha(h.fechaRaw) : null) || h.fecha || "---";
        var colorEstado = (typeof getEstadoColor === 'function' ? getEstadoColor(h.estadoEmocional) : 'primary');
        var nivel = Number(h.nivelEnergia || 0);
        var colorBarra = (typeof getEnergiaColor === 'function' ? getEnergiaColor(nivel) : 'primary');

        return "<tr>" +
            "<td>" + escapeHtmlEvolucion(fecha) + "</td>" +
            "<td>" + escapeHtmlEvolucion(h.paciente || "---") + renderRiesgoBajoBadge(h.idPaciente || h.idUsuario) + "</td>" +
            "<td><span class='badge bg-" + colorEstado + "'>" + escapeHtmlEvolucion(h.estadoEmocional || "---") + "</span></td>" +
            "<td><div class='energia-bar'><div class='bar'><div class='fill bg-" + colorBarra + "' style='width:" + Math.min(nivel * 10, 100) + "%'></div></div><small class='text-muted'>" + escapeHtmlEvolucion(nivel) + "</small></div></td>" +
            "<td>" + escapeHtmlEvolucion(h.notasPersonales || "---") + "</td>" +
            "</tr>";
    }).join('');
}

function actualizarBadgeEvolucion() {
    var badge = document.getElementById("badgeEvol");
    if (badge) badge.textContent = window.evolucionData ? window.evolucionData.length : 0;
}

