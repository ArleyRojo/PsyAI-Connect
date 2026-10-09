// ============================================================
// js/aside-professional/patients.js
// ============================================================

var pacienteSeleccionado = null;   // idUsuario (Number)
var filaSeleccionadaAnterior = null;
var evolucionData = [];
var pacientesEvolucionData = [];

// Pagination state
var allPacientes = [];
var currentPage = 1;
var pageSize = 10;

// ── Init ─────────────────────────────────────────────────────

window.onload = function () {
    cargarSaludoProfesional();

    // Fecha de hoy por defecto
    var fechaInput = document.getElementById("fechaDiagnostico");
    if (fechaInput) {
        var hoy = new Date();
        var dd  = String(hoy.getDate()).padStart(2, '0');
        var mm  = String(hoy.getMonth() + 1).padStart(2, '0');
        fechaInput.value = hoy.getFullYear() + '-' + mm + '-' + dd;
    }

    cargarPacientes();
    cargarProfesionales();
    cargarHistorial();
    cargarEvolucion();
};

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&')
        .replace(/</g, '<')
        .replace(/>/g, '>')
        .replace(/"/g, '"')
        .replace(/'/g, '&#039;');
}

function normalizarTexto(valor) {
    return String(valor ?? '')
        .trim()
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
}

function getPacienteId(item) {
    return item?.idPaciente ?? item?.idUsuario ?? '';
}

function getPacienteFiltroValue(item) {
    var id = getPacienteId(item);
    if (id !== null && id !== undefined && String(id) !== '') return 'id:' + id;
    return 'name:' + normalizarTexto(item?.paciente || item?.nombre || '');
}

// ── Saludo con nombre real de sesión ─────────────────────────

async function cargarSaludoProfesional() {
    try {
        const res  = await fetch("/api/session", { credentials: "include" });
        if (res.status === 401) return;
        const data = await res.json();
        if (data.success && data.usuario) {
            const nombre = data.usuario.nombre || data.usuario.email?.split('@')[0] || 'Profesional';
            const el = document.getElementById("nombreProfesional");
            if (el) el.textContent = `Hola, Dr(a). ${nombre}`;
        }
    } catch (e) {
        console.error("Error cargando sesión:", e);
    }
}

// ── Cargar pacientes ─────────────────────────────────────────

function cargarPacientes() {
    var tbody = document.getElementById("tbodyPacientes");
    if (!tbody) return;

    tbody.innerHTML = "<tr><td colspan='7' class='text-center py-3'><i class='fas fa-spinner fa-spin me-2'></i>Cargando...</td></tr>";

    fetch("/api/pacientes", { credentials: "include" })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (!data.success) {
                tbody.innerHTML = "<tr><td colspan='7' class='text-danger text-center'>" + data.message + "</td></tr>";
                return;
            }

            var pacientes = data.pacientes || data.usuarios || [];

            if (pacientes.length === 0) {
                tbody.innerHTML = "<tr><td colspan='7' class='text-muted text-center py-4'>No hay pacientes registrados</td></tr>";
                renderPagination(0);
                return;
            }

            allPacientes = pacientes;
            currentPage = 1;
            renderPage(currentPage);
            renderPagination(allPacientes.length);
        })
        .catch(function (err) {
            console.error(err);
            tbody.innerHTML = "<tr><td colspan='7' class='text-danger text-center'>Error al cargar pacientes</td></tr>";
        });
}

function renderPage(page) {
    var tbody = document.getElementById("tbodyPacientes");
    if (!tbody) return;

    var start = (page - 1) * pageSize;
    var end = start + pageSize;
    var pageItems = allPacientes.slice(start, end);

    if (pageItems.length === 0) {
        tbody.innerHTML = "<tr><td colspan='7' class='text-muted text-center py-4'>No hay pacientes en esta página</td></tr>";
        return;
    }

    tbody.innerHTML = pageItems.map(function (p) {
        var inicial = (p.nombre || "P").charAt(0).toUpperCase();
        var colorLetra = coloresLetras[inicial.toUpperCase()] || "#6c757d";
        var fotoUrl = p.fotoPerfil
            ? "/uploads/" + p.fotoPerfil
            : svgAvatar(inicial, 35, colorLetra, 14);

        var isSelected = pacienteSeleccionado === Number(p.idUsuario);
        var btnClass   = "btn btn-sm btn-outline-primary btn-seleccionar" + (isSelected ? " active-btn" : "");
        var btnTxt     = isSelected ? "Seleccionado" : "Seleccionar";

        var emailSafe = (p.email || "").replace(/"/g, '"');
        var nomSafe   = (p.nombre || "").replace(/"/g, '"');
        var fotoSafe  = (p.fotoPerfil || "").replace(/"/g, '"');
        var pacienteId = Number(p.idUsuario);

        var badgeAnamnesis = p.tieneAnamnesis
            ? '<span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i class="fas fa-check-circle me-1"></i>Registrada</span>'
            : '<span class="badge bg-warning-subtle text-warning border border-warning-subtle px-2 py-1"><i class="fas fa-clock me-1"></i>Pendiente</span>';

        return '<tr class="patient-row' + (isSelected ? " selected-patient" : "") + '">' +
            '<td><img src="' + fotoUrl + '" class="rounded-circle me-2" style="width:35px;height:35px;object-fit:cover;" data-inicial="' + inicial + '" data-color="' + colorLetra + '" data-size="35" data-fz="14" onerror="fallbackAvatar(this)">' + (p.nombre || "—") + '</td>' +
            "<td>—</td>" +
            "<td>—</td>" +
            "<td>" + (p.email || "—") + "</td>" +
            "<td>" + badgeAnamnesis + "</td>" +
            '<td><button class="' + btnClass + '" onclick=\'seleccionarPaciente(' + pacienteId + ', "' + nomSafe + '", "' + fotoSafe + '", "' + emailSafe + '", this)\'>' + btnTxt + "</button></td>" +
            '<td><a href="historia_clinica_pro.html?pacienteId=' + pacienteId + '" class="btn btn-sm btn-outline-info" title="Ver historia clínica"><i class="fas fa-file-medical"></i></a></td>' +
            "</tr>";
    }).join('');
}

function renderPagination(totalItems) {
    var nav = document.getElementById("paginationNav");
    if (!nav) return;
    var totalPages = Math.ceil(totalItems / pageSize);
    if (totalPages <= 1) {
        nav.innerHTML = "";
        return;
    }
    var html = '<ul class="pagination pagination-sm mb-0">';
    // Previous
    html += '<li class="page-item' + (currentPage === 1 ? ' disabled' : '') + '"><a class="page-link" href="#" onclick="event.preventDefault(); goToPage(' + (currentPage - 1) + ')">&laquo;</a></li>';
    // Page numbers (show up to 5)
    var startPage = Math.max(1, currentPage - 2);
    var endPage = Math.min(totalPages, startPage + 4);
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    for (var i = startPage; i <= endPage; i++) {
        html += '<li class="page-item' + (i === currentPage ? ' active' : '') + '"><a class="page-link" href="#" onclick="event.preventDefault(); goToPage(' + i + ')">' + i + '</a></li>';
    }
    // Next
    html += '<li class="page-item' + (currentPage === totalPages ? ' disabled' : '') + '"><a class="page-link" href="#" onclick="event.preventDefault(); goToPage(' + (currentPage + 1) + ')">&raquo;</a></li>';
    html += '</ul>';
    nav.innerHTML = html;
}

function goToPage(page) {
    var totalPages = Math.ceil(allPacientes.length / pageSize);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    renderPage(currentPage);
    renderPagination(allPacientes.length);
}

// ── Seleccionar paciente ─────────────────────────────────────

function seleccionarPaciente(id, nombre, fotoPerfil, email, btn) {
    try {
        // Si ya estaba seleccionado, solo avisar
        if (pacienteSeleccionado === id) {
            PsyAIAlerts
                ? PsyAIAlerts.info('Ya seleccionado', 'Este paciente ya está seleccionado')
                : alert('Este paciente ya está seleccionado');
            return;
        }

        // Desmarcar fila anterior
        if (filaSeleccionadaAnterior) {
            filaSeleccionadaAnterior.fila.classList.remove('selected-patient');
            filaSeleccionadaAnterior.btn.classList.remove('active-btn');
            filaSeleccionadaAnterior.btn.textContent = 'Seleccionar';
        }

        // Marcar nueva fila
        var fila = btn.closest('tr');
        fila.classList.add('selected-patient');
        btn.classList.add('active-btn');
        btn.textContent = 'Seleccionado';
        filaSeleccionadaAnterior = { fila: fila, btn: btn };

        // Avatar
        var inicial = (nombre || "P").charAt(0).toUpperCase();
        var colorLetra = coloresLetras[inicial.toUpperCase()] || "#6c757d";
        var fotoUrl = fotoPerfil
            ? "/uploads/" + fotoPerfil
            : svgAvatar(inicial, 46, colorLetra, 18);

        // Guardar estado
        pacienteSeleccionado = id;
        document.getElementById("idPacienteSeleccionado").value = id;

        // Actualizar banner paso 1
        document.getElementById("selectedPatientName").textContent  = nombre;
        document.getElementById("selectedPatientEmail").textContent = email || '—';
        document.getElementById("selectedPatientPhoto").src         = fotoUrl;

        // Mostrar banner y ocultar botón solitario
        document.getElementById("selectedPatientPhoto").setAttribute("data-inicial", inicial);
        document.getElementById("selectedPatientPhoto").setAttribute("data-color", colorLetra);
        document.getElementById("selectedPatientPhoto").setAttribute("data-size", "46");
        document.getElementById("selectedPatientPhoto").setAttribute("data-fz", "18");
        document.getElementById("selectedPatientPhoto").onerror = function() { fallbackAvatar(this); };
        document.getElementById("step2Photo").setAttribute("data-inicial", inicial);
        document.getElementById("step2Photo").setAttribute("data-color", colorLetra);
        document.getElementById("step2Photo").setAttribute("data-size", "46");
        document.getElementById("step2Photo").setAttribute("data-fz", "18");
        document.getElementById("step2Photo").onerror = function() { fallbackAvatar(this); };
        document.getElementById("paciente-seleccionado-card").classList.remove('d-none');
        document.getElementById("wrapBtnContinuar").style.display = 'none';

        // Pre-cargar datos en el encabezado del paso 2
        document.getElementById("step2Photo").src          = fotoUrl;
        document.getElementById("step2Name").textContent   = nombre;
        document.getElementById("step2Email").textContent  = email || '—';

        // Llamar verificación de anamnesis si está disponible
        if (typeof verificarAnamnesis === 'function') {
            verificarAnamnesis(id);
        }

        if (typeof PsyAIAlerts !== 'undefined') {
            PsyAIAlerts.success('Paciente seleccionado', nombre + ' ha sido seleccionado');
        }

    } catch (e) {
        console.error(e);
        alert('Error al seleccionar: ' + e.message);
    }
}

// ── Deseleccionar paciente ────────────────────────────────────

function deseleccionarPaciente() {
    pacienteSeleccionado = null;
    document.getElementById('idPacienteSeleccionado').value = '';
    document.getElementById('selectedPatientName').textContent  = '—';
    document.getElementById('selectedPatientEmail').textContent = '—';
    document.getElementById('selectedPatientPhoto').src         = '';
    document.getElementById('paciente-seleccionado-card').classList.add('d-none');
    document.getElementById('wrapBtnContinuar').style.display   = '';
    document.getElementById('btnContinuarDiagSolo').disabled    = true;

    if (filaSeleccionadaAnterior) {
        filaSeleccionadaAnterior.fila.classList.remove('selected-patient');
        filaSeleccionadaAnterior.btn.classList.remove('active-btn');
        filaSeleccionadaAnterior.btn.textContent = 'Seleccionar';
        filaSeleccionadaAnterior = null;
    }

    if (typeof limpiarFormulario === 'function') {
        limpiarFormulario();
    }
}

// ── Delegar navegación de pasos a Anamnesis ───────────────────

function goToStep(n) {
    if (typeof irAPaso === 'function') {
        irAPaso(n);
    }
}

// ── Historial de diagnósticos ─────────────────────────────────

async function cargarHistorial() {
    try {
        var res  = await fetch("/api/diagnosticos", { credentials: "include" });
        var data = await res.json();
        var tbody = document.getElementById("tbodyHistorial");

        var badge = document.getElementById("badgeDiag");
        if (badge) badge.textContent = (data.success && data.historial) ? data.historial.length : 0;

        if (!data.success || !data.historial || data.historial.length === 0) {
            tbody.innerHTML = "<tr><td colspan='5' class='text-muted text-center py-3'>Sin diagnósticos registrados</td></tr>";
            return;
        }

        tbody.innerHTML = data.historial.map(function (h) {
            var fecha = formatearFecha(h.fechaRaw);
            return "<tr>" +
                "<td>" + (h.paciente    || "—") + "</td>" +
                "<td>" + fecha           + "</td>" +
                "<td>" + (h.sintomas    || "—") + "</td>" +
                "<td>" + (h.diagnostico || "—") + "</td>" +
                "<td>" + (h.tratamiento || "—") + "</td>" +
                "</tr>";
        }).join('');
    } catch (e) {
        console.error(e);
    }
}

// ── Filtro de búsqueda ────────────────────────────────────────

function filtrarPacientes() {
    var q = document.getElementById("searchInput").value.toLowerCase();
    if (!q) {
        // reset to full list
        if (allPacientes._original) {
            allPacientes = allPacientes._original;
            delete allPacientes._original;
        }
        currentPage = 1;
        renderPage(currentPage);
        renderPagination(allPacientes.length);
        return;
    }
    var filtered = allPacientes.filter(function(p) {
        var nombre = (p.nombre || "").toLowerCase();
        var email = (p.email || "").toLowerCase();
        return nombre.includes(q) || email.includes(q);
    });
    // temporarily replace allPacientes for pagination
    if (!allPacientes._original) {
        allPacientes._original = allPacientes;
    }
    allPacientes = filtered;
    currentPage = 1;
    renderPage(currentPage);
    renderPagination(filtered.length);
}

// Reset filter when search cleared
var searchInput = document.getElementById("searchInput");
if (searchInput) {
    searchInput.addEventListener('input', function() {
        if (this.value === '') {
            if (allPacientes._original) {
                allPacientes = allPacientes._original;
                delete allPacientes._original;
            }
            currentPage = 1;
            renderPage(currentPage);
            renderPagination(allPacientes.length);
        }
    });
}

// ── Profesionales ─────────────────────────────────────────────

function cargarProfesionales() {
    var select = document.getElementById("profesional");
    if (!select) return;

    fetch("/api/profesionales", { credentials: "include" })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (!data.success) return;
            var profs = data.profesionales || [];
            select.innerHTML = "<option value=''>Seleccionar profesional...</option>" +
                profs.map(function (p) {
                    return "<option value='" + p.nombre + "'>" + p.nombre + "</option>";
                }).join('');
        })
        .catch(function (err) { console.error(err); });
}

// ── Pestañas ──────────────────────────────────────────────────

function mostrarPestana(pestana, btnEl) {
    document.querySelectorAll('.tab').forEach(function (t) { t.classList.remove('active'); });
    if (btnEl) btnEl.classList.add('active');

    var panelDiagnosticos = document.getElementById('pestana-diagnosticos');
    var panelEvolucion = document.getElementById('pestana-evolucion');
    var panelPrediagnosticos = document.getElementById('pestana-prediagnosticos');

    if (panelDiagnosticos) panelDiagnosticos.style.display = pestana === 'diagnosticos' ? '' : 'none';
    if (panelEvolucion) panelEvolucion.style.display = pestana === 'evolucion' ? '' : 'none';
    if (panelPrediagnosticos) panelPrediagnosticos.style.display = pestana === 'prediagnosticos' ? '' : 'none';

    if (pestana === 'diagnosticos') {
        cargarPacientes();
        cargarHistorial();
    } else if (pestana === 'evolucion') {
        cargarEvolucion();
    } else if (pestana === 'prediagnosticos') {
        cargarPrediagnosticos();
    }
}

// ── Evolución ─────────────────────────────────────────────────
// (funciones de evolución definidas en patients.evolution.js)

// ── Helpers ───────────────────────────────────────────────────

function formatearFecha(raw) {
    if (!raw) return "—";
    var d = new Date(raw);
    if (isNaN(d)) return "—";
    return String(d.getDate()).padStart(2,'0') + '/' +
           String(d.getMonth()+1).padStart(2,'0') + '/' +
           d.getFullYear();
}

function getEnergiaColor(n) {
    if (n <= 3) return 'danger';
    if (n <= 5) return 'warning';
    if (n <= 7) return 'info';
    return 'success';
}

function getEstadoColor(e) {
    var m = { feliz:'success', tranquilo:'info', estresado:'warning', ansioso:'secondary', triste:'danger' };
    return m[(e || '').toLowerCase()] || 'primary';
}

var coloresLetras = {
    'A':'#1D9E75','B':'#378ADD','C':'#D85A30','D':'#534AB7','E':'#BA7517',
    'F':'#639922','G':'#D4537E','H':'#1D9E75','I':'#378ADD','J':'#D85A30',
    'K':'#534AB7','L':'#BA7517','M':'#639922','N':'#D4537E','O':'#1D9E75',
    'P':'#378ADD','Q':'#D85A30','R':'#534AB7','S':'#BA7517','T':'#639922',
    'U':'#D4537E','V':'#1D9E75','W':'#378ADD','X':'#D85A30','Y':'#534AB7',
    'Z':'#BA7517'
};

function fallbackAvatar(img) {
    if (!img || !img.parentNode) return;
    var inicial = img.getAttribute("data-inicial") || "?";
    var color = img.getAttribute("data-color") || coloresLetras[inicial.toUpperCase()] || "#6c757d";
    var size = parseInt(img.getAttribute("data-size")) || 35;
    var fz = parseInt(img.getAttribute("data-fz")) || 14;
    img.src = svgAvatar(inicial, size, color, fz);
    img.onerror = null;
}

function svgAvatar(letra, size, color, fontSize) {
    return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='" + size + "' height='" + size + "' viewBox='0 0 " + size + " " + size + "'%3E%3Ccircle cx='" + (size/2) + "' cy='" + (size/2) + "' r='" + (size/2) + "' fill='" + encodeURIComponent(color) + "'/%3E%3Ctext x='" + (size/2) + "' y='" + (size/2 + fontSize*0.4) + "' text-anchor='middle' fill='white' font-family='Arial' font-size='" + fontSize + "'%3E" + letra + "%3C/text%3E%3C/svg%3E";
}

// ── Chatbot Historial ───────────────────────────────────────────