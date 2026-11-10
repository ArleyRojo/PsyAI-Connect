// Muestra en el menú lateral el nombre del rol del usuario, incluido su rol personalizado (HU-11).
(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        var etiquetas = document.querySelectorAll('.sidebar__role-badge, .sidebar__user-role');
        if (!etiquetas.length) return;
        fetch('/api/session', { credentials: 'include' })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                var nombre = data && data.usuario && data.usuario.rolNombre;
                if (!nombre) return;
                etiquetas.forEach(function (el) { el.textContent = nombre; });
            })
            .catch(function () {});
    });
})();
