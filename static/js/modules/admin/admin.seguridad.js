// Seguridad (admin) — HU-13: cierre por inactividad. HU-23: contraseñas, bloqueo y revisión periódica.
(function () {
    'use strict';

    var MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    var config = null;

    function avisar(tipo, mensaje, titulo) {
        if (window.PsyAIAlerts && typeof window.PsyAIAlerts[tipo] === 'function') {
            window.PsyAIAlerts[tipo](mensaje, titulo);
        } else {
            console.log(mensaje);
        }
    }

    function fecha(iso, conHora) {
        if (!iso) return '';
        var d = new Date(iso);
        var t = d.getDate() + ' ' + MESES[d.getMonth()] + ' ' + d.getFullYear();
        return conHora ? t + ', ' + d.toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' }) : t;
    }

    function $(id) { return document.getElementById(id); }

    // ── Pintar ────────────────────────────────────────────────
    function pintarActualizacion(c) {
        var el = $('ultimaActualizacion');
        el.textContent = c.fechaActualizacion && c.actualizadoPor
            ? 'Última modificación: ' + c.actualizadoPor + ' · ' + fecha(c.fechaActualizacion, true)
            : '';
    }

    function marcarAtajo(valor) {
        document.querySelectorAll('#atajosMinutos [data-minutos]').forEach(function (btn) {
            var activo = Number(btn.dataset.minutos) === Number(valor);
            btn.classList.toggle('btn-primary', activo);
            btn.classList.toggle('btn-outline-primary', !activo);
        });
    }

    function textoPolitica() {
        var partes = ['al menos ' + ($('passMinimo').value || '?') + ' caracteres'];
        if ($('passMayuscula').checked) partes.push('una mayúscula');
        if ($('passNumero').checked) partes.push('un número');
        if ($('passSimbolo').checked) partes.push('un símbolo');
        var ultimo = partes.pop();
        $('textoPolitica').textContent = 'Los usuarios verán: "La contraseña debe tener ' +
            (partes.length ? partes.join(', ') + ' y ' : '') + ultimo + '."';
    }

    function pintarRevision(c) {
        var estado = $('estadoRevision');
        estado.classList.remove('bg-vigente', 'bg-vencida');
        if (c.revisionVencida) {
            estado.textContent = 'Revisión pendiente';
            estado.classList.add('bg-vencida');
            $('textoRevision').textContent = c.fechaUltimaRevision
                ? 'Se vencieron el ' + fecha(c.proximaRevision) + '. Revisa las políticas de esta página y márcalas como revisadas.'
                : 'Aún no se han revisado. Revisa las políticas de esta página y márcalas como revisadas.';
        } else {
            estado.textContent = 'Al día';
            estado.classList.add('bg-vigente');
            $('textoRevision').textContent = 'Última revisión: ' + fecha(c.fechaUltimaRevision) +
                (c.revisadoPor ? ' por ' + c.revisadoPor : '') + '. Próxima: ' + fecha(c.proximaRevision) + '.';
        }
    }

    function pintar(c) {
        config = c;
        var r = c.rangos || {};
        [['minutosInactividad', c.minutosInactividad], ['passMinimo', c.passMinimo], ['intentosMaximos', c.intentosMaximos],
            ['minutosBloqueo', c.minutosBloqueo], ['revisionMeses', c.revisionMeses]].forEach(function (par) {
            var input = $(par[0]);
            input.value = par[1];
            if (r[par[0]]) { input.min = r[par[0]][0]; input.max = r[par[0]][1]; }
        });
        $('passMayuscula').checked = !!c.passMayuscula;
        $('passNumero').checked = !!c.passNumero;
        $('passSimbolo').checked = !!c.passSimbolo;
        marcarAtajo(c.minutosInactividad);
        pintarActualizacion(c);
        pintarRevision(c);
        textoPolitica();
    }

    // ── Guardar ───────────────────────────────────────────────
    function entero(id) {
        var input = $(id);
        var n = Number(input.value);
        if (!Number.isInteger(n) || n < Number(input.min) || n > Number(input.max)) {
            var etiqueta = document.querySelector('label[for="' + id + '"]');
            avisar('warning', (etiqueta ? etiqueta.textContent : id) + ': escribe un número entero entre ' + input.min + ' y ' + input.max + '.', 'Valor no válido');
            input.focus();
            return null;
        }
        return n;
    }

    async function enviar(datos, btn, exito) {
        if (btn) btn.disabled = true;
        try {
            var res = await fetch('/api/admin/seguridad', {
                method: 'PUT',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datos),
            });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) {
                avisar('error', data.message || 'No se pudo guardar.', 'Error');
                return;
            }
            pintar(data.config);
            avisar('success', exito(data.config), 'Guardado');
        } catch (err) {
            console.error(err);
            avisar('error', 'No se pudo conectar con el servidor.', 'Error');
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    function guardarInactividad(e) {
        e.preventDefault();
        var minutos = entero('minutosInactividad');
        if (minutos === null) return;
        enviar({ minutosInactividad: minutos }, $('btnGuardarSeguridad'), function (c) {
            return 'Las sesiones se cerrarán tras ' + c.minutosInactividad + ' minutos sin actividad.';
        });
    }

    function guardarPoliticas() {
        var datos = {};
        var campos = ['passMinimo', 'intentosMaximos', 'minutosBloqueo', 'revisionMeses'];
        for (var i = 0; i < campos.length; i++) {
            var n = entero(campos[i]);
            if (n === null) return;
            datos[campos[i]] = n;
        }
        datos.passMayuscula = $('passMayuscula').checked;
        datos.passNumero = $('passNumero').checked;
        datos.passSimbolo = $('passSimbolo').checked;
        enviar(datos, $('btnGuardarPoliticas'), function () { return 'Políticas de seguridad actualizadas.'; });
    }

    async function marcarRevisadas() {
        var meses = entero('revisionMeses');
        if (meses === null) return;
        var btn = $('btnMarcarRevisadas');
        btn.disabled = true;
        try {
            // Primero guarda la periodicidad si cambió
            if (config && meses !== config.revisionMeses) {
                await fetch('/api/admin/seguridad', {
                    method: 'PUT', credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ revisionMeses: meses }),
                });
            }
            var res = await fetch('/api/admin/seguridad/revisar', { method: 'POST', credentials: 'include' });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) {
                avisar('error', data.message || 'No se pudo marcar la revisión.', 'Error');
                return;
            }
            pintar(data.config);
            avisar('success', 'Próxima revisión: ' + fecha(data.config.proximaRevision) + '.', 'Políticas revisadas');
        } catch (err) {
            console.error(err);
            avisar('error', 'No se pudo conectar con el servidor.', 'Error');
        } finally {
            btn.disabled = false;
        }
    }

    async function cargar() {
        try {
            var res = await fetch('/api/admin/seguridad', { credentials: 'include' });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) throw new Error(data.message || 'Error ' + res.status);
            pintar(data.config);
        } catch (err) {
            console.error(err);
            avisar('error', 'No se pudo cargar la configuración de seguridad.', 'Error');
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        $('formSeguridad').addEventListener('submit', guardarInactividad);
        $('minutosInactividad').addEventListener('input', function () { marcarAtajo(this.value); });
        $('atajosMinutos').addEventListener('click', function (e) {
            var btn = e.target.closest('[data-minutos]');
            if (!btn) return;
            $('minutosInactividad').value = btn.dataset.minutos;
            marcarAtajo(btn.dataset.minutos);
        });
        ['passMinimo', 'passMayuscula', 'passNumero', 'passSimbolo'].forEach(function (id) {
            $(id).addEventListener('input', textoPolitica);
            $(id).addEventListener('change', textoPolitica);
        });
        $('btnGuardarPoliticas').addEventListener('click', guardarPoliticas);
        $('btnMarcarRevisadas').addEventListener('click', marcarRevisadas);
        cargar();
    });
})();
