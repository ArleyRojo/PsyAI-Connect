// Mis consejos (HU-68): el paciente ve los consejos de su profesional y los marca como completados.
(function () {
    var consejos = [];
    var filtro = 'todos';

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function aviso(tipo, mensaje) {
        if (window.mostrarToast) window.mostrarToast(mensaje, tipo);
    }

    function formatearFecha(iso) {
        if (!iso) return '';
        var d = new Date(iso);
        return isNaN(d) ? '' : d.toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' });
    }

    function render() {
        var lista = document.getElementById('consejos-lista');
        var contador = document.getElementById('consejos-count');
        var pendientes = consejos.filter(function (c) { return !c.completado; }).length;
        if (contador) contador.textContent = pendientes + (pendientes === 1 ? ' pendiente' : ' pendientes');

        var visibles = consejos.filter(function (c) {
            if (filtro === 'pendientes') return !c.completado;
            if (filtro === 'completados') return c.completado;
            return true;
        });

        if (!consejos.length) {
            lista.innerHTML = '<p class="consejos-vacio"><i class="fas fa-lightbulb me-2"></i>Todavía no tienes consejos. Cuando tu profesional te envíe uno, aparecerá aquí.</p>';
            return;
        }
        if (!visibles.length) {
            lista.innerHTML = '<p class="consejos-vacio">No hay consejos en este filtro.</p>';
            return;
        }

        lista.innerHTML = visibles.map(function (c) {
            var boton = c.completado
                ? '<button type="button" class="consejo-btn consejo-btn--deshacer" data-id="' + Number(c.idConsejo) + '" data-completado="false"><i class="fas fa-rotate-left"></i> Marcar como pendiente</button>'
                : '<button type="button" class="consejo-btn" data-id="' + Number(c.idConsejo) + '" data-completado="true"><i class="fas fa-check"></i> Marcar como completado</button>';
            return '<article class="consejo-item' + (c.completado ? ' consejo-item--hecho' : '') + '">' +
                '<div class="consejo-item__cabecera">' +
                    '<h3 class="consejo-item__titulo">' + escapeHtml(c.titulo) + '</h3>' +
                    '<span class="consejo-estado' + (c.completado ? ' consejo-estado--hecho' : '') + '">' + (c.completado ? 'Completado' : 'Pendiente') + '</span>' +
                '</div>' +
                '<p class="consejo-item__texto">' + escapeHtml(c.descripcion) + '</p>' +
                '<div class="consejo-item__pie">' +
                    '<span><i class="fas fa-user-doctor me-1"></i>' + escapeHtml(c.profesional) + ' · ' + formatearFecha(c.fecha) + '</span>' +
                    boton +
                '</div>' +
            '</article>';
        }).join('');
    }

    async function cargar() {
        var lista = document.getElementById('consejos-lista');
        try {
            var res = await fetch('/api/paciente/consejos', { credentials: 'include' });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) {
                lista.innerHTML = '<p class="consejos-vacio">' + escapeHtml(data.message || 'No se pudieron cargar tus consejos.') + '</p>';
                return;
            }
            consejos = data.consejos || [];
            render();
        } catch (err) {
            console.error(err);
            lista.innerHTML = '<p class="consejos-vacio">No se pudo conectar con el servidor.</p>';
        }
    }

    async function marcar(boton) {
        var id = Number(boton.dataset.id);
        var completado = boton.dataset.completado === 'true';
        boton.disabled = true;
        try {
            var res = await fetch('/api/paciente/consejos/' + id, {
                method: 'PATCH',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ completado: completado }),
            });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) {
                aviso('danger', data.message || 'No se pudo actualizar el consejo.');
                boton.disabled = false;
                return;
            }
            consejos = consejos.map(function (c) {
                return c.idConsejo === id ? Object.assign({}, c, data.consejo) : c;
            });
            render();
            aviso('success', data.message);
        } catch (err) {
            console.error(err);
            aviso('danger', 'No se pudo conectar con el servidor.');
            boton.disabled = false;
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.getElementById('consejos-lista').addEventListener('click', function (e) {
            var boton = e.target.closest('.consejo-btn');
            if (boton) marcar(boton);
        });
        document.querySelectorAll('.consejos-filtro').forEach(function (btn) {
            btn.addEventListener('click', function () {
                document.querySelectorAll('.consejos-filtro').forEach(function (b) { b.classList.remove('active'); });
                btn.classList.add('active');
                filtro = btn.dataset.filtro;
                render();
            });
        });
        cargar();
    });
})();
