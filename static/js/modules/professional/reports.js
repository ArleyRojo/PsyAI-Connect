let reportesData = [];
let reportesEliminadosData = [];
let pacientesFiltroData = [];

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById("filtroPaciente")?.addEventListener("change", filtrarReportes);
    cargarReportes();
    cargarPacientesFiltro();
});

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

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function getPacienteFilterValue(item) {
    const id = getPacienteId(item);
    if (id !== null && id !== undefined && String(id) !== '') {
        return `id:${id}`;
    }
    return `name:${normalizarTexto(item?.paciente ?? item?.nombre ?? 'General')}`;
}

function syncPacienteSelects(pacientes = [], reportes = []) {
    const select = document.getElementById("paciente");
    const filtroSelect = document.getElementById("filtroPaciente");
    if (!select && !filtroSelect) return;

    pacientesFiltroData = pacientes;
    const opciones = new Map();

    pacientes.forEach(p => {
        const id = getPacienteId(p);
        const nombre = p.nombre || p.paciente;
        if (!nombre) return;
        if (id !== null && id !== undefined && String(id) !== '') {
            opciones.set(`id:${id}`, { value: id, filterValue: `id:${id}`, label: nombre, canCreate: true });
        } else {
            opciones.set(`name:${normalizarTexto(nombre)}`, { value: nombre, filterValue: `name:${normalizarTexto(nombre)}`, label: nombre, canCreate: false });
        }
    });

    reportes.forEach(r => {
        const label = r.paciente || 'General';
        const key = getPacienteFilterValue(r);
        if (!opciones.has(key)) {
            opciones.set(key, {
                value: getPacienteId(r) || label,
                filterValue: key,
                label,
                canCreate: Boolean(getPacienteId(r))
            });
        }
    });

    const ordered = [...opciones.values()].sort((a, b) => a.label.localeCompare(b.label, 'es'));

    if (select) {
        select.innerHTML = '<option value="">Todos los pacientes</option>' +
            ordered
                .filter(option => option.canCreate)
                .map(option => `<option value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</option>`)
                .join('');
    }

    if (filtroSelect) {
        const currentValue = filtroSelect.value;
        filtroSelect.innerHTML = '<option value="">Todos los pacientes</option>' +
            ordered.map(option => `<option value="${escapeHtml(option.filterValue)}">${escapeHtml(option.label)}</option>`).join('');
        if ([...filtroSelect.options].some(option => option.value === currentValue)) {
            filtroSelect.value = currentValue;
        }
    }
}

async function cargarReportes() {
    const tbody = document.getElementById("tablaReportes");
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="6" class="text-center"><i class="fas fa-spinner fa-spin"></i> Cargando...</td></tr>';

    try {
        const res = await fetch("/api/reportes/profesional", { credentials: "include" });

        if (res.status === 401) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Inicia sesión para ver reportes</td></tr>';
            return;
        }

        if (res.status === 403) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-warning py-4">Tu cuenta profesional debe ser verificada por el administrador para consultar y generar reportes.</td></tr>';
            const eliminados = document.getElementById("tablaReportesEliminados");
            if (eliminados) eliminados.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">Disponible despues de la verificacion.</td></tr>';
            document.getElementById("statTotal").textContent = "0";
            document.getElementById("statPendientes").textContent = "0";
            document.getElementById("statCompletados").textContent = "0";
            document.getElementById("statEliminados").textContent = "0";
            return;
        }

        const data = await res.json();

        // Actualizar estadísticas
        const stats = data.stats || {};
        document.getElementById("statTotal").textContent      = stats.total       || 0;
        document.getElementById("statPendientes").textContent = stats.pendientes  || 0;
        document.getElementById("statCompletados").textContent= stats.completados || 0;
        
        // Cargar reportes eliminados del servidor
        await cargarReportesEliminados();
        
        // Actualizar contador de eliminados
        document.getElementById("statEliminados").textContent = reportesEliminadosData.length;

        reportesData = data.reportes || [];
        const pacientes = [...pacientesFiltroData];
        (data.pacientes || []).forEach(p => {
            const id = getPacienteId(p);
            const exists = pacientes.some(x => {
                const otherId = getPacienteId(x);
                if (String(id) !== '' && String(otherId) !== '') {
                    return String(id) === String(otherId);
                }
                return (x.nombre || x.paciente) === (p.nombre || p.paciente);
            });
            if (!exists) pacientes.push(p);
        });
        syncPacienteSelects(pacientes, reportesData);

        // Tabla principal
        if (!data.success || !data.reportes || data.reportes.length === 0) {
            renderizarReportes([]);
            return;
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3"><i class="fas fa-folder-open me-2"></i>No hay reportes generados aún</td></tr>';
            return;
        }

        filtrarReportes();

    } catch(e) {
        console.error("Error cargando reportes:", e);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3"><i class="fas fa-folder-open me-2"></i>No hay reportes generados aún</td></tr>';
    }
}

async function cargarReportesEliminados() {
    try {
        const res = await fetch("/api/reportes/eliminados", { credentials: "include" });
        if (res.ok) {
            const data = await res.json();
            if (data.success && data.reportes) {
                reportesEliminadosData = data.reportes;
            } else {
                reportesEliminadosData = [];
            }
        } else {
            reportesEliminadosData = [];
        }
    } catch(e) {
        console.error("Error cargando reportes eliminados:", e);
        reportesEliminadosData = [];
    }
    actualizarTablaEliminados(reportesEliminadosData);
}

function actualizarTablaEliminados(eliminados) {
    const tbody = document.getElementById("tablaReportesEliminados");
    if (!tbody) return;

    reportesEliminadosData = eliminados;

    if (!eliminados || eliminados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3"><i class="fas fa-trash me-2"></i>No hay reportes eliminados</td></tr>';
        return;
    }

    tbody.innerHTML = eliminados.map(r => `
        <tr>
            <td>${r.fechaInicio || '—'}</td>
            <td>${r.fechaFin || '—'}</td>
            <td>${r.paciente || '—'}</td>
            <td>${r.tipoReporte || '—'}</td>
            <td><span class="badge-estado eliminado">${r.estado || 'Eliminado'}</span></td>
        </tr>
    `).join('');
}

function renderizarReportes(reportes) {
    const tbody = document.getElementById("tablaReportes");
    if (!tbody) return;

    if (!reportes || reportes.length === 0) {
        const filtro = document.getElementById("filtroPaciente")?.value || '';
        const mensaje = filtro ? 'No hay reportes generados para este paciente' : 'No hay reportes';
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-3"><i class="fas fa-folder-open me-2"></i>${mensaje}</td></tr>`;
        return;
    }

    tbody.innerHTML = reportes.map(r => {
        const estadoClass = getEstadoClass(r.estado);
        return `
            <tr>
                <td>${r.fechaInicio || '—'}</td>
                <td>${r.fechaFin || '—'}</td>
                <td>${r.paciente || '—'}</td>
                <td>${r.tipoReporte || '—'}</td>
                <td><span class="badge-estado ${estadoClass}">${r.estado || '—'}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-secondary me-1 btn-action btn-view" title="Ver reporte" aria-label="Ver reporte" onclick="verReporte(${r.idReporte})">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-primary me-1 btn-action btn-edit" title="Editar reporte" aria-label="Editar reporte" onclick="editarReporte(${r.idReporte})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger btn-action btn-delete" title="Eliminar reporte" aria-label="Eliminar reporte" onclick="eliminarReporte(${r.idReporte})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function getEstadoClass(estado) {
    const map = { 'Completado': 'completado', 'Pendiente': 'pendiente', 'Eliminado': 'eliminado' };
    return map[estado] || 'pendiente';
}

async function cargarPacientesFiltro() {
    try {
        const res = await fetch("/api/profesional/pacientes", { credentials: "include" });
        const data = await res.json();
        if (!data.success || !data.pacientes) return;

        syncPacienteSelects(data.pacientes, reportesData);
    } catch(e) {
        console.error("Error cargando pacientes:", e);
    }
}

async function generarReporte() {
    const idPaciente  = document.getElementById("paciente").value;
    const fechaInicio = document.getElementById("fecha_inicio").value;
    const fechaFin    = document.getElementById("fecha_fin").value;
    const tipoReporte = document.getElementById("tipo_reporte").value;

    if (!fechaInicio || !fechaFin) {
        PsyAIAlerts.warning('Fechas Requeridas', 'Debes ingresar la fecha de inicio y la fecha de fin');
        return;
    }

    if (new Date(fechaFin) < new Date(fechaInicio)) {
        PsyAIAlerts.warning('Fecha Inválida', 'La fecha de fin no puede ser anterior a la fecha de inicio');
        return;
    }

    if (!tipoReporte) {
        PsyAIAlerts.warning('Campo Requerido', 'Selecciona un tipo de reporte');
        return;
    }

    try {
        const res = await fetch("/api/reportes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
                idPaciente:   idPaciente || null,
                fechaInicio:  fechaInicio || null,
                fechaFin:     fechaFin || null,
                tipoReporte:  tipoReporte
            })
        });

        if (res.status === 401) {
            PsyAIAlerts.error('Sesión Expirada', 'Por favor inicia sesión nuevamente');
            return;
        }

        const data = await res.json();
        if (data.success) {
            PsyAIAlerts.success('Reporte Generado', 'El reporte se ha creado correctamente');
            localStorage.setItem('psyai_dashboard_update', Date.now());
            registrarActividadReciente('reporte', 'Reporte generado', 'Tipo: ' + tipoReporte);
            cargarReportes();
        } else {
            PsyAIAlerts.error('Error', data.message || 'No se pudo generar el reporte');
        }
    } catch(e) {
        PsyAIAlerts.error('Error', 'Error de conexión');
    }
}

function filtrarReportes() {
    const filtroSelect = document.getElementById("filtroPaciente");
    const filtro = filtroSelect?.value || '';
    if (!filtro) {
        renderizarReportes(reportesData);
        return;
    }

    const selectedOption = filtroSelect?.selectedOptions?.[0];
    const selectedName = normalizarTexto(selectedOption?.textContent || '');
    const selectedId = filtro.startsWith('id:') ? filtro.slice(3) : '';
    const selectedFilterName = filtro.startsWith('name:') ? filtro.slice(5) : '';

    renderizarReportes(reportesData.filter(r => {
        const reportId = getPacienteId(r);
        const reportName = normalizarTexto(r.paciente || r.nombre || '');

        if (selectedId && String(reportId) === selectedId) return true;
        if (selectedFilterName && reportName === selectedFilterName) return true;
        if (selectedName && reportName === selectedName) return true;

        return getPacienteFilterValue(r) === filtro;
    }));
}

window.filtrarReportes = filtrarReportes;

window.verReporte = function(idReporte) {
    const reporte = reportesData.find(r => r.idReporte === idReporte);
    if (!reporte) return;

    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value || '---';
    };

    setText('viewPacienteReporte', reporte.paciente);
    setText('viewTipoReporte', reporte.tipoReporte);
    setText('viewFechaInicioReporte', reporte.fechaInicio);
    setText('viewFechaFinReporte', reporte.fechaFin);
    setText('viewEstadoReporte', reporte.estado);

    setText('viewSintomasReporte', reporte.sintomas);
    setText('viewDiagnosticoReporte', reporte.diagnostico);
    setText('viewTratamientoReporte', reporte.tratamiento);

    const hasDetail = Boolean(reporte.sintomas || reporte.diagnostico || reporte.tratamiento);
    document.getElementById('viewDetalleReporte')?.classList.toggle('d-none', !hasDetail);
    document.getElementById('viewDetalleVacio')?.classList.toggle('d-none', hasDetail);

    new bootstrap.Modal(document.getElementById("modalVerReporte")).show();
};

window.editarReporte = function(idReporte) {
    const reporte = reportesData.find(r => r.idReporte === idReporte);
    if (!reporte) return;
    document.getElementById("editIdReporte").value    = idReporte;
    document.getElementById("editTipoReporte").value  = reporte.tipoReporte;
    document.getElementById("editEstado").value       = reporte.estado;
    new bootstrap.Modal(document.getElementById("modalEditarReporte")).show();
};

window.eliminarReporte = function(idReporte) {
    window.reporteAeliminar = idReporte;
    new bootstrap.Modal(document.getElementById("modalEliminarReporte")).show();
};

document.getElementById("btnGuardarEdicion").addEventListener("click", async function() {
    const idReporte   = document.getElementById("editIdReporte").value;
    const tipoReporte = document.getElementById("editTipoReporte").value;
    const estado      = document.getElementById("editEstado").value;

    try {
        const res = await fetch(`/api/reportes/${idReporte}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ tipoReporte, estado })
        });
        const data = await res.json();
        bootstrap.Modal.getInstance(document.getElementById("modalEditarReporte")).hide();
        if (data.success) {
            PsyAIAlerts.success('Actualizado', 'Reporte actualizado correctamente');
            localStorage.setItem('psyai_dashboard_update', Date.now());
            registrarActividadReciente('reporte', 'Reporte actualizado', 'Estado: ' + estado);
            cargarReportes();
        } else {
            PsyAIAlerts.error('Error', data.message || 'No se pudo actualizar');
        }
    } catch(e) {
        PsyAIAlerts.error('Error', 'Error de conexión');
    }
});

document.getElementById("btnConfirmarEliminar").addEventListener("click", async function() {
    const idReporte = window.reporteAeliminar;
    if (!idReporte) return;

    try {
        const res = await fetch(`/api/reportes/${idReporte}`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            credentials: "include"
        });
        const data = await res.json();
        bootstrap.Modal.getInstance(document.getElementById("modalEliminarReporte")).hide();
        window.reporteAeliminar = null;

            if (data.success) {
            const reporteEliminado = reportesData.find(r => r.idReporte === idReporte);
            
            if (reporteEliminado) {
                const eliminadoObj = {
                    fechaInicio: reporteEliminado.fechaInicio || '—',
                    fechaFin: reporteEliminado.fechaFin || '—',
                    paciente: reporteEliminado.paciente || '—',
                    tipoReporte: reporteEliminado.tipoReporte || '—',
                    estado: 'Eliminado',
                    idReporte: reporteEliminado.idReporte
                };
                
                reportesEliminadosData.unshift(eliminadoObj);
                actualizarTablaEliminados(reportesEliminadosData);
                document.getElementById("statEliminados").textContent = reportesEliminadosData.length;
                reportesData = reportesData.filter(r => r.idReporte !== idReporte);
                filtrarReportes();
            }
            
            localStorage.setItem('psyai_dashboard_update', Date.now());
            registrarActividadReciente('reporte', 'Reporte eliminado', reporteEliminado?.paciente || 'Reporte');
            PsyAIAlerts.success('Eliminado', 'Reporte eliminado correctamente');
        } else {
            PsyAIAlerts.error('Error', data.message || 'No se pudo eliminar');
        }
    } catch(e) {
        PsyAIAlerts.error('Error', 'Error de conexión');
    }
});
