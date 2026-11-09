// Mis datos personales (HU-66): arma un documento con los datos del paciente
// para guardarlo como PDF desde el navegador (Ley 1581 de 2012, derecho de acceso).
// No incluye conversaciones con el chatbot ni mensajes del chat.
(function () {
    'use strict';

    var MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
        'septiembre', 'octubre', 'noviembre', 'diciembre'];

    // Nombres legibles de los campos de la historia clínica inicial (anamnesis)
    var ETIQUETAS = {
        fechaActualizacion: 'Última actualización', tipoDocumento: 'Tipo de documento', numeroDocumento: 'Número de documento',
        fechaNacimiento: 'Fecha de nacimiento', edad: 'Edad', edadCalculada: 'Edad calculada', genero: 'Género',
        estadoCivil: 'Estado civil', orientacionSexual: 'Orientación sexual', razaEtnica: 'Grupo étnico',
        lugarNacimiento: 'Lugar de nacimiento', telefonoPrincipal: 'Teléfono principal', telefonoAlterno: 'Teléfono alterno',
        whatsapp: 'WhatsApp', correoAlterno: 'Correo alterno', direccionResidencia: 'Dirección', ciudad: 'Ciudad',
        departamento: 'Departamento', barrio: 'Barrio', codigoPostal: 'Código postal',
        emergenciaNombre: 'Contacto de emergencia', emergenciaParentesco: 'Parentesco', emergenciaTelefono: 'Teléfono de emergencia',
        nivelEscolar: 'Nivel escolar', institucionEducativa: 'Institución educativa', anoGraduacion: 'Año de graduación',
        carreraEstudiada: 'Carrera', estudiaActualmente: 'Estudia actualmente', ocupacion: 'Ocupación',
        situacionLaboral: 'Situación laboral', empresa: 'Empresa', cargo: 'Cargo', rangoIngresosMensuales: 'Ingresos mensuales',
        seguroSalud: 'Seguro de salud', epsNombre: 'EPS', alergias: 'Alergias', cirugiasPrevias: 'Cirugías previas',
        enfermedadesCronicas: 'Enfermedades crónicas', medicamentosActuales: 'Medicamentos actuales', discapacidad: 'Discapacidad',
        tipoDiscapacidad: 'Tipo de discapacidad', conviveCon: 'Convive con', personasQueVivenCon: 'Personas con las que vive',
        cantidadHijos: 'Cantidad de hijos', consumoAlcohol: 'Consumo de alcohol', consumoTabaco: 'Consumo de tabaco',
        consumoSustancias: 'Consumo de sustancias', suenoHoras: 'Horas de sueño', calidadSueno: 'Calidad del sueño',
        familiares: 'Familiares', nombre: 'Nombre', parentesco: 'Parentesco', telefono: 'Teléfono'
    };
    var OCULTOS = ['idAnamnesis', 'idPaciente', 'idProfesional', 'idFamiliar', 'idUsuario'];

    function esc(valor) {
        return String(valor).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function vacio(v) {
        return v === null || v === undefined || v === '' || (Array.isArray(v) && v.length === 0);
    }

    // "2026-11-09" o "2026-11-09T19:22:32Z" -> "9 de noviembre de 2026" (con hora si la trae)
    function fecha(v, conHora) {
        if (vacio(v)) return '—';
        var s = String(v);
        var soloFecha = /^\d{4}-\d{2}-\d{2}$/.test(s);
        var d = soloFecha ? new Date(s + 'T00:00:00') : new Date(s);
        if (isNaN(d)) return s;
        var texto = d.getDate() + ' de ' + MESES[d.getMonth()] + ' de ' + d.getFullYear();
        if (conHora && !soloFecha) {
            texto += ', ' + d.toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' });
        }
        return texto;
    }

    function hora(v) {
        if (vacio(v)) return '—';
        var p = String(v).split(':');
        var d = new Date(2000, 0, 1, Number(p[0]) || 0, Number(p[1]) || 0);
        return d.toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' });
    }

    function dinero(v) {
        if (vacio(v)) return '—';
        var n = Number(v);
        return isNaN(n) ? String(v) : '$' + n.toLocaleString('es-CO', { maximumFractionDigits: 0 });
    }

    function siNo(v) {
        if (vacio(v)) return '—';
        return v ? 'Sí' : 'No';
    }

    // Convierte cualquier valor en texto legible
    function texto(v) {
        if (vacio(v)) return '—';
        if (typeof v === 'boolean') return siNo(v);
        if (Array.isArray(v)) return v.map(texto).join(', ');
        if (typeof v === 'object') {
            return Object.keys(v).map(function (k) { return (ETIQUETAS[k] || k) + ': ' + texto(v[k]); }).join(' · ');
        }
        if (/^\d{4}-\d{2}-\d{2}(T[\d:.]+(Z|[+-]\d{2}:?\d{2})?)?$/.test(String(v))) return fecha(v, String(v).length > 10);
        return String(v);
    }

    // camelCase -> "Camel case" cuando no hay etiqueta definida
    function etiqueta(clave) {
        if (ETIQUETAS[clave]) return ETIQUETAS[clave];
        var s = clave.replace(/_/g, ' ').replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase();
        return s.charAt(0).toUpperCase() + s.slice(1);
    }

    function seccion(icono, titulo, cuerpo) {
        return '<section class="md-seccion"><h2><i class="fas ' + icono + '"></i>' + esc(titulo) + '</h2>' + cuerpo + '</section>';
    }

    function sinDatos(msg) {
        return '<p class="md-vacio">' + esc(msg || 'No hay registros.') + '</p>';
    }

    // pares: [[etiqueta, valorYaFormateado], ...]
    function campos(pares) {
        return '<dl class="md-campos">' + pares.map(function (p) {
            return '<div class="md-campo"><dt>' + esc(p[0]) + '</dt><dd>' + esc(vacio(p[1]) ? '—' : p[1]) + '</dd></div>';
        }).join('') + '</dl>';
    }

    // columnas: [[titulo, function(fila) -> texto], ...]
    function tabla(filas, columnas) {
        if (!filas || !filas.length) return sinDatos();
        var cabeza = '<tr>' + columnas.map(function (c) { return '<th>' + esc(c[0]) + '</th>'; }).join('') + '</tr>';
        var cuerpo = filas.map(function (f) {
            return '<tr>' + columnas.map(function (c) {
                var v = c[1](f);
                return '<td>' + esc(vacio(v) ? '—' : v) + '</td>';
            }).join('') + '</tr>';
        }).join('');
        return '<table class="md-tabla"><thead>' + cabeza + '</thead><tbody>' + cuerpo + '</tbody></table>';
    }

    // ── Secciones ──────────────────────────────────────────────────────────
    function seccionCuenta(c) {
        return seccion('fa-user', 'Cuenta', campos([
            ['Nombre', c.nombre],
            ['Correo', c.email],
            ['Rol', c.rol],
            ['Estado de la cuenta', c.estadoCuenta],
            ['Correo verificado', siNo(c.email_verificado)],
            ['Fecha de registro', fecha(c.fechaRegistro, true)]
        ]));
    }

    function seccionPerfil(p) {
        if (!p) return seccion('fa-id-card', 'Perfil y preferencias', sinDatos('Aún no tienes perfil de paciente.'));
        return seccion('fa-id-card', 'Perfil y preferencias', campos([
            ['Género', p.genero],
            ['Edad', p.edad],
            ['Teléfono', p.numeroTelefonico],
            ['Canal de notificación', p.canalNotificacion],
            ['Autorización de WhatsApp', siNo(p.whatsappConsentimiento)],
            ['Fecha autorización WhatsApp', fecha(p.whatsappConsentimientoFecha, true)],
            ['Recordatorios de cita', siNo(p.recibirRecordatorioCita)],
            ['Confirmaciones de cita', siNo(p.recibirConfirmacion)],
            ['Mensajes del profesional', siNo(p.recibirMensajePro)],
            ['Avisos de facturas', siNo(p.recibirFacturas)],
            ['Avisos del administrador', siNo(p.recibirNotificacionesAdmin)],
            ['Consentimiento de datos', siNo(p.consentimientoDatos)],
            ['Consentimiento del chatbot', siNo(p.consentimiento_chatbot)]
        ]));
    }

    function seccionAnamnesis(a) {
        if (!a) return seccion('fa-notes-medical', 'Historia clínica inicial', sinDatos('Aún no tienes historia clínica inicial.'));
        var pares = [];
        var extras = '';
        Object.keys(a).forEach(function (k) {
            if (OCULTOS.indexOf(k) !== -1) return;
            var v = a[k];
            if (Array.isArray(v) && v.length && typeof v[0] === 'object') {
                var cols = Object.keys(v[0]).filter(function (c) { return OCULTOS.indexOf(c) === -1; });
                extras += '<h3 class="md-subtitulo">' + esc(etiqueta(k)) + '</h3>' +
                    tabla(v, cols.map(function (c) { return [etiqueta(c), function (f) { return texto(f[c]); }]; }));
                return;
            }
            pares.push([etiqueta(k), texto(v)]);
        });
        return seccion('fa-notes-medical', 'Historia clínica inicial', campos(pares) + extras);
    }

    function seccionCitas(citas) {
        return seccion('fa-calendar-check', 'Citas', tabla(citas, [
            ['Fecha', function (c) { return fecha(c.fecha); }],
            ['Hora', function (c) { return hora(c.hora); }],
            ['Profesional', function (c) { return c.idProfesional__nombre; }],
            ['Tipo', function (c) { return c.tipoCita; }],
            ['Motivo', function (c) { return c.motivo; }],
            ['Estado', function (c) { return c.estado; }],
            ['Tu calificación', function (c) {
                if (!c.calificacion__puntuacion) return '—';
                return c.calificacion__puntuacion + '/5' + (c.calificacion__comentario ? ' — ' + c.calificacion__comentario : '');
            }]
        ]));
    }

    function seccionConsejos(consejos) {
        if (!consejos || !consejos.length) return seccion('fa-lightbulb', 'Consejos de tu profesional', sinDatos());
        var html = consejos.map(function (c) {
            var estado = c.completado ? 'Completado el ' + fecha(c.fechaCompletado) : 'Pendiente';
            return '<div class="md-tarjeta"><h3>' + esc(c.titulo) + '</h3><p>' + esc(c.descripcion) + '</p>' +
                '<small>' + esc((c.idAsignacion__idProfesional__nombre || 'Tu profesional') + ' · ' + fecha(c.fecha) + ' · ' + estado) + '</small></div>';
        }).join('');
        return seccion('fa-lightbulb', 'Consejos de tu profesional', html);
    }

    function seccionPrediagnosticos(lista) {
        if (!lista || !lista.length) return seccion('fa-robot', 'Orientaciones del chatbot', sinDatos());
        var html = lista.map(function (p) {
            var partes = [
                ['Resumen', p.resumenPaciente],
                ['Resumen para el profesional', p.resumenProfesional],
                ['Posibles áreas', p.posiblesAreas],
                ['Recomendaciones', p.recomendaciones]
            ].filter(function (x) { return !vacio(x[1]); }).map(function (x) {
                return '<p><strong>' + esc(x[0]) + ':</strong> ' + esc(texto(x[1])) + '</p>';
            }).join('');
            return '<div class="md-tarjeta"><h3>' + esc(fecha(p.fecha, true)) + '</h3>' + partes +
                '<small>Nivel de riesgo: ' + esc(texto(p.nivelRiesgo)) + ' · Atención urgente: ' + esc(siNo(p.requiereAtencionUrgente)) + '</small></div>';
        }).join('');
        return seccion('fa-robot', 'Orientaciones del chatbot', html);
    }

    function seccionFacturas(facturas, items) {
        var conceptos = {};
        (items || []).forEach(function (i) {
            (conceptos[i.idFactura_id] = conceptos[i.idFactura_id] || []).push(i.descripcion);
        });
        return seccion('fa-file-invoice-dollar', 'Pagos y facturas', tabla(facturas, [
            ['N.º', function (f) { return f.idFactura; }],
            ['Fecha', function (f) { return fecha(f.fecha); }],
            ['Profesional', function (f) { return f.idProfesional__nombre; }],
            ['Concepto', function (f) { return (conceptos[f.idFactura] || []).join(', '); }],
            ['Monto', function (f) { return dinero(f.monto); }],
            ['Estado', function (f) { return f.estadoPago; }],
            ['Método', function (f) { return f.metodoPago; }],
            ['Fecha de pago', function (f) { return f.fechaPago ? fecha(f.fechaPago) : '—'; }]
        ]));
    }

    function seccionDocumentos(docs) {
        return seccion('fa-folder-open', 'Documentos', tabla(docs, [
            ['Nombre', function (d) { return d.nombreArchivo; }],
            ['Descripción', function (d) { return d.descripcion; }],
            ['Tamaño', function (d) { return d.tamanoArchivo ? Math.max(1, Math.round(d.tamanoArchivo / 1024)) + ' KB' : '—'; }],
            ['Fecha', function (d) { return fecha(d.fecha); }],
            ['Estado', function (d) { return d.eliminado ? 'Eliminado' : 'Activo'; }]
        ]));
    }

    function seccionConsentimientos(lista) {
        return seccion('fa-file-signature', 'Consentimientos', tabla(lista, [
            ['Tipo', function (c) { return c.tipo; }],
            ['Versión', function (c) { return c.version; }],
            ['Aceptado', function (c) { return siNo(c.aceptado); }],
            ['Fecha', function (c) { return fecha(c.fecha, true); }],
            ['IP', function (c) { return c.ip; }]
        ]));
    }

    function seccionSolicitudes(lista) {
        return seccion('fa-scale-balanced', 'Solicitudes sobre tus datos', tabla(lista, [
            ['Tipo', function (s) { return s.tipo; }],
            ['Fecha', function (s) { return fecha(s.fecha); }],
            ['Estado', function (s) { return s.estado; }],
            ['Fecha límite', function (s) { return fecha(s.fechaLimite); }],
            ['Respuesta', function (s) { return s.respuesta; }]
        ]));
    }

    function pintar(d) {
        document.getElementById('contenido').innerHTML = [
            seccionCuenta(d.cuenta || {}),
            seccionPerfil(d.perfil),
            seccionAnamnesis(d.anamnesis),
            seccionCitas(d.citas),
            seccionConsejos(d.consejos),
            seccionPrediagnosticos(d.prediagnosticos),
            seccionFacturas(d.facturas, d.items_factura),
            seccionDocumentos(d.documentos),
            seccionConsentimientos(d.consentimientos),
            seccionSolicitudes(d.solicitudes_derechos)
        ].join('');
    }

    function nombreArchivo(nombre) {
        var hoy = new Date();
        var dia = hoy.getFullYear() + '-' + String(hoy.getMonth() + 1).padStart(2, '0') + '-' + String(hoy.getDate()).padStart(2, '0');
        var limpio = String(nombre || 'paciente').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9]+/g, '_');
        return 'Mis_datos_PsyAI_' + limpio + '_' + dia;
    }

    async function cargar() {
        document.getElementById('fechaGenerado').textContent = 'Generado el ' + fecha(new Date().toISOString(), true);
        var boton = document.getElementById('btnGuardarPdf');
        boton.addEventListener('click', function () { window.print(); });

        try {
            var res = await fetch('/api/paciente/mis-datos', { credentials: 'include' });
            if (res.status === 401 || res.status === 403) {
                window.location.href = '/login.html';
                return;
            }
            var json = await res.json().catch(function () { return {}; });
            if (!res.ok || !json.success) throw new Error(json.message || 'Error ' + res.status);

            pintar(json.data || {});
            // El navegador usa el título como nombre del PDF
            document.title = nombreArchivo(json.data && json.data.cuenta && json.data.cuenta.nombre);
            boton.disabled = false;

            if (new URLSearchParams(window.location.search).get('imprimir') === '1') {
                setTimeout(function () { window.print(); }, 400);
            }
        } catch (err) {
            console.error(err);
            document.getElementById('contenido').innerHTML =
                '<p class="md-error"><i class="fas fa-circle-exclamation"></i> No se pudieron cargar tus datos. Intenta de nuevo más tarde.</p>';
        }
    }

    document.addEventListener('DOMContentLoaded', cargar);
})();
