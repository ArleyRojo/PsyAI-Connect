// Aviso en el dashboard del admin cuando toca revisar las políticas de seguridad (HU-23, RN-14).
(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        fetch('/api/admin/seguridad', { credentials: 'include' })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                if (!data || !data.success || !data.config.revisionVencida) return;
                var main = document.querySelector('main.main-content');
                if (!main) return;
                var aviso = document.createElement('div');
                aviso.className = 'alert alert-warning d-flex flex-wrap align-items-center justify-content-between gap-2 mb-4';
                aviso.setAttribute('role', 'alert');
                aviso.innerHTML =
                    '<span><i class="fas fa-clipboard-check me-2"></i><strong>Revisión de seguridad pendiente.</strong> ' +
                    'Toca revisar las políticas de seguridad y privacidad.</span>' +
                    '<a class="btn btn-sm btn-warning" href="./aside-admin/seguridad.html">Revisar ahora</a>';
                var header = main.querySelector('header');
                if (header && header.nextSibling) main.insertBefore(aviso, header.nextSibling);
                else main.prepend(aviso);
            })
            .catch(function () {});
    });
})();
