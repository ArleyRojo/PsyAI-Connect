// ============================================================
// js/aside-professional/patients.js
// ============================================================

var pacienteSeleccionado = null;   // idUsuario (Number)
var filaSeleccionadaAnterior = null;
var evolucionData = [];
var pacientesEvolucionData = [];

// ── Init ─────────────────────────────────────────────────────

function initPatientsPage() {
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
    if (typeof cargarEvolucion === 'function') {
        cargarEvolucion();
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPatientsPage);
} else {
    initPatientsPage();
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
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

function actualizarBadgeDiagnosticos(total) {
    var badge = document.getElementById("badgeDiag");
    if (badge) badge.textContent = Number(total) || 0;
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
            actualizarBadgeDiagnosticos(pacientes.length);

            if (pacientes.length === 0) {
                tbody.innerHTML = "<tr><td colspan='7' class='text-muted text-center py-4'>No hay pacientes registrados</td></tr>";
                return;
            }

            tbody.innerHTML = pacientes.map(function (p) {
                var inicial = (p.nombre || "P").charAt(0).toUpperCase();
                var colorLetra = coloresLetras[inicial.toUpperCase()] || "#6c757d";
                var fotoUrl = p.fotoPerfil
                    ? "/uploads/" + p.fotoPerfil
                    : svgAvatar(inicial, 35, colorLetra, 14);

                // Si este paciente ya está seleccionado, marcar el botón
                var isSelected = pacienteSeleccionado === Number(p.idUsuario);
                var btnClass   = "btn btn-sm btn-outline-primary btn-seleccionar" + (isSelected ? " active-btn" : "");
                var btnTxt     = isSelected ? "Seleccionado" : "Seleccionar";

                var emailSafe = (p.email || "").replace(/"/g, '&quot;');
                var nomSafe   = (p.nombre || "").replace(/"/g, '&quot;');
                var fotoSafe  = (p.fotoPerfil || "").replace(/"/g, '&quot;');
                var pacienteId = Number(p.idUsuario);

                return '<tr class="patient-row' + (isSelected ? " selected-patient" : "") + '">' +
                    '<td><img src="' + fotoUrl + '" class="rounded-circle me-2" style="width:35px;height:35px;object-fit:cover;" data-inicial="' + inicial + '" data-color="' + colorLetra + '" data-size="35" data-fz="14" onerror="fallbackAvatar(this)">' + (p.nombre || "—") + '</td>' +
                    "<td>—</td>" +
                    "<td>—</td>" +
                    "<td>" + (p.email || "—") + "</td>" +
                    "<td>—</td>" +
                    '<td><button class="' + btnClass + '" onclick=\'seleccionarPaciente(' + pacienteId + ', "' + nomSafe + '", "' + fotoSafe + '", "' + emailSafe + '", this)\'>' + btnTxt + "</button></td>" +
                    '<td><a href="historia_clinica_pro.html?pacienteId=' + pacienteId + '" class="btn btn-sm btn-outline-info" title="Ver historia clínica"><i class="fas fa-file-medical"></i></a></td>' +
                    "</tr>";
            }).join('');
        })
        .catch(function (err) {
            console.error(err);
            actualizarBadgeDiagnosticos(0);
            tbody.innerHTML = "<tr><td colspan='7' class='text-danger text-center'>Error al cargar pacientes</td></tr>";
        });
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
}

// ── Navegación entre pasos ────────────────────────────────────

function goToStep(n) {
    // Validaciones
    if (n === 2 && !pacienteSeleccionado) {
        PsyAIAlerts
            ? PsyAIAlerts.warning('Selecciona un paciente', 'Debes seleccionar un paciente antes de continuar')
            : alert('Selecciona un paciente primero');
        return;
    }
    if (n === 3) {
        if (!validarFormulario()) return;
        buildResumen();
    }
    if (n === 1) {
        // Al volver al paso 1, limpiar selección de fila visualmente pero mantener el paciente
        // para que no se pierda si el usuario quiere editar el formulario
    }

    // Actualizar pasos visuales
    for (var i = 1; i <= 3; i++) {
        var panel = document.getElementById("panelStep" + i);
        var step  = document.getElementById("step" + i);
        panel.classList.add("d-none");
        step.classList.remove("active", "done");
        if (i < n) step.classList.add("done");
        else if (i === n) step.classList.add("active");
    }
    document.getElementById("panelStep" + n).classList.remove("d-none");

    // Barra de progreso
    var labels = { 1: "Paso 1 de 3 — Seleccionar paciente", 2: "Paso 2 de 3 — Registrar diagnóstico", 3: "Paso 3 de 3 — Confirmar y guardar" };
    var pcts   = { 1: "33%", 2: "66%", 3: "100%" };
    document.getElementById("progressLabel").textContent = labels[n];
    document.getElementById("progressPct").textContent   = pcts[n];
    document.getElementById("progressFill").style.width  = pcts[n];

    // Scroll al top del contenido
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Validar formulario paso 2 ────────────────────────────────

function validarFormulario() {
    var campos = [
        { id: "profesional",    msg: "Selecciona un profesional" },
        { id: "fechaDiagnostico", msg: "Selecciona una fecha" },
        { id: "sintomas",       msg: "Describe los síntomas" },
        { id: "diagnostico",    msg: "Ingresa el diagnóstico clínico" },
        { id: "tratamiento",    msg: "Ingresa el plan de tratamiento" }
    ];
    for (var i = 0; i < campos.length; i++) {
        var val = document.getElementById(campos[i].id)?.value?.trim();
        if (!val) {
            PsyAIAlerts
                ? PsyAIAlerts.warning('Campo requerido', campos[i].msg)
                : alert(campos[i].msg);
            document.getElementById(campos[i].id)?.focus();
            return false;
        }
    }
    return true;
}

// ── Resumen paso 3 ────────────────────────────────────────────

function buildResumen() {
    var campos = [
        { label: "Paciente",    val: document.getElementById("selectedPatientName").textContent },
        { label: "Profesional", val: document.getElementById("profesional").value },
        { label: "Fecha",       val: document.getElementById("fechaDiagnostico").value },
        { label: "Síntomas",    val: document.getElementById("sintomas").value },
        { label: "Diagnóstico", val: document.getElementById("diagnostico").value },
        { label: "Tratamiento", val: document.getElementById("tratamiento").value }
    ];

    document.getElementById("resumenContent").innerHTML = campos.map(function (c) {
        return '<div class="resumen-item"><label>' + c.label + '</label><span>' + (c.val || '—') + '</span></div>';
    }).join('');
}

// ── Guardar diagnóstico ───────────────────────────────────────

async function guardarDiagnostico() {
    if (!validarFormulario()) return;

    var body = {
        idPaciente:        pacienteSeleccionado,
        fecha_diagnostico: document.getElementById("fechaDiagnostico").value,
        profesional:       document.getElementById("profesional").value,
        sintomas:          document.getElementById("sintomas").value,
        diagnostico:       document.getElementById("diagnostico").value,
        tratamiento:       document.getElementById("tratamiento").value
    };

    try {
        var res  = await fetch("/api/diagnosticos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(body)
        });
        var data = await res.json();

        if (data.success) {
            PsyAIAlerts
                ? PsyAIAlerts.success('Guardado', 'Diagnóstico registrado correctamente')
                : alert('Diagnóstico guardado');

            localStorage.setItem('psyai_dashboard_update', Date.now());
            registrarActividadReciente('diagnostico', 'Diagnóstico registrado', 'Paciente: ' + document.getElementById("selectedPatientName").textContent);
            cargarHistorial();
            resetearFlujo();
        } else {
            PsyAIAlerts
                ? PsyAIAlerts.error('Error', data.message || 'No se pudo guardar')
                : alert('Error: ' + data.message);
        }
    } catch (e) {
        console.error(e);
        PsyAIAlerts
            ? PsyAIAlerts.error('Error de conexión', e.message)
            : alert('Error de conexión');
    }
}

// ── Resetear flujo tras guardar ───────────────────────────────

function resetearFlujo() {
    pacienteSeleccionado = null;
    if (filaSeleccionadaAnterior) {
        filaSeleccionadaAnterior.fila.classList.remove('selected-patient');
        filaSeleccionadaAnterior.btn.classList.remove('active-btn');
        filaSeleccionadaAnterior.btn.textContent = 'Seleccionar';
        filaSeleccionadaAnterior = null;
    }
    document.getElementById("formDiagnostico").reset();
    document.getElementById("paciente-seleccionado-card").classList.add('d-none');
    document.getElementById("wrapBtnContinuar").style.display   = '';
    document.getElementById("btnContinuarDiagSolo").disabled    = true;
    document.getElementById("idPacienteSeleccionado").value     = '';
    goToStep(1);
}

// ── Historial de diagnósticos ─────────────────────────────────

async function cargarHistorial() {
    try {
        var res  = await fetch("/api/diagnosticos", { credentials: "include" });
        var data = await res.json();
        var tbody = document.getElementById("tbodyHistorial");
        var historial = data.success && Array.isArray(data.historial) ? data.historial : [];

        actualizarBadgeDiagnosticos(Math.max(historial.length, Number(document.getElementById("badgeDiag")?.textContent) || 0));

        if (historial.length === 0) {
            tbody.innerHTML = "<tr><td colspan='5' class='text-muted text-center py-3'>Sin diagnósticos registrados</td></tr>";
            return;
        }

        tbody.innerHTML = historial.map(function (h) {
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
        actualizarBadgeDiagnosticos(Number(document.getElementById("badgeDiag")?.textContent) || 0);
    }
}

// ── Filtro de búsqueda ────────────────────────────────────────

function filtrarPacientes() {
    var q    = document.getElementById("searchInput").value.toLowerCase();
    var rows = document.querySelectorAll("#tbodyPacientes tr");
    rows.forEach(function (row) {
        row.style.display = row.textContent.toLowerCase().includes(q) ? "" : "none";
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

    if (panelDiagnosticos) panelDiagnosticos.style.display = pestana === 'diagnosticos' ? '' : 'none';
    if (panelEvolucion) panelEvolucion.style.display = pestana === 'evolucion' ? '' : 'none';

    if (pestana === 'diagnosticos') {
        cargarPacientes();
        cargarHistorial();
    } else if (pestana === 'evolucion') {
        cargarEvolucion();
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
