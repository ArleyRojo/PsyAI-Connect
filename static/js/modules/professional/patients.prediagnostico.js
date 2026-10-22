var prediagnosticosData = window.prediagnosticosData || [];

function escapeHtmlPrediag(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function getRiesgoColorPrediag(nivel) {
    switch ((nivel || '').toLowerCase()) {
        case 'critico': return 'dark';
        case 'alto': return 'danger';
        case 'moderado': return 'warning';
        default: return 'success';
    }
}

async function cargarPrediagnosticos() {
    var tbody = document.getElementById("tablaPrediagnosticos");
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3"><i class="fas fa-spinner fa-spin me-2"></i>Cargando...</td></tr>';

    try {
        var res = await fetch("/api/prediagnosticos/profesional", { credentials: "include" });
        var data = await res.json();
        window.prediagnosticosData = prediagnosticosData = (data.success && data.prediagnosticos) ? data.prediagnosticos : [];
        actualizarBadgePrediag();
        renderPrediagnosticos(prediagnosticosData);
    } catch (e) {
        console.error(e);
        prediagnosticosData = [];
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error al cargar los prediagnósticos</td></tr>';
    }
}

function renderPrediagnosticos(lista) {
    var tbody = document.getElementById("tablaPrediagnosticos");
    if (!tbody) return;

    if (!lista || !lista.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No hay prediagnósticos generados aún</td></tr>';
        return;
    }

    tbody.innerHTML = lista.map(function (p) {
        var fecha = (typeof formatearFecha === 'function' ? formatearFecha(p.fecha) : null) || p.fecha || '—';
        var color = getRiesgoColorPrediag(p.nivelRiesgo);
        var urgente = p.requiereAtencionUrgente ? ' <span class="badge bg-danger">Urgente</span>' : '';
        var areas = (p.posiblesAreas || []).join(', ') || '—';

        return "<tr>" +
            "<td>" + escapeHtmlPrediag(fecha) + "</td>" +
            "<td>" + escapeHtmlPrediag(p.paciente || '—') + "</td>" +
            "<td><span class='badge bg-" + color + "'>" + escapeHtmlPrediag(p.nivelRiesgo || '—') + "</span>" + urgente + "</td>" +
            "<td>" + escapeHtmlPrediag(areas) + "</td>" +
            "<td>" + escapeHtmlPrediag(p.resumenProfesional || '—') + "</td>" +
            "</tr>";
    }).join('');
}

function actualizarBadgePrediag() {
    var badge = document.getElementById("badgePrediag");
    if (badge) badge.textContent = prediagnosticosData.length;
}