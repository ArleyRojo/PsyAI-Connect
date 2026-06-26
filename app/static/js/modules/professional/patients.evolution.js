var pacientesEvolucionData = window.pacientesEvolucionData || [];

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
            return '<option value="' + escapeHtmlEvolucion(option.value) + '">' + escapeHtmlEvolucion(option.label) + '</option>';
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
        
        evolucionData = (data.success && data.historial ? data.historial : []).sort(function (a, b) {
            return new Date(b.fechaRaw || b.fecha || 0) - new Date(a.fechaRaw || a.fecha || 0);
        });

        await cargarPacientesSelectEvolucion(evolucionData);
        actualizarBadgeEvolucion();
        filtrarEvolucionPorPaciente(); // Re-apply filter and render
    } catch (e) {
        console.error(e);
        evolucionData = [];
        await cargarPacientesSelectEvolucion([]);
        actualizarBadgeEvolucion();
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error al cargar la evolución</td></tr>';
    }
}

function filtrarEvolucionPorPaciente() {
    var select = document.getElementById("selectPacienteEvolucion");
    var filtro = select?.value || "";
    
    if (!filtro) {
        renderEvolucion(evolucionData);
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
            "<td>" + escapeHtmlEvolucion(h.paciente || "---") + "</td>" +
            "<td><span class='badge bg-" + colorEstado + "'>" + escapeHtmlEvolucion(h.estadoEmocional || "---") + "</span></td>" +
            "<td><div class='energia-bar'><div class='bar'><div class='fill bg-" + colorBarra + "' style='width:" + Math.min(nivel * 10, 100) + "%'></div></div><small class='text-muted'>" + escapeHtmlEvolucion(nivel) + "</small></div></td>" +
            "<td>" + escapeHtmlEvolucion(h.notasPersonales || "---") + "</td>" +
            "</tr>";
    }).join('');
}

function actualizarBadgeEvolucion() {
    var badge = document.getElementById("badgeEvol");
<<<<<<< HEAD
    if (badge) badge.textContent = window.evolucionData ? window.evolucionData.length : 0;
=======
    if (badge) badge.textContent = Array.isArray(evolucionData) ? evolucionData.length : 0;
>>>>>>> main-local
}

