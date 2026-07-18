let _prevValues = {};

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? '—';
}

function toggleClass(id, cls, add) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle(cls, add);
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function csvCell(value) {
    return `"${String(value ?? '').replace(/"/g, '""')}"`;
}

function estadoPorValor(valor) {
    if (valor >= 82) return 'critical';
    if (valor >= 66) return 'warning';
    return 'stable';
}

function etiquetaEstado(valor) {
    const estado = typeof valor === 'string' ? valor : estadoPorValor(valor);
    if (estado === 'critical') return 'crítico';
    if (estado === 'warning') return 'advertencia';
    return 'estable';
}

function fechaLog(valor) {
    if (!valor) return 0;
    const directa = Date.parse(valor);
    if (!Number.isNaN(directa)) return directa;
    const match = String(valor).match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?/);
    if (!match) return 0;
    const [, dia, mes, anio, hora = '00', minuto = '00'] = match;
    return new Date(Number(anio), Number(mes) - 1, Number(dia), Number(hora), Number(minuto)).getTime();
}

function exportCSV(filename, headers, rows) {
    const bom = '\uFEFF';
    const csv = bom + headers.join(',') + '\n' + rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}
