// Calificar la atención de una cita completada (HU-67).
(function () {
    var TEXTOS = ['', 'Muy mala', 'Mala', 'Regular', 'Buena', 'Excelente'];
    var citaActual = null;
    var puntuacion = 0;
    var modal = null;

    function pintarEstrellas(valor) {
        document.querySelectorAll('#calificarEstrellas .calificar-estrella').forEach(function (btn) {
            var activa = Number(btn.dataset.valor) <= valor;
            btn.classList.toggle('activa', activa);
            btn.setAttribute('aria-checked', Number(btn.dataset.valor) === valor ? 'true' : 'false');
        });
        document.getElementById('calificarTexto').textContent = valor ? TEXTOS[valor] : 'Elige de 1 a 5 estrellas';
        document.getElementById('btnGuardarCalificacion').disabled = !valor;
    }

    function actualizarContador() {
        var area = document.getElementById('calificarComentario');
        document.getElementById('calificarContador').textContent = area.value.length + '/500';
    }

    window.abrirCalificacion = function (idCita) {
        var cita = (window._citasPorId || {})[Number(idCita)];
        if (!cita) return;
        citaActual = cita;
        puntuacion = cita.calificacion ? Number(cita.calificacion.puntuacion) : 0;
        document.getElementById('calificarDetalle').textContent =
            (cita.profesional || 'Tu profesional') + ' · ' + cita.fecha;
        document.getElementById('calificarComentario').value = cita.calificacion ? (cita.calificacion.comentario || '') : '';
        actualizarContador();
        pintarEstrellas(puntuacion);

        // Si el historial está abierto, se cierra para no apilar dos ventanas.
        var historial = document.getElementById('modalHistorialCitasPaciente');
        var instHistorial = historial && window.bootstrap ? bootstrap.Modal.getInstance(historial) : null;
        if (instHistorial) instHistorial.hide();
        modal.show();
    };

    async function guardar() {
        if (!citaActual || !puntuacion) return;
        var btn = document.getElementById('btnGuardarCalificacion');
        btn.disabled = true;
        try {
            var res = await fetch('/api/citas/' + Number(citaActual.idCita) + '/calificacion', {
                method: 'PUT',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    puntuacion: puntuacion,
                    comentario: document.getElementById('calificarComentario').value.trim(),
                }),
            });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) {
                if (window.mostrarToast) window.mostrarToast(data.message || 'No se pudo guardar la calificación.', 'danger');
                btn.disabled = false;
                return;
            }
            citaActual.calificacion = { puntuacion: data.calificacion.puntuacion, comentario: data.calificacion.comentario };
            modal.hide();
            if (window.mostrarToast) window.mostrarToast(data.message, 'success');
            if (typeof cargarCitasPaciente === 'function') cargarCitasPaciente();
        } catch (err) {
            console.error(err);
            if (window.mostrarToast) window.mostrarToast('No se pudo conectar con el servidor.', 'danger');
            btn.disabled = false;
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var el = document.getElementById('modalCalificar');
        if (!el || !window.bootstrap) return;
        modal = new bootstrap.Modal(el);
        document.getElementById('calificarEstrellas').addEventListener('click', function (e) {
            var btn = e.target.closest('.calificar-estrella');
            if (!btn) return;
            puntuacion = Number(btn.dataset.valor);
            pintarEstrellas(puntuacion);
        });
        document.getElementById('calificarComentario').addEventListener('input', actualizarContador);
        document.getElementById('btnGuardarCalificacion').addEventListener('click', guardar);
    });
})();
