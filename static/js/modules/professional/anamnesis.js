// ============================================================
// static/js/modules/professional/anamnesis.js
// Gestión de Anamnesis Clínica y Dinámica Familiar
// ============================================================

var currentAnamnesis = null;
var modoEdicionAnamnesis = false;
var contadorFamiliares = 0;

// Opciones de parentesco y salud para familiares
var PARENTESCO_OPCIONES = [
    { value: "PADRE", text: "Padre" },
    { value: "MADRE", text: "Madre" },
    { value: "HIJO", text: "Hijo" },
    { value: "HIJA", text: "Hija" },
    { value: "HERMANO", text: "Hermano" },
    { value: "HERMANA", text: "Hermana" },
    { value: "CONYUGE", text: "Cónyuge / Pareja" },
    { value: "ABUELO_PATERNO", text: "Abuelo paterno" },
    { value: "ABUELA_PATERNA", text: "Abuela paterna" },
    { value: "ABUELO_MATERNO", text: "Abuelo materno" },
    { value: "ABUELA_MATERNA", text: "Abuela materna" },
    { value: "TIO", text: "Tío" },
    { value: "TIA", text: "Tía" },
    { value: "PRIMO", text: "Primo" },
    { value: "PRIMA", text: "Prima" },
    { value: "BISABUELO", text: "Bisabuelo" },
    { value: "OTRO", text: "Otro" }
];

var ESTADO_SALUD_OPCIONES = [
    { value: "sano", text: "Sano" },
    { value: "enfermedad_cronica", text: "Enfermedad crónica" },
    { value: "discapacidad", text: "Discapacidad" },
    { value: "fallecido", text: "Fallecido" },
    { value: "desconocido", text: "Desconocido" }
];

// ── Navegación entre pasos de Anamnesis ──────────────────────

function irAPaso(paso) {
    if (paso === 2 && !pacienteSeleccionado) {
        if (typeof PsyAIAlerts !== 'undefined') {
            PsyAIAlerts.warning('Selecciona un paciente', 'Debes seleccionar un paciente antes de pasar a la ficha clínica.');
        } else {
            alert('Debes seleccionar un paciente antes de continuar.');
        }
        return;
    }

    var panel1 = document.getElementById("panelStep1");
    var panel2 = document.getElementById("panelStep2");
    var step1  = document.getElementById("step1");
    var step2  = document.getElementById("step2");

    if (paso === 1) {
        if (panel1) panel1.classList.remove("d-none");
        if (panel2) panel2.classList.add("d-none");
        if (step1) { step1.classList.add("active"); step1.classList.remove("done"); }
        if (step2) { step2.classList.remove("active", "done"); }

        document.getElementById("progressLabel").textContent = "Paso 1 de 2 — Seleccionar paciente";
        document.getElementById("progressPct").textContent   = "50%";
        document.getElementById("progressFill").style.width  = "50%";
    } else if (paso === 2) {
        if (panel1) panel1.classList.add("d-none");
        if (panel2) panel2.classList.remove("d-none");
        if (step1) { step1.classList.remove("active"); step1.classList.add("done"); }
        if (step2) { step2.classList.add("active"); }

        document.getElementById("progressLabel").textContent = "Paso 2 de 2 — Ficha de Anamnesis Clínica";
        document.getElementById("progressPct").textContent   = "100%";
        document.getElementById("progressFill").style.width  = "100%";
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Calcular edad en vivo ────────────────────────────────────

function calcularEdad(fechaStr) {
    if (!fechaStr) return '';
    var partes = fechaStr.split('-');
    if (partes.length !== 3) return '';
    var anio = parseInt(partes[0], 10);
    var mes  = parseInt(partes[1], 10) - 1;
    var dia  = parseInt(partes[2], 10);
    var nac  = new Date(anio, mes, dia);
    if (isNaN(nac.getTime())) return '';

    var hoy = new Date();
    var edad = hoy.getFullYear() - nac.getFullYear();
    var m = hoy.getMonth() - nac.getMonth();
    if (m < 0 || (m === 0 && hoy.getDate() < nac.getDate())) {
        edad--;
    }
    return edad >= 0 ? edad : 0;
}

function onFechaNacimientoChange() {
    var inputFecha = document.getElementById("anam_fechaNacimiento");
    var inputEdad  = document.getElementById("anam_edad");
    if (inputFecha && inputEdad) {
        var edad = calcularEdad(inputFecha.value);
        inputEdad.value = (edad !== '') ? edad : '';
    }
}

// ── Verificar Anamnesis del paciente ────────────────────────

async function verificarAnamnesis(pacienteId) {
    if (!pacienteId) return;

    var badgeEstado = document.getElementById("badgeEstadoAnamnesis");
    var btnGuardar  = document.getElementById("btnGuardarAnamnesis");
    var txtActualiz = document.getElementById("fechaActualizacionAnamnesis");

    if (badgeEstado) {
        badgeEstado.className = "badge bg-secondary-subtle text-secondary";
        badgeEstado.innerHTML = "<i class='fas fa-spinner fa-spin me-1'></i>Consultando estado...";
    }

    try {
        var res = await fetch("/api/paciente/" + pacienteId + "/anamnesis", {
            credentials: "include"
        });

        if (res.status === 200) {
            var data = await res.json();
            if (data.success && data.anamnesis) {
                currentAnamnesis = data.anamnesis;
                modoEdicionAnamnesis = true;
                poblarFormulario(data.anamnesis);

                if (btnGuardar) {
                    btnGuardar.className = "btn btn-primary px-4";
                    btnGuardar.innerHTML = "<i class='fas fa-save me-2'></i>Actualizar anamnesis";
                }
                if (badgeEstado) {
                    badgeEstado.className = "badge bg-success-subtle text-success border border-success-subtle px-2 py-1";
                    badgeEstado.innerHTML = "<i class='fas fa-check-circle me-1'></i>Anamnesis registrada (Edición)";
                }
                if (txtActualiz && data.anamnesis.fechaActualizacion) {
                    var d = new Date(data.anamnesis.fechaActualizacion);
                    txtActualiz.textContent = "Última actualización: " + d.toLocaleString();
                }
                return;
            }
        }

        if (res.status === 404) {
            // No existe anamnesis -> modo creación
            currentAnamnesis = null;
            modoEdicionAnamnesis = false;
            limpiarFormulario();

            if (btnGuardar) {
                btnGuardar.className = "btn btn-success px-4";
                btnGuardar.innerHTML = "<i class='fas fa-save me-2'></i>Guardar anamnesis";
            }
            if (badgeEstado) {
                badgeEstado.className = "badge bg-warning-subtle text-warning border border-warning-subtle px-2 py-1";
                badgeEstado.innerHTML = "<i class='fas fa-plus-circle me-1'></i>Ficha clínica pendiente";
            }
            if (txtActualiz) {
                txtActualiz.textContent = "Sin registrar";
            }
            return;
        }

        if (res.status === 403) {
            currentAnamnesis = null;
            modoEdicionAnamnesis = false;
            limpiarFormulario();
            if (badgeEstado) {
                badgeEstado.className = "badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1";
                badgeEstado.innerHTML = "<i class='fas fa-lock me-1'></i>Creada por otro profesional";
            }
            if (typeof PsyAIAlerts !== 'undefined') {
                PsyAIAlerts.warning('Acceso Restringido', 'La anamnesis de este paciente fue registrada por otro profesional y solo puede ser gestionada por su autor.');
            }
            return;
        }

        console.error("Respuesta inesperada al consultar anamnesis:", res.status);
    } catch (err) {
        console.error("Error al consultar anamnesis:", err);
    }
}

// ── Poblar formulario con datos existentes ───────────────────

function poblarFormulario(anam) {
    if (!anam) return;

    // A. Personales
    setVal("anam_tipoDocumento", anam.tipoDocumento);
    setVal("anam_numeroDocumento", anam.numeroDocumento);
    setVal("anam_fechaNacimiento", anam.fechaNacimiento);
    setVal("anam_edad", (anam.edad !== null && anam.edad !== undefined) ? anam.edad : calcularEdad(anam.fechaNacimiento));
    setVal("anam_genero", anam.genero);
    setVal("anam_estadoCivil", anam.estadoCivil);
    setVal("anam_orientacionSexual", anam.orientacionSexual);
    setVal("anam_razaEtnica", anam.razaEtnica);
    setVal("anam_lugarNacimiento", anam.lugarNacimiento);

    // B. Contacto
    setVal("anam_telefonoPrincipal", anam.telefonoPrincipal);
    setVal("anam_telefonoAlterno", anam.telefonoAlterno);
    setVal("anam_whatsapp", anam.whatsapp);
    setVal("anam_correoAlterno", anam.correoAlterno);
    setVal("anam_direccionResidencia", anam.direccionResidencia);
    setVal("anam_ciudad", anam.ciudad);
    setVal("anam_departamento", anam.departamento);
    setVal("anam_barrio", anam.barrio);
    setVal("anam_codigoPostal", anam.codigoPostal);
    setVal("anam_emergenciaNombre", anam.emergenciaNombre);
    setVal("anam_emergenciaParentesco", anam.emergenciaParentesco);
    setVal("anam_emergenciaTelefono", anam.emergenciaTelefono);

    // C. Escolar y Ocupación
    setVal("anam_nivelEscolar", anam.nivelEscolar);
    setVal("anam_institucionEducativa", anam.institucionEducativa);
    setVal("anam_anoGraduacion", anam.anoGraduacion);
    setVal("anam_carreraEstudiada", anam.carreraEstudiada);
    setVal("anam_estudiaActualmente", boolToStr(anam.estudiaActualmente));
    setVal("anam_ocupacion", anam.ocupacion);
    setVal("anam_situacionLaboral", anam.situacionLaboral);
    setVal("anam_empresa", anam.empresa);
    setVal("anam_cargo", anam.cargo);
    setVal("anam_rangoIngresosMensuales", anam.rangoIngresosMensuales);

    // D. Salud y Psicosocial
    setVal("anam_seguroSalud", boolToStr(anam.seguroSalud));
    setVal("anam_epsNombre", anam.epsNombre);
    setVal("anam_alergias", anam.alergias);
    setVal("anam_cirugiasPrevias", anam.cirugiasPrevias);
    setVal("anam_enfermedadesCronicas", anam.enfermedadesCronicas);
    setVal("anam_medicamentosActuales", anam.medicamentosActuales);
    setVal("anam_discapacidad", boolToStr(anam.discapacidad));
    setVal("anam_tipoDiscapacidad", anam.tipoDiscapacidad);
    setVal("anam_conviveCon", anam.conviveCon);
    setVal("anam_personasQueVivenCon", anam.personasQueVivenCon);
    setVal("anam_cantidadHijos", anam.cantidadHijos);
    setVal("anam_consumoAlcohol", anam.consumoAlcohol);
    setVal("anam_consumoTabaco", anam.consumoTabaco);
    setVal("anam_consumoSustancias", anam.consumoSustancias);
    setVal("anam_suenoHoras", anam.suenoHoras);
    setVal("anam_calidadSueno", anam.calidadSueno);
    setVal("anam_actividadFisica", anam.actividadFisica);

    // E. Entrevista
    setVal("anam_motivoConsulta", anam.motivoConsulta);
    setVal("anam_antecedentesFamiliares", anam.antecedentesFamiliares);
    setVal("anam_narrativa", anam.narrativa);
    setVal("anam_observaciones", anam.observaciones);
    setVal("anam_entrevistador", anam.entrevistador);

    // Familiares
    limpiarFamiliares();
    if (anam.familiares && Array.isArray(anam.familiares) && anam.familiares.length > 0) {
        anam.familiares.forEach(function (f) {
            agregarFamiliar(f);
        });
    }
}

// ── Limpiar formulario ───────────────────────────────────────

function limpiarFormulario() {
    var form = document.getElementById("formAnamnesis");
    if (form) form.reset();
    limpiarFamiliares();
    var inputEdad = document.getElementById("anam_edad");
    if (inputEdad) inputEdad.value = '';
}

function limpiarFamiliares() {
    var tbody = document.getElementById("tablaFamiliaresBody");
    if (tbody) tbody.innerHTML = "";
    contadorFamiliares = 0;
    actualizarEmptyStateFamiliares();
}

function actualizarEmptyStateFamiliares() {
    var tbody = document.getElementById("tablaFamiliaresBody");
    var empty = document.getElementById("emptyFamiliaresMsg");
    if (!tbody || !empty) return;
    if (tbody.children.length === 0) {
        empty.classList.remove("d-none");
    } else {
        empty.classList.add("d-none");
    }
}

// ── Manejo de Familiares Dinámicos ───────────────────────────

function agregarFamiliar(data) {
    contadorFamiliares++;
    var tbody = document.getElementById("tablaFamiliaresBody");
    if (!tbody) return;

    var tr = document.createElement("tr");
    tr.className = "fam-row";

    var d = data || {};
    var parentescoOpts = PARENTESCO_OPCIONES.map(function(opt) {
        var sel = (d.tipoParentesco === opt.value) ? " selected" : "";
        return '<option value="' + opt.value + '"' + sel + '>' + opt.text + '</option>';
    }).join("");

    var saludOpts = ESTADO_SALUD_OPCIONES.map(function(opt) {
        var sel = (d.estadoSalud === opt.value) ? " selected" : "";
        return '<option value="' + opt.value + '"' + sel + '>' + opt.text + '</option>';
    }).join("");

    var vivoVal = (d.vivo === true) ? "true" : ((d.vivo === false) ? "false" : "");

    tr.innerHTML =
        '<td class="text-center"><span class="fam-counter-badge">' + contadorFamiliares + '</span></td>' +
        '<td><select class="form-select fam-parentesco">' +
            '<option value="">Seleccione...</option>' + parentescoOpts +
        '</select></td>' +
        '<td><input type="text" class="form-control fam-nombre" placeholder="Nombre completo" value="' + escapeAttr(d.nombreCompleto) + '"></td>' +
        '<td><input type="number" class="form-control fam-edad" placeholder="Edad" min="0" max="130" value="' + escapeAttr(d.edad) + '"></td>' +
        '<td><select class="form-select fam-vivo">' +
            '<option value="">—</option>' +
            '<option value="true"' + (vivoVal === "true" ? " selected" : "") + '>Sí</option>' +
            '<option value="false"' + (vivoVal === "false" ? " selected" : "") + '>No</option>' +
        '</select></td>' +
        '<td><select class="form-select fam-salud">' +
            '<option value="">Seleccione...</option>' + saludOpts +
        '</select></td>' +
        '<td><input type="text" class="form-control fam-diagnostico" placeholder="Enfermedades o diagnósticos..." value="' + escapeAttr(d.diagnosticoOEnfermedad) + '"></td>' +
        '<td><input type="text" class="form-control fam-ocupacion" placeholder="Ocupación..." value="' + escapeAttr(d.ocupacion) + '"></td>' +
        '<td><input type="text" class="form-control fam-telefono" placeholder="Teléfono..." value="' + escapeAttr(d.telefono) + '"></td>' +
        '<td class="text-center">' +
            '<button type="button" class="btn btn-sm btn-outline-danger" title="Eliminar pariente" onclick="eliminarFamiliar(this)">' +
                '<i class="fas fa-trash-alt"></i>' +
            '</button>' +
        '</td>';

    tbody.appendChild(tr);
    actualizarEmptyStateFamiliares();
}

function eliminarFamiliar(btn) {
    if (!btn) return;
    var tr = btn.closest("tr");
    if (tr) tr.remove();

    // Renumerar filas
    var tbody = document.getElementById("tablaFamiliaresBody");
    if (tbody) {
        var rows = tbody.querySelectorAll("tr.fam-row");
        contadorFamiliares = rows.length;
        rows.forEach(function(row, idx) {
            var badge = row.querySelector(".fam-counter-badge");
            if (badge) badge.textContent = idx + 1;
        });
    }
    actualizarEmptyStateFamiliares();
}

function recopilarFamiliares() {
    var tbody = document.getElementById("tablaFamiliaresBody");
    if (!tbody) return [];

    var familiares = [];
    var rows = tbody.querySelectorAll("tr.fam-row");
    rows.forEach(function(row, idx) {
        var parentesco = row.querySelector(".fam-parentesco")?.value || null;
        var nombre     = row.querySelector(".fam-nombre")?.value?.trim() || null;
        var edadVal    = row.querySelector(".fam-edad")?.value;
        var edad       = edadVal ? parseInt(edadVal, 10) : null;
        var vivoStr    = row.querySelector(".fam-vivo")?.value;
        var vivo       = (vivoStr === "true") ? true : ((vivoStr === "false") ? false : null);
        var salud      = row.querySelector(".fam-salud")?.value || null;
        var diag       = row.querySelector(".fam-diagnostico")?.value?.trim() || null;
        var ocupacion  = row.querySelector(".fam-ocupacion")?.value?.trim() || null;
        var tel        = row.querySelector(".fam-telefono")?.value?.trim() || null;

        // Solo incluir si tiene al menos parentesco o nombre
        if (parentesco || nombre) {
            familiares.push({
                tipoParentesco: parentesco,
                nombreCompleto: nombre,
                edad: isNaN(edad) ? null : edad,
                vivo: vivo,
                estadoSalud: salud,
                diagnosticoOEnfermedad: diag,
                ocupacion: ocupacion,
                telefono: tel,
                orden: idx
            });
        }
    });

    return familiares;
}

// ── Validación de Anamnesis ──────────────────────────────────

function validarAnamnesis() {
    var requeridos = [
        { id: "anam_fechaNacimiento", nombre: "Fecha de nacimiento" },
        { id: "anam_telefonoPrincipal", nombre: "Teléfono principal" },
        { id: "anam_direccionResidencia", nombre: "Dirección de residencia" },
        { id: "anam_nivelEscolar", nombre: "Nivel escolar" },
        { id: "anam_motivoConsulta", nombre: "Motivo de consulta" }
    ];

    for (var i = 0; i < requeridos.length; i++) {
        var campo = requeridos[i];
        var el = document.getElementById(campo.id);
        var val = el ? el.value.trim() : "";
        if (!val) {
            if (typeof PsyAIAlerts !== 'undefined') {
                PsyAIAlerts.warning("Campo obligatorio", "Por favor completa el campo requerido: " + campo.nombre);
            } else {
                alert("Por favor completa: " + campo.nombre);
            }
            if (el) {
                el.focus();
                el.classList.add("is-invalid");
                setTimeout(function() { el.classList.remove("is-invalid"); }, 4000);
            }
            return false;
        }
    }
    return true;
}

// ── Recopilar Payload Completo ───────────────────────────────

function recopilarPayloadAnamnesis() {
    return {
        // A. Personales
        tipoDocumento: getValOrNull("anam_tipoDocumento"),
        numeroDocumento: getValOrNull("anam_numeroDocumento"),
        fechaNacimiento: getValOrNull("anam_fechaNacimiento"),
        edad: getIntOrNull("anam_edad"),
        genero: getValOrNull("anam_genero"),
        estadoCivil: getValOrNull("anam_estadoCivil"),
        orientacionSexual: getValOrNull("anam_orientacionSexual"),
        razaEtnica: getValOrNull("anam_razaEtnica"),
        lugarNacimiento: getValOrNull("anam_lugarNacimiento"),

        // B. Contacto
        telefonoPrincipal: getValOrNull("anam_telefonoPrincipal"),
        telefonoAlterno: getValOrNull("anam_telefonoAlterno"),
        whatsapp: getValOrNull("anam_whatsapp"),
        correoAlterno: getValOrNull("anam_correoAlterno"),
        direccionResidencia: getValOrNull("anam_direccionResidencia"),
        ciudad: getValOrNull("anam_ciudad"),
        departamento: getValOrNull("anam_departamento"),
        barrio: getValOrNull("anam_barrio"),
        codigoPostal: getValOrNull("anam_codigoPostal"),
        emergenciaNombre: getValOrNull("anam_emergenciaNombre"),
        emergenciaParentesco: getValOrNull("anam_emergenciaParentesco"),
        emergenciaTelefono: getValOrNull("anam_emergenciaTelefono"),

        // C. Escolar y Ocupación
        nivelEscolar: getValOrNull("anam_nivelEscolar"),
        institucionEducativa: getValOrNull("anam_institucionEducativa"),
        anoGraduacion: getIntOrNull("anam_anoGraduacion"),
        carreraEstudiada: getValOrNull("anam_carreraEstudiada"),
        estudiaActualmente: getBoolOrNull("anam_estudiaActualmente"),
        ocupacion: getValOrNull("anam_ocupacion"),
        situacionLaboral: getValOrNull("anam_situacionLaboral"),
        empresa: getValOrNull("anam_empresa"),
        cargo: getValOrNull("anam_cargo"),
        rangoIngresosMensuales: getValOrNull("anam_rangoIngresosMensuales"),

        // D. Salud y Psicosocial
        seguroSalud: getBoolOrNull("anam_seguroSalud"),
        epsNombre: getValOrNull("anam_epsNombre"),
        alergias: getValOrNull("anam_alergias"),
        cirugiasPrevias: getValOrNull("anam_cirugiasPrevias"),
        enfermedadesCronicas: getValOrNull("anam_enfermedadesCronicas"),
        medicamentosActuales: getValOrNull("anam_medicamentosActuales"),
        discapacidad: getBoolOrNull("anam_discapacidad"),
        tipoDiscapacidad: getValOrNull("anam_tipoDiscapacidad"),
        conviveCon: getValOrNull("anam_conviveCon"),
        personasQueVivenCon: getIntOrNull("anam_personasQueVivenCon"),
        cantidadHijos: getIntOrNull("anam_cantidadHijos"),
        consumoAlcohol: getValOrNull("anam_consumoAlcohol"),
        consumoTabaco: getValOrNull("anam_consumoTabaco"),
        consumoSustancias: getValOrNull("anam_consumoSustancias"),
        suenoHoras: getFloatOrNull("anam_suenoHoras"),
        calidadSueno: getValOrNull("anam_calidadSueno"),
        actividadFisica: getValOrNull("anam_actividadFisica"),

        // E. Entrevista
        motivoConsulta: getValOrNull("anam_motivoConsulta"),
        antecedentesFamiliares: getValOrNull("anam_antecedentesFamiliares"),
        narrativa: getValOrNull("anam_narrativa"),
        observaciones: getValOrNull("anam_observaciones"),
        entrevistador: getValOrNull("anam_entrevistador"),

        // Familiares
        familiares: recopilarFamiliares()
    };
}

// ── Guardar o Actualizar Anamnesis ───────────────────────────

async function guardarOActualizarAnamnesis() {
    if (!pacienteSeleccionado) {
        if (typeof PsyAIAlerts !== 'undefined') {
            PsyAIAlerts.warning("Sin paciente", "Selecciona primero un paciente.");
        } else {
            alert("Selecciona primero un paciente.");
        }
        return;
    }

    if (!validarAnamnesis()) return;

    var payload = recopilarPayloadAnamnesis();
    var metodo  = modoEdicionAnamnesis ? "PUT" : "POST";
    var url     = "/api/paciente/" + pacienteSeleccionado + "/anamnesis";

    var btnGuardar = document.getElementById("btnGuardarAnamnesis");
    var originalHtml = btnGuardar ? btnGuardar.innerHTML : "";
    if (btnGuardar) {
        btnGuardar.disabled = true;
        btnGuardar.innerHTML = "<i class='fas fa-spinner fa-spin me-2'></i>Guardando...";
    }

    try {
        var res = await fetch(url, {
            method: metodo,
            headers: {
                "Content-Type": "application/json"
            },
            credentials: "include",
            body: JSON.stringify(payload)
        });

        var data = await res.json();

        if (res.ok && data.success) {
            var msg = modoEdicionAnamnesis
                ? "Anamnesis actualizada correctamente"
                : "Anamnesis registrada correctamente";

            if (typeof PsyAIAlerts !== 'undefined') {
                PsyAIAlerts.success("Ficha Guardada", msg);
            } else {
                alert(msg);
            }

            // Cambiar a modo edición con los datos retornados
            modoEdicionAnamnesis = true;
            currentAnamnesis = data.anamnesis;
            poblarFormulario(data.anamnesis);

            var badgeEstado = document.getElementById("badgeEstadoAnamnesis");
            if (badgeEstado) {
                badgeEstado.className = "badge bg-success-subtle text-success border border-success-subtle px-2 py-1";
                badgeEstado.innerHTML = "<i class='fas fa-check-circle me-1'></i>Anamnesis registrada (Edición)";
            }
            if (btnGuardar) {
                btnGuardar.className = "btn btn-primary px-4";
                btnGuardar.innerHTML = "<i class='fas fa-save me-2'></i>Actualizar anamnesis";
            }
            var txtActualiz = document.getElementById("fechaActualizacionAnamnesis");
            if (txtActualiz && data.anamnesis && data.anamnesis.fechaActualizacion) {
                var d = new Date(data.anamnesis.fechaActualizacion);
                txtActualiz.textContent = "Última actualización: " + d.toLocaleString();
            }

            // Notificar al dashboard si aplica
            localStorage.setItem('psyai_dashboard_update', Date.now());
        } else {
            var errorMsg = data.message || "Error al procesar la anamnesis";
            if (typeof PsyAIAlerts !== 'undefined') {
                PsyAIAlerts.error("Error", errorMsg);
            } else {
                alert("Error: " + errorMsg);
            }
        }
    } catch (e) {
        console.error("Error en guardarOActualizarAnamnesis:", e);
        if (typeof PsyAIAlerts !== 'undefined') {
            PsyAIAlerts.error("Error de conexión", e.message || "No fue posible conectar con el servidor.");
        } else {
            alert("Error de conexión");
        }
    } finally {
        if (btnGuardar) {
            btnGuardar.disabled = false;
            if (btnGuardar.innerHTML.includes("fa-spinner")) {
                btnGuardar.innerHTML = originalHtml;
            }
        }
    }
}

// ── Helpers de Utilidad ──────────────────────────────────────

function setVal(id, val) {
    var el = document.getElementById(id);
    if (el) el.value = (val !== null && val !== undefined) ? val : "";
}

function getValOrNull(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    var v = el.value.trim();
    return v === "" ? null : v;
}

function getIntOrNull(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    var v = el.value.trim();
    if (v === "") return null;
    var n = parseInt(v, 10);
    return isNaN(n) ? null : n;
}

function getFloatOrNull(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    var v = el.value.trim();
    if (v === "") return null;
    var n = parseFloat(v);
    return isNaN(n) ? null : n;
}

function getBoolOrNull(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    var v = el.value.trim();
    if (v === "true") return true;
    if (v === "false") return false;
    return null;
}

function boolToStr(b) {
    if (b === true) return "true";
    if (b === false) return "false";
    return "";
}

function escapeAttr(val) {
    if (val === null || val === undefined) return "";
    return String(val)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}
