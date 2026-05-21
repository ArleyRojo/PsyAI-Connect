let reportesData = [];
let reportesEliminadosData = [];

document.addEventListener('DOMContentLoaded', function() {
    cargarReportes();
    cargarPacientesFiltro();
});

async function cargarReportes() {
    const tbody = document.getElementById("tablaReportes");
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="7" class="text-center"><i class="fas fa-spinner fa-spin"></i> Cargando...</td></tr>';

    try {
        const res = await fetch("/api/reportes/profesional", { credentials: "include" });

        if (res.status === 401) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Inicia sesión para ver reportes</td></tr>';
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

        // Tabla principal
        if (!data.success || !data.reportes || data.reportes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3"><i class="fas fa-folder-open me-2"></i>No hay reportes generados aún</td></tr>';
            reportesData = [];
            return;
        }

        reportesData = data.reportes;
        renderizarReportes(reportesData);

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
            <td><span class="badge bg-danger">${r.estado || 'Eliminado'}</span></td>
        </tr>
    `).join('');
}

function renderizarReportes(reportes) {
    const tbody = document.getElementById("tablaReportes");
    if (!tbody) return;

    if (!reportes || reportes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3"><i class="fas fa-folder-open me-2"></i>No hay reportes</td></tr>';
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
                <td><span class="badge bg-${estadoClass}">${r.estado || '—'}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="editarReporte(${r.idReporte})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="eliminarReporte(${r.idReporte})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function getEstadoClass(estado) {
    const map = { 'Completado': 'success', 'Pendiente': 'warning', 'Eliminado': 'danger' };
    return map[estado] || 'secondary';
}

async function cargarPacientesFiltro() {
    const select = document.getElementById("paciente");
    const filtroSelect = document.getElementById("filtroPaciente");
    if (!select && !filtroSelect) return;

    try {
        const res = await fetch("/api/pacientes", { credentials: "include" });
        const data = await res.json();
        if (!data.success || !data.pacientes) return;

        const optionsHTML = '<option value="">Todos los pacientes</option>' +
            data.pacientes.map(p => `<option value="${p.idUsuario}">${p.nombre}</option>`).join('');

        if (select) select.innerHTML = optionsHTML;
        if (filtroSelect) filtroSelect.innerHTML = optionsHTML;
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
    const filtro = document.getElementById("filtroPaciente").value;
    if (!filtro) { renderizarReportes(reportesData); return; }
    renderizarReportes(reportesData.filter(r => r.idPaciente == filtro));
}

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
                renderizarReportes(reportesData);
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