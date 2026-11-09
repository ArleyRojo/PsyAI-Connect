// "Mis calificaciones" en el perfil del profesional (HU-67): promedio y comentarios anónimos.
(function () {
    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function estrellas(n) {
        var redondeo = Math.round(Number(n) || 0);
        return '★'.repeat(redondeo) + '☆'.repeat(5 - redondeo);
    }

    function fecha(iso) {
        var d = new Date(iso);
        return isNaN(d) ? '' : d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
    }

    async function cargar() {
        var resumen = document.getElementById('califResumen');
        var lista = document.getElementById('califLista');
        if (!resumen || !lista) return;
        try {
            var res = await fetch('/api/profesional/calificaciones', { credentials: 'include' });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) {
                lista.innerHTML = '<p class="text-muted small mb-0">' + escapeHtml(data.message || 'No se pudieron cargar tus calificaciones.') + '</p>';
                return;
            }
            if (!data.total) {
                resumen.innerHTML = '';
                lista.innerHTML = '<p class="text-muted small mb-0">Aún no tienes calificaciones. Aparecerán cuando tus pacientes califiquen sus citas completadas.</p>';
                return;
            }
            var promedio = Number(data.promedio).toFixed(1).replace('.', ',');
            resumen.innerHTML =
                '<span class="calif-resumen__numero">' + promedio + '</span>' +
                '<div><div class="calif-estrellas" aria-label="' + promedio + ' de 5 estrellas">' + estrellas(data.promedio) + '</div>' +
                '<div class="calif-resumen__total">' + data.total + (data.total === 1 ? ' calificación' : ' calificaciones') + '</div></div>';
            lista.innerHTML = data.calificaciones.map(function (c) {
                var comentario = c.comentario
                    ? '<p class="calif-item__comentario">' + escapeHtml(c.comentario) + '</p>'
                    : '<p class="calif-item__sin-comentario">Sin comentario</p>';
                return '<div class="calif-item"><div class="calif-item__cabecera">' +
                    '<span class="calif-estrellas">' + estrellas(c.puntuacion) + '</span>' +
                    '<span>' + fecha(c.fecha) + '</span></div>' + comentario + '</div>';
            }).join('');
        } catch (err) {
            console.error(err);
            lista.innerHTML = '<p class="text-muted small mb-0">No se pudo conectar con el servidor.</p>';
        }
    }

    document.addEventListener('DOMContentLoaded', cargar);
})();
