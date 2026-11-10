// Campanita del administrador: muestra los avisos recientes y enlaza a Notificaciones.
// Funciona en el dashboard y en todas las páginas del panel admin.
(function () {
    'use strict';
    var ruta = window.location.pathname;
    if (ruta !== '/admin.dashboard.html' && ruta.indexOf('/aside-admin/') !== 0) return;

    var MAX = 6;
    var URL_TODAS = '/aside-admin/notifications.html';

    function esc(v) {
        return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function crearBoton() {
        // Dashboard: <div class="header-notification">. Otras páginas: <i class="fas fa-bell"> suelto.
        var existente = document.querySelector('.main-header .header-notification');
        var icono = existente ? null : document.querySelector('.main-header .user-info > i.fa-bell');
        if (!existente && !icono) return null;

        var envoltura = document.createElement('div');
        envoltura.className = 'admin-campana';
        envoltura.innerHTML =
            '<button type="button" class="header-notification" aria-haspopup="true" aria-expanded="false" title="Notificaciones">' +
                '<i class="fas fa-bell"></i><span class="notification-dot" hidden></span>' +
            '</button>' +
            '<div class="professional-notification-panel admin-campana__panel" role="dialog" aria-label="Notificaciones" hidden>' +
                '<div class="professional-notification-panel__header"><span>Notificaciones</span>' +
                '<button type="button" class="professional-notification-close" aria-label="Cerrar">&times;</button></div>' +
                '<div class="professional-notification-list"><p class="professional-notification-empty">Cargando...</p></div>' +
                '<a class="admin-campana__todas" href="' + URL_TODAS + '">Ver todas las notificaciones</a>' +
            '</div>';
        (existente || icono).replaceWith(envoltura);
        return envoltura;
    }

    function item(titulo, mensaje, meta, enlace) {
        return '<div class="professional-notification-item">' +
            '<div class="professional-notification-item__title">' + esc(titulo) + '</div>' +
            (mensaje ? '<p class="professional-notification-item__message">' + esc(mensaje) + '</p>' : '') +
            (meta ? '<p class="professional-notification-item__message admin-campana__fecha">' + esc(meta) + '</p>' : '') +
            (enlace ? '<a class="professional-notification-action" href="' + enlace[0] + '">' + esc(enlace[1]) + '</a>' : '') +
            '</div>';
    }

    async function cargar(envoltura) {
        var lista = document.querySelector('.admin-campana__panel .professional-notification-list');
        var html = [];
        try {
            var seg = await fetch('/api/admin/seguridad', { credentials: 'include' }).then(function (r) { return r.ok ? r.json() : null; });
            if (seg && seg.config && seg.config.revisionVencida) {
                html.push(item('Revisión de seguridad pendiente', 'Toca revisar las políticas de seguridad.', '',
                    ['/aside-admin/seguridad.html', 'Revisar ahora']));
            }
            var res = await fetch('/api/admin/notificaciones', { credentials: 'include' });
            var data = await res.json();
            (data.notificaciones || []).slice(0, MAX).forEach(function (n) {
                html.push(item(n.titulo || 'Notificación', n.mensaje, [n.fecha, n.destinatario].filter(Boolean).join(' · ')));
            });
        } catch (e) {
            console.error(e);
        }
        lista.innerHTML = html.length ? html.join('') : '<p class="professional-notification-empty">No hay notificaciones recientes.</p>';
        envoltura.querySelector('.notification-dot').hidden = !html.length;
    }

    document.addEventListener('DOMContentLoaded', function () {
        var envoltura = crearBoton();
        if (!envoltura) return;
        var boton = envoltura.querySelector('.header-notification');
        var panel = envoltura.querySelector('.admin-campana__panel');
        // El encabezado tiene efectos (blur/transform) que atrapan y recortan los elementos fijos:
        // el panel se mueve al <body> para que quede encima de todo.
        document.body.appendChild(panel);

        function ubicar() {
            var caja = boton.getBoundingClientRect();
            panel.style.top = Math.round(caja.bottom + 10) + 'px';
            panel.style.right = Math.max(16, Math.round(window.innerWidth - caja.right)) + 'px';
        }
        window.addEventListener('resize', function () { if (!panel.hidden) ubicar(); });
        window.addEventListener('scroll', function () { if (!panel.hidden) ubicar(); }, true);

        function cerrar() {
            panel.hidden = true;
            boton.setAttribute('aria-expanded', 'false');
        }
        boton.addEventListener('click', function (e) {
            e.stopPropagation();
            var abrir = panel.hidden;
            panel.hidden = !abrir;
            boton.setAttribute('aria-expanded', abrir ? 'true' : 'false');
            if (abrir) { ubicar(); cargar(envoltura); }
        });
        panel.querySelector('.professional-notification-close').addEventListener('click', cerrar);
        document.addEventListener('click', function (e) {
            if (!envoltura.contains(e.target) && !panel.contains(e.target)) cerrar();
        });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') cerrar(); });
        cargar(envoltura);
    });
})();
