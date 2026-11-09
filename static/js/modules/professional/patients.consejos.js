// Consejos del profesional al paciente (HU-54): enviar, listar y eliminar.

var consejosInicializado = false;

function escapeConsejo(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function avisoConsejo(tipo, mensaje) {
    if (window.mostrarToast) {
        window.mostrarToast(mensaje, tipo);
    } else {
        console.warn(mensaje);
    }
}

function fechaConsejo(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return isNaN(d) ? '' : d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
}

async function cargarPacientesConsejos() {
    inicializarConsejos();
    var select = document.getElementById('selectPacienteConsejo');
    if (!select) return;
    var seleccionado = select.value;
    try {
        var res = await fetch('/api/profesional/pacientes', { credentials: 'include' });
        var data = await res.json().catch(function () { return {}; });
        if (!res.ok || !data.success) {
            avisoConsejo('danger', data.message || 'No se pudieron cargar tus pacientes.');
            return;
        }
        var pacientes = data.pacientes || [];
        select.innerHTML = '<option value="">' + (pacientes.length ? 'Selecciona un paciente asignado' : 'No tienes pacientes asignados') + '</option>' +
            pacientes.map(function (p) {
                return '<option value="' + Number(p.idUsuario) + '">' + escapeConsejo(p.nombre) + '</option>';
            }).join('');
        if (seleccionado) {
            select.value = seleccionado;
            cargarConsejos();
        }
    } catch (err) {
        console.error(err);
        avisoConsejo('danger', 'No se pudo conectar con el servidor.');
    }
}

async function cargarConsejos() {
    var tbody = document.getElementById('tablaConsejos');
    var badge = document.getElementById('badgeConsejos');
    var pacienteId = document.getElementById('selectPacienteConsejo').value;
    if (!pacienteId) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Selecciona un paciente para ver sus consejos.</td></tr>';
        if (badge) badge.textContent = '0';
        return;
    }
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted"><i class="fas fa-spinner fa-spin me-2"></i>Cargando...</td></tr>';
    try {
        var res = await fetch('/api/profesional/pacientes/' + pacienteId + '/consejos', { credentials: 'include' });
        var data = await res.json().catch(function () { return {}; });
        if (!res.ok || !data.success) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">' + escapeConsejo(data.message || 'No se pudieron cargar los consejos.') + '</td></tr>';
            return;
        }
        var consejos = data.consejos || [];
        if (badge) badge.textContent = String(consejos.length);
        if (!consejos.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Aún no le has enviado consejos a este paciente.</td></tr>';
            return;
        }
        tbody.innerHTML = consejos.map(function (c) {
            var estado = c.completado
                ? '<span class="badge bg-success">Completado</span>'
                : '<span class="badge bg-warning text-dark">Pendiente</span>';
            return '<tr>' +
                '<td class="text-nowrap">' + fechaConsejo(c.fecha) + '</td>' +
                '<td class="fw-semibold">' + escapeConsejo(c.titulo) + '</td>' +
                '<td style="white-space:pre-line">' + escapeConsejo(c.descripcion) + '</td>' +
                '<td>' + estado + '</td>' +
                '<td><button type="button" class="btn btn-sm btn-outline-danger" title="Eliminar consejo" onclick="eliminarConsejo(' + Number(c.idConsejo) + ')"><i class="fas fa-trash"></i></button></td>' +
                '</tr>';
        }).join('');
    } catch (err) {
        console.error(err);
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">No se pudo conectar con el servidor.</td></tr>';
    }
}

async function enviarConsejo(event) {
    event.preventDefault();
    var pacienteId = document.getElementById('selectPacienteConsejo').value;
    var titulo = document.getElementById('tituloConsejo').value.trim();
    var descripcion = document.getElementById('descripcionConsejo').value.trim();
    if (!pacienteId || !titulo || !descripcion) {
        avisoConsejo('warning', 'Selecciona un paciente y escribe el título y el consejo.');
        return;
    }
    var btn = document.getElementById('btnEnviarConsejo');
    btn.disabled = true;
    try {
        var res = await fetch('/api/profesional/pacientes/' + pacienteId + '/consejos', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ titulo: titulo, descripcion: descripcion }),
        });
        var data = await res.json().catch(function () { return {}; });
        if (!res.ok || !data.success) {
            avisoConsejo('danger', data.message || 'No se pudo enviar el consejo.');
            return;
        }
        avisoConsejo('success', 'Consejo enviado. El paciente recibió un aviso.');
        document.getElementById('tituloConsejo').value = '';
        document.getElementById('descripcionConsejo').value = '';
        actualizarContadorConsejo();
        cargarConsejos();
    } catch (err) {
        console.error(err);
        avisoConsejo('danger', 'No se pudo conectar con el servidor.');
    } finally {
        btn.disabled = false;
    }
}

async function eliminarConsejo(idConsejo) {
    if (window.Swal) {
        var r = await window.Swal.fire({
            title: '¿Eliminar este consejo?',
            text: 'El paciente ya no lo verá.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Eliminar',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#dc2626',
        });
        if (!r.isConfirmed) return;
    }
    try {
        var res = await fetch('/api/profesional/consejos/' + Number(idConsejo), {
            method: 'DELETE',
            credentials: 'include',
        });
        var data = await res.json().catch(function () { return {}; });
        if (!res.ok || !data.success) {
            avisoConsejo('danger', data.message || 'No se pudo eliminar el consejo.');
            return;
        }
        avisoConsejo('success', 'Consejo eliminado.');
        cargarConsejos();
    } catch (err) {
        console.error(err);
        avisoConsejo('danger', 'No se pudo conectar con el servidor.');
    }
}

function actualizarContadorConsejo() {
    var area = document.getElementById('descripcionConsejo');
    var contador = document.getElementById('contadorConsejo');
    if (area && contador) contador.textContent = area.value.length + ' / 2000';
}

function inicializarConsejos() {
    if (consejosInicializado) return;
    var form = document.getElementById('formConsejo');
    if (!form) return;
    consejosInicializado = true;
    form.addEventListener('submit', enviarConsejo);
    document.getElementById('selectPacienteConsejo').addEventListener('change', cargarConsejos);
    document.getElementById('descripcionConsejo').addEventListener('input', actualizarContadorConsejo);
}
