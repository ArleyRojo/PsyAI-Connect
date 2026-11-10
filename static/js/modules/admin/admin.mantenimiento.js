// Mantenimiento (admin) — HU-24 estado y acciones, HU-30/31 copias de seguridad.
(function () {
    'use strict';

    var MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    var TARJETAS = [
        ['baseDatos', 'Base de datos', 'fa-database'],
        ['correo', 'Correo', 'fa-envelope'],
        ['disco', 'Disco', 'fa-hard-drive'],
        ['programador', 'Programador de tareas', 'fa-clock-rotate-left'],
        ['migraciones', 'Migraciones', 'fa-code-branch'],
        ['copias', 'Copias de seguridad', 'fa-shield-halved'],
    ];
    var modalRestaurar = null;
    var copiaElegida = null;

    function $(id) { return document.getElementById(id); }

    function esc(v) {
        return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function avisar(tipo, mensaje, titulo) {
        if (window.PsyAIAlerts && typeof window.PsyAIAlerts[tipo] === 'function') window.PsyAIAlerts[tipo](mensaje, titulo);
        else console.log(mensaje);
    }

    function fecha(iso) {
        var d = new Date(iso);
        return d.getDate() + ' ' + MESES[d.getMonth()] + ' ' + d.getFullYear() + ', ' +
            d.toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' });
    }

    function tamano(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1024 / 1024).toFixed(1) + ' MB';
    }

    async function api(url, opciones) {
        var res = await fetch(url, Object.assign({ credentials: 'include' }, opciones || {}));
        var data = await res.json().catch(function () { return {}; });
        if (!res.ok || !data.success) throw new Error(data.message || 'Error ' + res.status);
        return data;
    }

    function enviarJSON(metodo, cuerpo) {
        return { method: metodo, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo || {}) };
    }

    // ── Pestañas ──────────────────────────────────────────────
    function mostrarTab(tab) {
        ['estado', 'copias'].forEach(function (t) { $('tab-' + t).style.display = t === tab ? '' : 'none'; });
        document.querySelectorAll('.admin-panel-tab').forEach(function (b) {
            var activa = b.dataset.tab === tab;
            b.classList.toggle('active', activa);
            b.setAttribute('aria-selected', activa ? 'true' : 'false');
        });
    }

    // ── Estado ────────────────────────────────────────────────
    function pintarModo(config) {
        $('switchMantenimiento').checked = !!config.modoMantenimiento;
        if (document.activeElement !== $('mensajeMantenimiento')) $('mensajeMantenimiento').value = config.mensajeMantenimiento || '';
        var el = $('estadoModo');
        el.className = 'mant-modo-estado mt-3 ' + (config.modoMantenimiento ? 'mant-modo-estado--activo' : 'mant-modo-estado--inactivo');
        el.innerHTML = config.modoMantenimiento
            ? '<i class="fas fa-triangle-exclamation me-1"></i>Activo: los usuarios ven el aviso de mantenimiento.'
            : '<i class="fas fa-circle-check me-1"></i>Inactivo: la plataforma funciona normal.';
    }

    async function cargarEstado() {
        try {
            var data = await api('/api/admin/mantenimiento');
            $('estadoSistema').innerHTML = TARJETAS.map(function (t) {
                var e = data.estado[t[0]] || {};
                return '<div class="mant-tarjeta mant-tarjeta--' + esc(e.estado) + '">' +
                    '<i class="fas ' + t[2] + '"></i><div>' +
                    '<div class="mant-tarjeta__nombre">' + esc(t[1]) + '</div>' +
                    '<div class="mant-tarjeta__texto">' + esc(e.texto) + '</div>' +
                    '<div class="mant-tarjeta__detalle">' + esc(e.detalle) + '</div></div></div>';
            }).join('');
            pintarModo(data.config);
        } catch (err) {
            $('estadoSistema').innerHTML = '<p class="text-danger">No se pudo revisar el estado del sistema.</p>';
        }
    }

    async function cambiarModo() {
        var sw = $('switchMantenimiento');
        var activo = sw.checked;
        if (activo && window.Swal) {
            var r = await Swal.fire({
                title: '¿Activar el modo mantenimiento?',
                text: 'Pacientes y profesionales no podrán usar la plataforma hasta que lo desactives.',
                icon: 'warning', showCancelButton: true,
                confirmButtonText: 'Sí, activar', cancelButtonText: 'Cancelar',
            });
            if (!r.isConfirmed) { sw.checked = false; return; }
        }
        sw.disabled = true;
        try {
            var data = await api('/api/admin/mantenimiento/modo',
                enviarJSON('PUT', { activo: activo, mensaje: $('mensajeMantenimiento').value.trim() }));
            pintarModo(data.config);
            avisar(activo ? 'warning' : 'success', data.message, activo ? 'Mantenimiento activo' : 'Mantenimiento terminado');
        } catch (err) {
            sw.checked = !activo;
            avisar('error', err.message, 'Error');
        } finally {
            sw.disabled = false;
        }
    }

    async function ejecutar(btn) {
        if (btn.dataset.confirmar && window.Swal) {
            var r = await Swal.fire({
                title: '¿Continuar?', text: btn.dataset.confirmar, icon: 'question',
                showCancelButton: true, confirmButtonText: 'Sí', cancelButtonText: 'Cancelar',
            });
            if (!r.isConfirmed) return;
        }
        btn.disabled = true;
        var salida = $('resultadoAccion');
        try {
            var data = await api('/api/admin/mantenimiento/accion', enviarJSON('POST', { accion: btn.dataset.accion }));
            salida.hidden = false;
            salida.textContent = btn.textContent.trim() + ':\n' + data.message;
            avisar('success', data.message.split('\n')[0], 'Listo');
            cargarEstado();
        } catch (err) {
            avisar('error', err.message, 'Error');
        } finally {
            btn.disabled = false;
        }
    }

    // ── Copias ────────────────────────────────────────────────
    async function cargarCopias() {
        var tbody = $('tablaCopias');
        try {
            var data = await api('/api/admin/copias');
            $('cntCopias').textContent = data.copias.length;
            $('maxCopias').textContent = data.maxCopias;
            if (document.activeElement !== $('horaCopia')) $('horaCopia').value = data.horaCopia;
            tbody.innerHTML = data.copias.length ? data.copias.map(function (c) {
                return '<tr>' +
                    '<td>' + esc(fecha(c.fecha)) + '</td>' +
                    '<td><span class="mant-tipo mant-tipo--' + esc(c.clave) + '">' + esc(c.tipo) + '</span></td>' +
                    '<td>' + esc(tamano(c.tamano)) + '</td>' +
                    '<td><code>' + esc(c.archivo) + '</code></td>' +
                    '<td class="text-end"><button type="button" class="btn btn-outline-danger btn-sm" data-restaurar="' +
                    esc(c.archivo) + '" data-fecha="' + esc(fecha(c.fecha)) + '"><i class="fas fa-rotate-left me-1"></i>Restaurar</button></td>' +
                    '</tr>';
            }).join('') : '<tr><td colspan="5" class="text-center text-muted py-4">Aún no hay copias. Crea la primera.</td></tr>';
        } catch (err) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger py-4">No se pudieron cargar las copias.</td></tr>';
        }
    }

    async function crearCopia() {
        var btn = $('btnCrearCopia');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Creando...';
        try {
            var data = await api('/api/admin/copias', { method: 'POST' });
            avisar('success', data.copia.archivo, 'Copia creada');
            cargarCopias();
            cargarEstado();
        } catch (err) {
            avisar('error', err.message, 'Error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-plus me-1"></i>Crear copia ahora';
        }
    }

    async function guardarHora() {
        try {
            var data = await api('/api/admin/copias/hora', enviarJSON('PUT', { hora: $('horaCopia').value }));
            avisar('success', data.message, 'Guardado');
        } catch (err) {
            avisar('error', err.message, 'Error');
        }
    }

    function abrirRestaurar(btn) {
        copiaElegida = btn.dataset.restaurar;
        $('restaurarFecha').textContent = btn.dataset.fecha;
        $('confirmarRestaurar').value = '';
        $('btnConfirmarRestaurar').disabled = true;
        modalRestaurar.show();
    }

    async function restaurar() {
        var btn = $('btnConfirmarRestaurar');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Restaurando...';
        try {
            var data = await api('/api/admin/copias/restaurar',
                enviarJSON('POST', { archivo: copiaElegida, confirmacion: $('confirmarRestaurar').value.trim() }));
            modalRestaurar.hide();
            avisar('success', data.message, 'Datos restaurados');
            cargarCopias();
            cargarEstado();
        } catch (err) {
            avisar('error', err.message, 'No se restauró');
            btn.disabled = false;
        } finally {
            btn.innerHTML = '<i class="fas fa-rotate-left me-1"></i>Restaurar';
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        modalRestaurar = new bootstrap.Modal($('modalRestaurar'));
        document.querySelectorAll('.admin-panel-tab').forEach(function (b) {
            b.addEventListener('click', function () { mostrarTab(b.dataset.tab); });
        });
        $('switchMantenimiento').addEventListener('change', cambiarModo);
        document.querySelectorAll('[data-accion]').forEach(function (b) {
            b.addEventListener('click', function () { ejecutar(b); });
        });
        $('btnCrearCopia').addEventListener('click', crearCopia);
        $('btnGuardarHora').addEventListener('click', guardarHora);
        $('tablaCopias').addEventListener('click', function (e) {
            var btn = e.target.closest('[data-restaurar]');
            if (btn) abrirRestaurar(btn);
        });
        $('confirmarRestaurar').addEventListener('input', function () {
            $('btnConfirmarRestaurar').disabled = this.value.trim() !== 'RESTAURAR';
        });
        $('btnConfirmarRestaurar').addEventListener('click', restaurar);
        cargarEstado();
        cargarCopias();
        setInterval(cargarEstado, 60000);
    });
})();
