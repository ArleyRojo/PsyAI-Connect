from django.db import models

from apps.authentication.models import Register


class PerfilPaciente(models.Model):
    NOTIF_CHOICES = [("Activadas", "Activadas"), ("Desactivadas", "Desactivadas")]
    RECORDAT_CHOICES = [("Activados", "Activados"), ("Desactivados", "Desactivados")]
    CONTACTO_CHOICES = [
        ("Correo", "Correo"),
        ("WhatsApp", "WhatsApp"),
        ("Teléfono", "Teléfono"),
    ]
    CANAL_CHOICES = [
        ("email", "Correo"),
        ("whatsapp", "WhatsApp"),
        ("ambos", "Ambos"),
        ("ninguno", "Ninguno"),
    ]

    idPaciente = models.OneToOneField(
        Register,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="idPaciente",
        related_name="perfil_paciente",
    )
    genero = models.CharField(max_length=20, null=True, blank=True)
    edad = models.IntegerField(null=True, blank=True)
    numeroTelefonico = models.CharField(max_length=20, null=True, blank=True)
    consentimientoDatos = models.BooleanField(default=False)
    consentimiento_chatbot = models.BooleanField(default=False)
    prefNotificaciones = models.CharField(
        max_length=15, choices=NOTIF_CHOICES, default="Activadas"
    )
    prefRecordatorios = models.CharField(
        max_length=15, choices=RECORDAT_CHOICES, default="Activados"
    )
    prefContacto = models.CharField(
        max_length=15, choices=CONTACTO_CHOICES, default="Correo"
    )
    # Nuevas preferencias de notificación
    canalNotificacion = models.CharField(
        max_length=10,
        choices=CANAL_CHOICES,
        default="email",
        verbose_name="Canal de notificación",
    )
    whatsappConsentimiento = models.BooleanField(
        default=False,
        verbose_name="Consentimiento WhatsApp",
    )
    whatsappConsentimientoFecha = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha consentimiento WhatsApp",
    )
    recibirRecordatorioCita = models.BooleanField(default=True)
    recibirConfirmacion = models.BooleanField(default=True)
    recibirMensajePro = models.BooleanField(default=True)

    class Meta:
        db_table = "PerfilPaciente"

    def __str__(self):
        return f"Paciente {self.idPaciente_id}"

    def to_dict(self):
        return {
            "idPaciente": self.idPaciente_id,
            "genero": self.genero,
            "edad": self.edad,
            "numeroTelefonico": self.numeroTelefonico,
            "consentimientoDatos": self.consentimientoDatos,
            "consentimiento_chatbot": self.consentimiento_chatbot,
            "prefNotificaciones": self.prefNotificaciones,
            "prefRecordatorios": self.prefRecordatorios,
            "prefContacto": self.prefContacto,
            "canalNotificacion": self.canalNotificacion,
            "whatsappConsentimiento": self.whatsappConsentimiento,
            "whatsappConsentimientoFecha": self.whatsappConsentimientoFecha.isoformat() if self.whatsappConsentimientoFecha else None,
            "recibirRecordatorioCita": self.recibirRecordatorioCita,
            "recibirConfirmacion": self.recibirConfirmacion,
            "recibirMensajePro": self.recibirMensajePro,
        }


class EvolucionPaciente(models.Model):
    idEvolucion = models.AutoField(primary_key=True)
    idPaciente = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
        related_name="evoluciones",
    )
    idConversacion = models.IntegerField(null=True, blank=True)
    estadoEmocional = models.CharField(max_length=100, null=True, blank=True)
    nivelEnergia = models.IntegerField(null=True, blank=True)
    notasPersonales = models.TextField(null=True, blank=True)
    resultadoEmocional = models.CharField(max_length=100, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "EvolucionPaciente"

    def __str__(self):
        return f"Evolucion {self.idEvolucion} - Paciente {self.idPaciente_id}"

    def to_dict(self):
        return {
            "idEvolucion": self.idEvolucion,
            "idPaciente": self.idPaciente_id,
            "idConversacion": self.idConversacion,
            "estadoEmocional": self.estadoEmocional,
            "nivelEnergia": self.nivelEnergia,
            "notasPersonales": self.notasPersonales,
            "resultadoEmocional": self.resultadoEmocional,
            "fecha": self.fecha.isoformat() if self.fecha else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Anamnesis clínica (área profesional)
# ─────────────────────────────────────────────────────────────────────────────

class Anamnesis(models.Model):
    # ── Choices ──────────────────────────────────────────────────────────────
    TIPO_DOC_CHOICES = [
        ("CC", "Cédula de Ciudadanía"),
        ("CE", "Cédula de Extranjería"),
        ("TI", "Tarjeta de Identidad"),
        ("Pasaporte", "Pasaporte"),
    ]
    NIVEL_ESCOLAR_CHOICES = [
        ("ninguno", "Ninguno"),
        ("primaria", "Primaria"),
        ("secundaria", "Secundaria / Bachillerato"),
        ("tecnico", "Técnico / Tecnólogo"),
        ("universitario", "Universitario"),
        ("posgrado", "Posgrado"),
    ]
    RANGO_INGRESOS_CHOICES = [
        ("NO_INFORMA", "No informa"),
        ("SIN_INGRESOS", "Sin ingresos"),
        ("MENOS1SMM", "Menos de 1 SMMLV"),
        ("1SMM2SMM", "Entre 1 y 2 SMMLV"),
        ("2SMM4SMM", "Entre 2 y 4 SMMLV"),
        ("4SMM6SMM", "Entre 4 y 6 SMMLV"),
        ("6SMM10SMM", "Entre 6 y 10 SMMLV"),
        ("MAS10SMM", "Más de 10 SMMLV"),
    ]

    # ── PK / FK ───────────────────────────────────────────────────────────────
    idAnamnesis = models.AutoField(primary_key=True)
    idPaciente = models.OneToOneField(
        Register,
        on_delete=models.CASCADE,
        db_column="idPaciente",
        related_name="anamnesis",
    )
    idProfesional = models.ForeignKey(
        Register,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="idProfesional",
        related_name="anamnesis_creadas",
    )
    fechaActualizacion = models.DateTimeField(auto_now=True)

    # ── A. Personales ─────────────────────────────────────────────────────────
    tipoDocumento = models.CharField(
        max_length=20, choices=TIPO_DOC_CHOICES, null=True, blank=True
    )
    numeroDocumento = models.CharField(max_length=40, null=True, blank=True)
    fechaNacimiento = models.DateField(null=True, blank=True)
    edad = models.IntegerField(null=True, blank=True)
    genero = models.CharField(max_length=30, null=True, blank=True)
    estadoCivil = models.CharField(max_length=30, null=True, blank=True)
    orientacionSexual = models.CharField(max_length=30, null=True, blank=True)
    razaEtnica = models.CharField(max_length=40, null=True, blank=True)
    lugarNacimiento = models.CharField(max_length=120, null=True, blank=True)

    # ── B. Contacto ───────────────────────────────────────────────────────────
    telefonoPrincipal = models.CharField(max_length=20, null=True, blank=True)
    telefonoAlterno = models.CharField(max_length=20, null=True, blank=True)
    whatsapp = models.CharField(max_length=20, null=True, blank=True)
    correoAlterno = models.EmailField(max_length=120, null=True, blank=True)
    direccionResidencia = models.CharField(max_length=200, null=True, blank=True)
    ciudad = models.CharField(max_length=80, null=True, blank=True)
    departamento = models.CharField(max_length=80, null=True, blank=True)
    barrio = models.CharField(max_length=80, null=True, blank=True)
    codigoPostal = models.CharField(max_length=10, null=True, blank=True)
    emergenciaNombre = models.CharField(max_length=120, null=True, blank=True)
    emergenciaParentesco = models.CharField(max_length=40, null=True, blank=True)
    emergenciaTelefono = models.CharField(max_length=20, null=True, blank=True)

    # ── C. Escolar ────────────────────────────────────────────────────────────
    nivelEscolar = models.CharField(
        max_length=20, choices=NIVEL_ESCOLAR_CHOICES, null=True, blank=True
    )
    institucionEducativa = models.CharField(max_length=150, null=True, blank=True)
    anoGraduacion = models.IntegerField(null=True, blank=True)
    carreraEstudiada = models.CharField(max_length=150, null=True, blank=True)
    estudiaActualmente = models.BooleanField(null=True, blank=True)

    # ── D. Ocupación ──────────────────────────────────────────────────────────
    ocupacion = models.CharField(max_length=120, null=True, blank=True)
    situacionLaboral = models.CharField(max_length=60, null=True, blank=True)
    empresa = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=100, null=True, blank=True)
    rangoIngresosMensuales = models.CharField(
        max_length=20, choices=RANGO_INGRESOS_CHOICES, null=True, blank=True
    )

    # ── E. Salud ──────────────────────────────────────────────────────────────
    seguroSalud = models.BooleanField(null=True, blank=True)
    epsNombre = models.CharField(max_length=120, null=True, blank=True)
    alergias = models.TextField(null=True, blank=True)
    cirugiasPrevias = models.TextField(null=True, blank=True)
    enfermedadesCronicas = models.TextField(null=True, blank=True)
    medicamentosActuales = models.TextField(null=True, blank=True)
    discapacidad = models.BooleanField(null=True, blank=True)
    tipoDiscapacidad = models.CharField(max_length=120, null=True, blank=True)

    # ── F. Psicosocial ────────────────────────────────────────────────────────
    conviveCon = models.CharField(max_length=80, null=True, blank=True)
    personasQueVivenCon = models.IntegerField(null=True, blank=True)
    cantidadHijos = models.IntegerField(null=True, blank=True)
    consumoAlcohol = models.CharField(max_length=40, null=True, blank=True)
    consumoTabaco = models.CharField(max_length=40, null=True, blank=True)
    consumoSustancias = models.TextField(null=True, blank=True)
    suenoHoras = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    calidadSueno = models.CharField(max_length=40, null=True, blank=True)
    actividadFisica = models.CharField(max_length=40, null=True, blank=True)

    # ── G/H. Entrevista ───────────────────────────────────────────────────────
    motivoConsulta = models.TextField(null=True, blank=True)
    antecedentesFamiliares = models.TextField(null=True, blank=True)
    narrativa = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    entrevistador = models.CharField(max_length=120, null=True, blank=True)

    class Meta:
        db_table = "Anamnesis"

    def __str__(self):
        return f"Anamnesis paciente {self.idPaciente_id}"

    @property
    def edad_calculada(self):
        """Calcula la edad a partir de fechaNacimiento sin dependencias externas."""
        import datetime
        if not self.fechaNacimiento:
            return None
        fn = self.fechaNacimiento
        if isinstance(fn, str):
            try:
                fn = datetime.date.fromisoformat(fn)
            except Exception:
                return None
        hoy = datetime.date.today()
        cumple_este_anio = fn.replace(year=hoy.year)
        anios = hoy.year - fn.year
        if cumple_este_anio > hoy:
            anios -= 1
        return anios

    def to_dict(self, include_familiares=False):
        fn_str = (
            self.fechaNacimiento.isoformat()
            if hasattr(self.fechaNacimiento, "isoformat")
            else (str(self.fechaNacimiento) if self.fechaNacimiento else None)
        )
        data = {
            "idAnamnesis": self.idAnamnesis,
            "idPaciente": self.idPaciente_id,
            "idProfesional": self.idProfesional_id,
            "fechaActualizacion": self.fechaActualizacion.isoformat() if self.fechaActualizacion else None,
            # A. Personales
            "tipoDocumento": self.tipoDocumento,
            "numeroDocumento": self.numeroDocumento,
            "fechaNacimiento": fn_str,
            "edad": self.edad,
            "edadCalculada": self.edad_calculada,
            "genero": self.genero,
            "estadoCivil": self.estadoCivil,
            "orientacionSexual": self.orientacionSexual,
            "razaEtnica": self.razaEtnica,
            "lugarNacimiento": self.lugarNacimiento,
            # B. Contacto
            "telefonoPrincipal": self.telefonoPrincipal,
            "telefonoAlterno": self.telefonoAlterno,
            "whatsapp": self.whatsapp,
            "correoAlterno": self.correoAlterno,
            "direccionResidencia": self.direccionResidencia,
            "ciudad": self.ciudad,
            "departamento": self.departamento,
            "barrio": self.barrio,
            "codigoPostal": self.codigoPostal,
            "emergenciaNombre": self.emergenciaNombre,
            "emergenciaParentesco": self.emergenciaParentesco,
            "emergenciaTelefono": self.emergenciaTelefono,
            # C. Escolar
            "nivelEscolar": self.nivelEscolar,
            "institucionEducativa": self.institucionEducativa,
            "anoGraduacion": self.anoGraduacion,
            "carreraEstudiada": self.carreraEstudiada,
            "estudiaActualmente": self.estudiaActualmente,
            # D. Ocupación
            "ocupacion": self.ocupacion,
            "situacionLaboral": self.situacionLaboral,
            "empresa": self.empresa,
            "cargo": self.cargo,
            "rangoIngresosMensuales": self.rangoIngresosMensuales,
            # E. Salud
            "seguroSalud": self.seguroSalud,
            "epsNombre": self.epsNombre,
            "alergias": self.alergias,
            "cirugiasPrevias": self.cirugiasPrevias,
            "enfermedadesCronicas": self.enfermedadesCronicas,
            "medicamentosActuales": self.medicamentosActuales,
            "discapacidad": self.discapacidad,
            "tipoDiscapacidad": self.tipoDiscapacidad,
            # F. Psicosocial
            "conviveCon": self.conviveCon,
            "personasQueVivenCon": self.personasQueVivenCon,
            "cantidadHijos": self.cantidadHijos,
            "consumoAlcohol": self.consumoAlcohol,
            "consumoTabaco": self.consumoTabaco,
            "consumoSustancias": self.consumoSustancias,
            "suenoHoras": float(self.suenoHoras) if self.suenoHoras is not None else None,
            "calidadSueno": self.calidadSueno,
            "actividadFisica": self.actividadFisica,
            # G/H. Entrevista
            "motivoConsulta": self.motivoConsulta,
            "antecedentesFamiliares": self.antecedentesFamiliares,
            "narrativa": self.narrativa,
            "observaciones": self.observaciones,
            "entrevistador": self.entrevistador,
        }
        if include_familiares:
            data["familiares"] = [f.to_dict() for f in self.familiares.all()]
        return data


class Familiar(models.Model):
    PARENTESCO_CHOICES = [
        ("PADRE", "Padre"),
        ("MADRE", "Madre"),
        ("HIJO", "Hijo"),
        ("HIJA", "Hija"),
        ("ABUELO_PATERNO", "Abuelo paterno"),
        ("ABUELA_PATERNA", "Abuela paterna"),
        ("ABUELO_MATERNO", "Abuelo materno"),
        ("ABUELA_MATERNA", "Abuela materna"),
        ("BISABUELO", "Bisabuelo"),
        ("TIO", "Tío"),
        ("TIA", "Tía"),
        ("PRIMO", "Primo"),
        ("PRIMA", "Prima"),
        ("HERMANO", "Hermano"),
        ("HERMANA", "Hermana"),
        ("CONYUGE", "Cónyuge / Pareja"),
        ("OTRO", "Otro"),
    ]
    ESTADO_SALUD_CHOICES = [
        ("sano", "Sano"),
        ("enfermedad_cronica", "Enfermedad crónica"),
        ("discapacidad", "Discapacidad"),
        ("fallecido", "Fallecido"),
        ("desconocido", "Desconocido"),
    ]

    idFamiliar = models.AutoField(primary_key=True)
    idAnamnesis = models.ForeignKey(
        Anamnesis,
        on_delete=models.CASCADE,
        db_column="idAnamnesis",
        related_name="familiares",
    )
    tipoParentesco = models.CharField(
        max_length=20, choices=PARENTESCO_CHOICES, null=True, blank=True
    )
    nombreCompleto = models.CharField(max_length=120, null=True, blank=True)
    fechaNacimiento = models.DateField(null=True, blank=True)
    edad = models.IntegerField(null=True, blank=True)
    sexo = models.CharField(max_length=20, null=True, blank=True)
    vivo = models.BooleanField(null=True, blank=True)
    causaFallecimiento = models.CharField(max_length=200, null=True, blank=True)
    estadoSalud = models.CharField(
        max_length=20, choices=ESTADO_SALUD_CHOICES, null=True, blank=True
    )
    diagnosticoOEnfermedad = models.TextField(null=True, blank=True)
    ocupacion = models.CharField(max_length=120, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    notas = models.TextField(null=True, blank=True)
    orden = models.IntegerField(default=0)

    class Meta:
        db_table = "AnamnesisFamiliar"
        ordering = ["orden"]

    def __str__(self):
        return f"{self.tipoParentesco} — Anamnesis {self.idAnamnesis_id}"

    def to_dict(self):
        return {
            "idFamiliar": self.idFamiliar,
            "idAnamnesis": self.idAnamnesis_id,
            "tipoParentesco": self.tipoParentesco,
            "nombreCompleto": self.nombreCompleto,
            "fechaNacimiento": (
                self.fechaNacimiento.isoformat()
                if hasattr(self.fechaNacimiento, "isoformat")
                else (str(self.fechaNacimiento) if self.fechaNacimiento else None)
            ),
            "edad": self.edad,
            "sexo": self.sexo,
            "vivo": self.vivo,
            "causaFallecimiento": self.causaFallecimiento,
            "estadoSalud": self.estadoSalud,
            "diagnosticoOEnfermedad": self.diagnosticoOEnfermedad,
            "ocupacion": self.ocupacion,
            "telefono": self.telefono,
            "notas": self.notas,
            "orden": self.orden,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Derechos del titular (Ley 1581/2012)
# ─────────────────────────────────────────────────────────────────────────────

def sumar_dias_habiles(fecha_inicio, dias_habiles, festivos=None):
    """
    Suma días hábiles a una fecha dada (excluye sábados, domingos y festivos colombianos).
    Retorna la fecha límite (date).
    """
    from datetime import timedelta
    if festivos is None:
        festivos = set()
    fecha = fecha_inicio
    while dias_habiles > 0:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5 and fecha not in festivos:  # 0-4 = Lun-Vie
            dias_habiles -= 1
    return fecha


def calcular_fecha_limite_solicitud(tipo_solicitud):
    """
    Calcula la fecha límite para responder una solicitud de derechos.
    - Consulta/Acceso/Rectificación/Revocatoria: 10 días hábiles (prorrogables 5)
    - Reclamo: 15 días hábiles (prorrogables 8)
    """
    from django.utils import timezone
    hoy = timezone.now().date()
    if tipo_solicitud in ("acceso", "rectificacion", "supresion", "revocatoria"):
        return sumar_dias_habiles(hoy, 10)
    elif tipo_solicitud == "reclamo":
        return sumar_dias_habiles(hoy, 15)
    else:
        return sumar_dias_habiles(hoy, 10)


class SolicitudDerechos(models.Model):
    """
    Solicitudes de derechos ARCO + revocatoria + reclamo (Ley 1581/2012).
    Plazos:
    - Consulta/Acceso/Rectificación/Supresión/Revocatoria: 10 días hábiles (prorrogables 5)
    - Reclamo: 15 días hábiles (prorrogables 8)
    """
    TIPO_CHOICES = [
        ("acceso", "Acceso / Consulta"),
        ("rectificacion", "Rectificación / Actualización"),
        ("supresion", "Supresión / Eliminación"),
        ("revocatoria", "Revocatoria del consentimiento"),
        ("reclamo", "Reclamo"),
    ]
    ESTADO_CHOICES = [
        ("recibida", "Recibida"),
        ("en_proceso", "En proceso"),
        ("respondida", "Respondida"),
        ("prorrogada", "Prorrogada"),
        ("cerrada", "Cerrada"),
    ]

    idSolicitud = models.AutoField(primary_key=True)
    idUsuario = models.ForeignKey(
        Register,
        on_delete=models.CASCADE,
        db_column="idUsuario",
        related_name="solicitudes_derechos",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField(blank=True, help_text="Detalle de la solicitud")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="recibida")
    fecha = models.DateTimeField(auto_now_add=True)
    fechaLimite = models.DateField(help_text="Fecha límite de respuesta (días hábiles)")
    fechaRespuesta = models.DateTimeField(null=True, blank=True)
    respuesta = models.TextField(blank=True, help_text="Respuesta dada al titular")
    prorrogada = models.BooleanField(default=False)
    fechaProrroga = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "SolicitudDerechos"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["idUsuario", "estado"]),
            models.Index(fields=["fechaLimite"]),
        ]

    def __str__(self):
        return f"Solicitud {self.tipo} - Usuario {self.idUsuario_id} ({self.estado})"

    def to_dict(self):
        return {
            "idSolicitud": self.idSolicitud,
            "idUsuario": self.idUsuario_id,
            "tipo": self.tipo,
            "descripcion": self.descripcion,
            "estado": self.estado,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "fechaLimite": self.fechaLimite.isoformat() if self.fechaLimite else None,
            "fechaRespuesta": self.fechaRespuesta.isoformat() if self.fechaRespuesta else None,
            "respuesta": self.respuesta,
            "prorrogada": self.prorrogada,
            "fechaProrroga": self.fechaProrroga.isoformat() if self.fechaProrroga else None,
        }
