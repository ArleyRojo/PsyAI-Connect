from django.db.models import OuterRef, Subquery
from django.utils import timezone

from apps.authentication.models import Register
from apps.patients.models import PerfilPaciente, EvolucionPaciente, Anamnesis, Familiar
from apps.professionals.models import PerfilProfesional


class PatientRepository:
    def update_profile_photo(self, filename, user_id):
        Register.objects.filter(idUsuario=user_id).update(fotoPerfil=filename)

    def get_patient_profile(self, user_id):
        try:
            user = Register.objects.get(idUsuario=user_id)
        except Register.DoesNotExist:
            return None
        try:
            perfil = PerfilPaciente.objects.get(idPaciente=user_id)
        except PerfilPaciente.DoesNotExist:
            perfil = None
        return {
            "nombre": user.nombre,
            "email": user.email,
            "fotoPerfil": user.fotoPerfil,
            "fechaRegistro": user.fechaRegistro,
            "edad": perfil.edad if perfil else None,
            "genero": perfil.genero if perfil else None,
            "numeroTelefonico": perfil.numeroTelefonico if perfil else None,
            "consentimiento_chatbot": perfil.consentimiento_chatbot if perfil else None,
            "prefNotificaciones": perfil.prefNotificaciones if perfil else "Activadas",
            "prefRecordatorios": perfil.prefRecordatorios if perfil else "Activados",
            "prefContacto": perfil.prefContacto if perfil else "Correo",
            # nuevos
            "canalNotificacion": perfil.canalNotificacion if perfil else "email",
            "whatsappConsentimiento": perfil.whatsappConsentimiento if perfil else False,
            "whatsappConsentimientoFecha": perfil.whatsappConsentimientoFecha.isoformat() if perfil and perfil.whatsappConsentimientoFecha else None,
            "recibirRecordatorioCita": perfil.recibirRecordatorioCita if perfil else True,
            "recibirConfirmacion": perfil.recibirConfirmacion if perfil else True,
            "recibirMensajePro": perfil.recibirMensajePro if perfil else True,
        }

    def update_patient_profile(self, data):
        user_id = data.get("idPaciente") or data.get("user_id") or data.get("idUsuario")
        perfil, _ = PerfilPaciente.objects.get_or_create(
            idPaciente_id=user_id,
            defaults={"consentimiento_chatbot": False},
        )
        campos_editables = ["genero", "edad", "numeroTelefonico"]
        campos_a_guardar = []
        for campo in campos_editables:
            if campo in data:
                setattr(perfil, campo, data[campo])
                campos_a_guardar.append(campo)
        if campos_a_guardar:
            perfil.save(update_fields=campos_a_guardar)

    def get_preferences(self, user_id):
        try:
            perfil = PerfilPaciente.objects.get(idPaciente=user_id)
            return {
                "canalNotificacion": perfil.canalNotificacion,
                "whatsappConsentimiento": perfil.whatsappConsentimiento,
                "whatsappConsentimientoFecha": perfil.whatsappConsentimientoFecha.isoformat() if perfil.whatsappConsentimientoFecha else None,
                "numeroTelefonico": perfil.numeroTelefonico,
                "recibirRecordatorioCita": perfil.recibirRecordatorioCita,
                "recibirConfirmacion": perfil.recibirConfirmacion,
                "recibirMensajePro": perfil.recibirMensajePro,
            }
        except PerfilPaciente.DoesNotExist:
            return {
                "canalNotificacion": "email",
                "whatsappConsentimiento": False,
                "whatsappConsentimientoFecha": None,
                "numeroTelefonico": "",
                "recibirRecordatorioCita": True,
                "recibirConfirmacion": True,
                "recibirMensajePro": True,
            }

    def save_preferences(self, user_id, data):
        perfil, _ = PerfilPaciente.objects.get_or_create(
            idPaciente_id=user_id,
            defaults={"consentimiento_chatbot": False},
        )
        allowed = [
            "canalNotificacion", "whatsappConsentimiento",
            "numeroTelefonico", "recibirRecordatorioCita",
            "recibirConfirmacion", "recibirMensajePro",
        ]
        for k in allowed:
            if k in data:
                setattr(perfil, k, data[k])

        # consentimiento -> fecha
        if "whatsappConsentimiento" in data:
            if data["whatsappConsentimiento"] and not perfil.whatsappConsentimientoFecha:
                from django.utils import timezone
                perfil.whatsappConsentimientoFecha = timezone.now()
            elif not data["whatsappConsentimiento"]:
                perfil.whatsappConsentimientoFecha = None

        perfil.save(update_fields=[
            "canalNotificacion", "whatsappConsentimiento",
            "whatsappConsentimientoFecha", "numeroTelefonico",
            "recibirRecordatorioCita", "recibirConfirmacion",
            "recibirMensajePro",
        ])

    def get_chatbot_consent(self, user_id):
        try:
            perfil = PerfilPaciente.objects.get(idPaciente=user_id)
            return bool(perfil.consentimiento_chatbot)
        except PerfilPaciente.DoesNotExist:
            return False

    def update_chatbot_consent(self, user_id, consent):
        perfil, created = PerfilPaciente.objects.get_or_create(
            idPaciente_id=user_id,
        )
        perfil.consentimiento_chatbot = bool(consent)
        perfil.save(update_fields=["consentimiento_chatbot"])

    def create_patient_evolution(self, user_id, data):
        EvolucionPaciente.objects.create(
            idPaciente_id=user_id,
            estadoEmocional=data.get("estadoEmocional"),
            nivelEnergia=data.get("nivelEnergia"),
            notasPersonales=data.get("notasPersonales"),
        )

    def get_patient_evolution_history(self, user_id):
        rows = EvolucionPaciente.objects.filter(
            idPaciente_id=user_id
        ).order_by("-fecha")
        return [
            {
                "estadoEmocional": r.estadoEmocional,
                "nivelEnergia": r.nivelEnergia,
                "notasPersonales": r.notasPersonales,
                "fecha": r.fecha.strftime("%d/%m/%Y") if r.fecha else None,
                "fechaRaw": r.fecha,
            }
            for r in rows
        ]

    def list_patients(self, page=1, limit=20):
        offset = (page - 1) * limit
        users = list(
            Register.objects.filter(rol="paciente").order_by("nombre")[offset : offset + limit]
        )
        user_ids = [u.idUsuario for u in users]
        anamnesis_paciente_ids = set(
            Anamnesis.objects.filter(idPaciente_id__in=user_ids).values_list("idPaciente_id", flat=True)
        )
        return [
            {
                "idUsuario": u.idUsuario,
                "nombre": u.nombre,
                "email": u.email,
                "fotoPerfil": u.fotoPerfil,
                "tieneAnamnesis": u.idUsuario in anamnesis_paciente_ids,
            }
            for u in users
        ]

    def list_professionals(self):
        rows = Register.objects.filter(
            rol="profesional"
        ).order_by("nombre").values("idUsuario", "nombre")
        return [{"idUsuario": r["idUsuario"], "nombre": r["nombre"]} for r in rows]

    def list_professionals_for_patient(self, patient_id):
        rows = (
            Register.objects.filter(rol="profesional")
            .order_by("nombre")
            .values("idUsuario", "nombre", "fotoPerfil")
        )
        especialidades = {
            p.idProfesional_id: p.especialidad
            for p in PerfilProfesional.objects.filter(
                idProfesional_id__in=rows.values_list("idUsuario", flat=True)
            )
        }
        return [
            {
                "idUsuario": r["idUsuario"],
                "nombre": r["nombre"],
                "fotoPerfil": r["fotoPerfil"],
                "especialidad": especialidades.get(r["idUsuario"]),
            }
            for r in rows
        ]

    # ── Anamnesis ─────────────────────────────────────────────────────────────

    def get_anamnesis_by_paciente(self, paciente_id):
        """Retorna la Anamnesis (con familiares prefetch) o None."""
        try:
            return (
                Anamnesis.objects
                .select_related("idProfesional")
                .prefetch_related("familiares")
                .get(idPaciente_id=paciente_id)
            )
        except Anamnesis.DoesNotExist:
            return None

    def create_anamnesis(self, paciente_id, profesional_id, data, familiares_data=None):
        """Crea Anamnesis + Familiares en una transacción atómica."""
        from django.db import transaction
        CAMPOS_ANAMNESIS = [
            "tipoDocumento", "numeroDocumento", "fechaNacimiento", "edad", "genero",
            "estadoCivil", "orientacionSexual", "razaEtnica", "lugarNacimiento",
            "telefonoPrincipal", "telefonoAlterno", "whatsapp", "correoAlterno",
            "direccionResidencia", "ciudad", "departamento", "barrio", "codigoPostal",
            "emergenciaNombre", "emergenciaParentesco", "emergenciaTelefono",
            "nivelEscolar", "institucionEducativa", "anoGraduacion", "carreraEstudiada",
            "estudiaActualmente", "ocupacion", "situacionLaboral", "empresa", "cargo",
            "rangoIngresosMensuales", "seguroSalud", "epsNombre", "alergias",
            "cirugiasPrevias", "enfermedadesCronicas", "medicamentosActuales",
            "discapacidad", "tipoDiscapacidad", "conviveCon", "personasQueVivenCon",
            "cantidadHijos", "consumoAlcohol", "consumoTabaco", "consumoSustancias",
            "suenoHoras", "calidadSueno", "actividadFisica", "motivoConsulta",
            "antecedentesFamiliares", "narrativa", "observaciones", "entrevistador",
        ]
        with transaction.atomic():
            kwargs = {c: data[c] for c in CAMPOS_ANAMNESIS if c in data}
            anamnesis = Anamnesis.objects.create(
                idPaciente_id=paciente_id,
                idProfesional_id=profesional_id,
                **kwargs,
            )
            if familiares_data:
                Familiar.objects.bulk_create([
                    Familiar(
                        idAnamnesis=anamnesis,
                        tipoParentesco=f.get("tipoParentesco"),
                        nombreCompleto=f.get("nombreCompleto"),
                        fechaNacimiento=f.get("fechaNacimiento"),
                        edad=f.get("edad"),
                        sexo=f.get("sexo"),
                        vivo=f.get("vivo"),
                        causaFallecimiento=f.get("causaFallecimiento"),
                        estadoSalud=f.get("estadoSalud"),
                        diagnosticoOEnfermedad=f.get("diagnosticoOEnfermedad"),
                        ocupacion=f.get("ocupacion"),
                        telefono=f.get("telefono"),
                        notas=f.get("notas"),
                        orden=f.get("orden", idx),
                    )
                    for idx, f in enumerate(familiares_data)
                ])
        return anamnesis

    def update_anamnesis(self, anamnesis, data):
        """Actualiza campos presentes en data y retorna la instancia actualizada."""
        CAMPOS_EDITABLES = [
            "tipoDocumento", "numeroDocumento", "fechaNacimiento", "edad", "genero",
            "estadoCivil", "orientacionSexual", "razaEtnica", "lugarNacimiento",
            "telefonoPrincipal", "telefonoAlterno", "whatsapp", "correoAlterno",
            "direccionResidencia", "ciudad", "departamento", "barrio", "codigoPostal",
            "emergenciaNombre", "emergenciaParentesco", "emergenciaTelefono",
            "nivelEscolar", "institucionEducativa", "anoGraduacion", "carreraEstudiada",
            "estudiaActualmente", "ocupacion", "situacionLaboral", "empresa", "cargo",
            "rangoIngresosMensuales", "seguroSalud", "epsNombre", "alergias",
            "cirugiasPrevias", "enfermedadesCronicas", "medicamentosActuales",
            "discapacidad", "tipoDiscapacidad", "conviveCon", "personasQueVivenCon",
            "cantidadHijos", "consumoAlcohol", "consumoTabaco", "consumoSustancias",
            "suenoHoras", "calidadSueno", "actividadFisica", "motivoConsulta",
            "antecedentesFamiliares", "narrativa", "observaciones", "entrevistador",
        ]
        campos_a_guardar = []
        for campo in CAMPOS_EDITABLES:
            if campo in data:
                setattr(anamnesis, campo, data[campo])
                campos_a_guardar.append(campo)
        if campos_a_guardar:
            # fechaActualizacion se actualiza sola por auto_now=True
            anamnesis.save(update_fields=campos_a_guardar + ["fechaActualizacion"])
        return anamnesis

    def replace_familiares(self, anamnesis, familiares_data):
        """Reemplaza todos los familiares de una anamnesis (delete + bulk_create)."""
        from django.db import transaction
        with transaction.atomic():
            anamnesis.familiares.all().delete()
            if familiares_data:
                Familiar.objects.bulk_create([
                    Familiar(
                        idAnamnesis=anamnesis,
                        tipoParentesco=f.get("tipoParentesco"),
                        nombreCompleto=f.get("nombreCompleto"),
                        fechaNacimiento=f.get("fechaNacimiento"),
                        edad=f.get("edad"),
                        sexo=f.get("sexo"),
                        vivo=f.get("vivo"),
                        causaFallecimiento=f.get("causaFallecimiento"),
                        estadoSalud=f.get("estadoSalud"),
                        diagnosticoOEnfermedad=f.get("diagnosticoOEnfermedad"),
                        ocupacion=f.get("ocupacion"),
                        telefono=f.get("telefono"),
                        notas=f.get("notas"),
                        orden=f.get("orden", idx),
                    )
                    for idx, f in enumerate(familiares_data)
                ])

    def existe_anamnesis(self, paciente_id):
        return Anamnesis.objects.filter(idPaciente_id=paciente_id).exists()

