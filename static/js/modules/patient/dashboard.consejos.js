// Tarjeta "Consejos de tu profesional" del dashboard del paciente (HU-54): muestra hasta 3 pendientes.
(function () {
    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    async function cargar() {
        var contenedor = document.getElementById('dashConsejos');
        if (!contenedor) return;
        try {
            var res = await fetch('/api/paciente/consejos', { credentials: 'include' });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) {
                contenedor.innerHTML = '<p class="dash-tip-v2__text">No se pudieron cargar tus consejos.</p>';
                return;
            }
            var pendientes = (data.consejos || []).filter(function (c) { return !c.completado; }).slice(0, 3);
            if (!pendientes.length) {
                contenedor.innerHTML = '<p class="dash-tip-v2__text">No tienes consejos pendientes.</p>';
                return;
            }
            contenedor.innerHTML = pendientes.map(function (c) {
                return '<div class="dash-consejos__item"><i class="fas fa-lightbulb"></i><div>' +
                    '<div class="dash-consejos__titulo">' + escapeHtml(c.titulo) + '</div>' +
                    '<div class="dash-consejos__autor">' + escapeHtml(c.profesional) + '</div>' +
                    '</div></div>';
            }).join('');
        } catch (err) {
            console.error(err);
            contenedor.innerHTML = '<p class="dash-tip-v2__text">No se pudo conectar con el servidor.</p>';
        }
    }

    document.addEventListener('DOMContentLoaded', cargar);
})();
