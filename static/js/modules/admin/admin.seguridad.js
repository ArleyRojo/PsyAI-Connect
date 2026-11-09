// Seguridad (admin) — HU-13: minutos de inactividad antes de cerrar la sesión.
(function () {
    'use strict';

    var MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

    function avisar(tipo, mensaje, titulo) {
        if (window.PsyAIAlerts && typeof window.PsyAIAlerts[tipo] === 'function') {
            window.PsyAIAlerts[tipo](mensaje, titulo);
        } else {
            console.log(mensaje);
        }
    }

    function pintarActualizacion(config) {
        var el = document.getElementById('ultimaActualizacion');
        if (!config.fechaActualizacion || !config.actualizadoPor) {
            el.textContent = '';
            return;
        }
        var d = new Date(config.fechaActualizacion);
        var hora = d.toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' });
        el.textContent = 'Última modificación: ' + config.actualizadoPor + ' · ' +
            d.getDate() + ' ' + MESES[d.getMonth()] + ' ' + d.getFullYear() + ', ' + hora;
    }

    function marcarAtajo(valor) {
        document.querySelectorAll('#atajosMinutos [data-minutos]').forEach(function (btn) {
            var activo = Number(btn.dataset.minutos) === Number(valor);
            btn.classList.toggle('btn-primary', activo);
            btn.classList.toggle('btn-outline-primary', !activo);
        });
    }

    async function cargar() {
        try {
            var res = await fetch('/api/admin/seguridad', { credentials: 'include' });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) throw new Error(data.message || 'Error ' + res.status);
            var input = document.getElementById('minutosInactividad');
            input.value = data.config.minutosInactividad;
            input.min = data.config.minutosMin;
            input.max = data.config.minutosMax;
            marcarAtajo(input.value);
            pintarActualizacion(data.config);
        } catch (err) {
            console.error(err);
            avisar('error', 'No se pudo cargar la configuración de seguridad.', 'Error');
        }
    }

    async function guardar(e) {
        e.preventDefault();
        var input = document.getElementById('minutosInactividad');
        var minutos = Number(input.value);
        if (!Number.isInteger(minutos) || minutos < Number(input.min) || minutos > Number(input.max)) {
            avisar('warning', 'Escribe un número entero entre ' + input.min + ' y ' + input.max + ' minutos.', 'Valor no válido');
            input.focus();
            return;
        }

        var btn = document.getElementById('btnGuardarSeguridad');
        btn.disabled = true;
        try {
            var res = await fetch('/api/admin/seguridad', {
                method: 'PUT',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ minutosInactividad: minutos }),
            });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) {
                avisar('error', data.message || 'No se pudo guardar.', 'Error');
                return;
            }
            pintarActualizacion(data.config);
            marcarAtajo(data.config.minutosInactividad);
            avisar('success', 'Las sesiones se cerrarán tras ' + data.config.minutosInactividad + ' minutos sin actividad.', 'Guardado');
        } catch (err) {
            console.error(err);
            avisar('error', 'No se pudo conectar con el servidor.', 'Error');
        } finally {
            btn.disabled = false;
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.getElementById('formSeguridad').addEventListener('submit', guardar);
        document.getElementById('minutosInactividad').addEventListener('input', function () { marcarAtajo(this.value); });
        document.getElementById('atajosMinutos').addEventListener('click', function (e) {
            var btn = e.target.closest('[data-minutos]');
            if (!btn) return;
            document.getElementById('minutosInactividad').value = btn.dataset.minutos;
            marcarAtajo(btn.dataset.minutos);
        });
        cargar();
    });
})();
