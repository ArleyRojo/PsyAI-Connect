// Asignaciones (admin) — HU-57 asignar y HU-58 reasignar pacientes a profesionales.
(function () {
    'use strict';

    var MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    var datos = { pacientes: [], profesionales: [] };
    var accion = null; // { modo: 'asignar'|'reasignar', paciente, actual }
    var modal = null;

    function esc(v) {
        return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function fecha(iso, conHora) {
        if (!iso) return '—';
        var d = new Date(iso);
        if (isNaN(d)) return '—';
        var t = d.getDate() + ' ' + MESES[d.getMonth()] + ' ' + d.getFullYear();
        return conHora ? t + ', ' + d.toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' }) : t;
    }

    function avisar(tipo, mensaje, titulo) {
        if (window.PsyAIAlerts && typeof window.PsyAIAlerts[tipo] === 'function') window.PsyAIAlerts[tipo](mensaje, titulo);
        else console.log(mensaje);
    }

    // ── Pestañas ──────────────────────────────────────────────
    function mostrarTab(tab) {
        ['pacientes', 'historial'].forEach(function (t) {
            document.getElementById('tab-' + t).style.display = t === tab ? '' : 'none';
        });
        document.querySelectorAll('.admin-panel-tab').forEach(function (b) {
            var activa = b.dataset.tab === tab;
            b.classList.toggle('active', activa);
            b.setAttribute('aria-selected', activa ? 'true' : 'false');
        });
    }

    // ── Pacientes ─────────────────────────────────────────────
    function filaPaciente(p) {
        var profesionales = p.profesionales.length
            ? p.profesionales.map(function (pr) {
                var meta = 'Desde ' + fecha(pr.desde) + (pr.citasFuturas ? ' · ' + pr.citasFuturas + ' cita(s) próxima(s)' : '');
                return '<div class="asig-profesional">' +
                    '<div><div class="asig-profesional__nombre">' + esc(pr.nombre) + '</div>' +
                    '<div class="asig-profesional__meta">' + esc(meta) + '</div></div>' +
                    '<button type="button" class="btn btn-outline-primary btn-sm" data-reasignar="' + Number(p.idPaciente) +
                    '" data-profesional="' + Number(pr.idProfesional) + '"><i class="fas fa-people-arrows me-1"></i>Reasignar</button>' +
                    '</div>';
            }).join('')
            : '<span class="asig-sin"><i class="fas fa-triangle-exclamation me-1"></i>Sin profesional</span>';

        var acciones = p.profesionales.length ? '' :
            '<button type="button" class="btn btn-primary btn-sm" data-asignar="' + Number(p.idPaciente) +
            '"><i class="fas fa-user-plus me-1"></i>Asignar</button>';

        return '<tr>' +
            '<td><div class="asig-paciente"><strong>' + esc(p.nombre) + '</strong><small>' + esc(p.email) + '</small></div></td>' +
            '<td>' + profesionales + '</td>' +
            '<td class="text-end">' + acciones + '</td>' +
            '</tr>';
    }

    function pintarPacientes() {
        var texto = document.getElementById('buscarPaciente').value.trim().toLowerCase();
        var filtro = document.getElementById('filtroAsignacion').value;
        var lista = datos.pacientes.filter(function (p) {
            if (filtro === 'sin' && p.profesionales.length) return false;
            if (filtro === 'con' && !p.profesionales.length) return false;
            if (!texto) return true;
            var buscable = [p.nombre, p.email].concat(p.profesionales.map(function (x) { return x.nombre; })).join(' ').toLowerCase();
            return buscable.indexOf(texto) !== -1;
        });
        document.getElementById('tablaAsignaciones').innerHTML = lista.length
            ? lista.map(filaPaciente).join('')
            : '<tr><td colspan="3" class="text-center text-muted py-4">No hay pacientes que coincidan.</td></tr>';
        document.getElementById('cntPacientes').textContent = datos.pacientes.length;
        document.getElementById('cntSinProfesional').textContent =
            datos.pacientes.filter(function (p) { return !p.profesionales.length; }).length;
    }

    async function cargarPacientes() {
        try {
            var res = await fetch('/api/admin/asignaciones', { credentials: 'include' });
            var json = await res.json().catch(function () { return {}; });
            if (!res.ok || !json.success) throw new Error(json.message || 'Error ' + res.status);
            datos = json;
            pintarPacientes();
        } catch (err) {
            console.error(err);
            document.getElementById('tablaAsignaciones').innerHTML =
                '<tr><td colspan="3" class="text-center text-danger py-4">No se pudieron cargar las asignaciones.</td></tr>';
        }
    }

    // ── Historial ─────────────────────────────────────────────
    async function cargarHistorial() {
        var tbody = document.getElementById('tablaHistorial');
        try {
            var res = await fetch('/api/admin/asignaciones/historial', { credentials: 'include' });
            var json = await res.json().catch(function () { return {}; });
            if (!res.ok || !json.success) throw new Error(json.message || 'Error ' + res.status);
            document.getElementById('cntHistorial').textContent = json.historial.length;
            tbody.innerHTML = json.historial.length ? json.historial.map(function (h) {
                var esAsignacion = h.tipo === 'Asignación';
                return '<tr>' +
                    '<td>' + esc(fecha(h.fecha, true)) + '</td>' +
                    '<td><span class="asig-tipo' + (esAsignacion ? ' asig-tipo--asignacion' : '') + '">' + esc(h.tipo) + '</span></td>' +
                    '<td>' + esc(h.paciente || '—') + '</td>' +
                    '<td>' + esc(h.profesionalAnterior || '—') + '</td>' +
                    '<td>' + esc(h.profesionalNuevo || '—') + '</td>' +
                    '<td class="asig-motivo">' + esc(h.motivo) + '</td>' +
                    '<td>' + Number(h.citasCanceladas || 0) + '</td>' +
                    '<td>' + esc(h.administrador || '—') + '</td>' +
                    '</tr>';
            }).join('') : '<tr><td colspan="8" class="text-center text-muted py-4">Todavía no hay asignaciones ni reasignaciones.</td></tr>';
        } catch (err) {
            console.error(err);
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger py-4">No se pudo cargar el historial.</td></tr>';
        }
    }

    // ── Modal ─────────────────────────────────────────────────
    function abrirModal(modo, idPaciente, idActual) {
        var paciente = datos.pacientes.find(function (p) { return p.idPaciente === idPaciente; });
        if (!paciente) return;
        var actual = idActual ? paciente.profesionales.find(function (x) { return x.idProfesional === idActual; }) : null;
        accion = { modo: modo, paciente: paciente, actual: actual };

        var esReasignar = modo === 'reasignar';
        document.getElementById('modalAsignacionTitulo').textContent = esReasignar ? 'Reasignar caso' : 'Asignar profesional';
        document.getElementById('asigPaciente').textContent = paciente.nombre;
        document.getElementById('asigActualWrap').style.display = esReasignar ? '' : 'none';
        document.getElementById('asigActual').textContent = actual ? actual.nombre : '';
        document.getElementById('asigNuevoLabel').textContent = esReasignar ? 'Nuevo profesional' : 'Profesional';
        document.getElementById('btnConfirmarAsignacion').innerHTML = esReasignar
            ? '<i class="fas fa-people-arrows me-1"></i>Reasignar'
            : '<i class="fas fa-user-plus me-1"></i>Asignar';

        var opciones = datos.profesionales.filter(function (pr) {
            return !paciente.profesionales.some(function (x) { return x.idProfesional === pr.idProfesional; });
        });
        var select = document.getElementById('asigNuevo');
        select.innerHTML = '<option value="">Selecciona un profesional...</option>' + opciones.map(function (pr) {
            var extra = [pr.especialidad, pr.pacientes + ' paciente(s)'].filter(Boolean).join(' · ');
            return '<option value="' + Number(pr.idProfesional) + '">' + esc(pr.nombre + ' — ' + extra) + '</option>';
        }).join('');

        document.getElementById('asigMotivo').value = '';
        document.getElementById('asigContador').textContent = '0/500';
        pintarAviso();
        modal.show();
    }

    function pintarAviso() {
        var aviso = document.getElementById('asigAviso');
        if (!accion || accion.modo !== 'reasignar') { aviso.style.display = 'none'; return; }
        aviso.style.display = '';
        var select = document.getElementById('asigNuevo');
        var nuevo = select.value ? 'a ' + select.options[select.selectedIndex].text.split(' — ')[0] : 'al nuevo profesional';
        var actual = accion.actual;
        document.getElementById('asigAvisoAcceso').textContent = actual.nombre + ' dejará de ver a este paciente.';
        var citas = actual.citasFuturas || 0;
        document.getElementById('asigAvisoCitasWrap').style.display = citas ? '' : 'none';
        document.getElementById('asigAvisoCitas').textContent =
            'Se cancelarán ' + citas + ' cita(s) próxima(s) con ' + actual.nombre + '.';
        document.getElementById('asigAvisoNotif').textContent =
            'Se avisará al paciente, a ' + actual.nombre + ' y ' + nuevo + '.';
    }

    async function confirmar() {
        if (!accion) return;
        var idNuevo = Number(document.getElementById('asigNuevo').value);
        var motivo = document.getElementById('asigMotivo').value.trim();
        if (!idNuevo) { avisar('warning', 'Elige un profesional.', 'Falta un dato'); return; }
        if (motivo.length < 5) { avisar('warning', 'Escribe el motivo (mínimo 5 caracteres).', 'Falta un dato'); return; }

        var esReasignar = accion.modo === 'reasignar';
        var url = esReasignar ? '/api/admin/asignaciones/reasignar' : '/api/admin/asignaciones';
        var cuerpo = esReasignar
            ? { idPaciente: accion.paciente.idPaciente, idProfesionalAnterior: accion.actual.idProfesional, idProfesionalNuevo: idNuevo, motivo: motivo }
            : { idPaciente: accion.paciente.idPaciente, idProfesional: idNuevo, motivo: motivo };

        var btn = document.getElementById('btnConfirmarAsignacion');
        btn.disabled = true;
        try {
            var res = await fetch(url, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cuerpo),
            });
            var json = await res.json().catch(function () { return {}; });
            if (!res.ok || !json.success) {
                avisar('error', json.message || 'No se pudo guardar.', 'Error');
                return;
            }
            modal.hide();
            avisar('success', json.message, esReasignar ? 'Caso reasignado' : 'Paciente asignado');
            cargarPacientes();
            cargarHistorial();
        } catch (err) {
            console.error(err);
            avisar('error', 'No se pudo conectar con el servidor.', 'Error');
        } finally {
            btn.disabled = false;
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        modal = new bootstrap.Modal(document.getElementById('modalAsignacion'));
        document.querySelectorAll('.admin-panel-tab').forEach(function (b) {
            b.addEventListener('click', function () { mostrarTab(b.dataset.tab); });
        });
        document.getElementById('buscarPaciente').addEventListener('input', pintarPacientes);
        document.getElementById('filtroAsignacion').addEventListener('change', pintarPacientes);
        document.getElementById('tablaAsignaciones').addEventListener('click', function (e) {
            var btn = e.target.closest('[data-reasignar], [data-asignar]');
            if (!btn) return;
            if (btn.dataset.reasignar) abrirModal('reasignar', Number(btn.dataset.reasignar), Number(btn.dataset.profesional));
            else abrirModal('asignar', Number(btn.dataset.asignar));
        });
        document.getElementById('asigNuevo').addEventListener('change', pintarAviso);
        document.getElementById('asigMotivo').addEventListener('input', function () {
            document.getElementById('asigContador').textContent = this.value.length + '/500';
        });
        document.getElementById('btnConfirmarAsignacion').addEventListener('click', confirmar);
        cargarPacientes();
        cargarHistorial();
    });
})();
