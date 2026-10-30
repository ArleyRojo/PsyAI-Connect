from django.db.models import OuterRef, Subquery, Q
from django.utils import timezone

from apps.authentication.models import Register, ConsentimientoUsuario
from apps.patients.models import (
    PerfilPaciente, EvolucionPaciente, Anamnesis, Familiar,
    SolicitudDerechos
)
from apps.professionals.models import PerfilProfesional
from apps.chatbot.models import MensajesChat


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

    # ─────────────────────────────────────────────────────────────────────────────
    # Derechos del titular (Ley 1581/2012)
    # ─────────────────────────────────────────────────────────────────────────────

    def get_consentimientos(self, user_id):
        """Obtiene todos los consentimientos del usuario."""
        from apps.authentication.models import ConsentimientoUsuario
        return list(
            ConsentimientoUsuario.objects.filter(idUsuario_id=user_id)
            .order_by("-fecha")
            .values("tipo", "version", "aceptado", "fecha", "ip")
        )

    def revocar_consentimiento(self, user_id, tipo):
        """Revoca un consentimiento específico (datos_sensibles_ia o whatsapp)."""
        from apps.authentication.models import ConsentimientoUsuario
        from apps.patients.models import PerfilPaciente
        updated = ConsentimientoUsuario.objects.filter(
            idUsuario_id=user_id, tipo=tipo, aceptado=True
        ).update(aceptado=False)
        if tipo == "datos_sensibles_ia":
            # Al revocar datos_sensibles_ia, también desactivamos consentimiento_chatbot
            PerfilPaciente.objects.filter(idPaciente_id=user_id).update(consentimiento_chatbot=False)
        elif tipo == "whatsapp":
            PerfilPaciente.objects.filter(idPaciente_id=user_id).update(whatsappConsentimiento=False)
        return updated > 0

    def get_solicitudes_derechos(self, user_id):
        """Obtiene el historial de solicitudes de derechos del usuario."""
        from apps.patients.models import SolicitudDerechos
        return list(
            SolicitudDerechos.objects.filter(idUsuario_id=user_id)
            .order_by("-fecha")
            .values("idSolicitud", "tipo", "descripcion", "estado", "fecha", "fechaLimite", "fechaRespuesta", "respuesta", "prorrogada")
        )

    def crear_solicitud_derechos(self, user_id, tipo, descripcion=""):
        """Crea una nueva solicitud de derechos con fecha límite calculada."""
        from apps.patients.models import SolicitudDerechos, calcular_fecha_limite_solicitud
        from django.utils import timezone
        fecha_limite = calcular_fecha_limite_solicitud(tipo)
        return SolicitudDerechos.objects.create(
            idUsuario_id=user_id,
            tipo=tipo,
            descripcion=descripcion,
            fechaLimite=fecha_limite,
        )

    def exportar_datos_usuario(self, user_id):
        """Exporta todos los datos del usuario para derecho de acceso."""
        from apps.authentication.models import Register
        from apps.patients.models import (
            PerfilPaciente, EvolucionPaciente, Anamnesis, Familiar,
            SolicitudDerechos, ConsentimientoUsuario
        )
        from apps.chatbot.models import ConversacionesChatbot, PrediagnosticoChatbot
        from apps.documents.models import DocumentosPaciente
        from apps.billing.models import Facturas, ItemsFactura
        from apps.scheduling.models import Citas

        try:
            user = Register.objects.get(idUsuario=user_id)
        except Register.DoesNotExist:
            return None

        # Datos básicos
        perfil = None
        try:
            perfil = PerfilPaciente.objects.get(idPaciente=user_id)
        except:
            pass

        # Conversaciones chatbot
        conversaciones = list(
            ConversacionesChatbot.objects.filter(idPaciente_id=user_id)
            .order_by("-fecha")
            .values("mensajeUsuario", "respuestaChatbot", "nivelEmocionalDetectado", "palabrasRiesgoDetectadas", "fecha")
        )

        # Prediagnósticos
        prediagnosticos = list(
            PrediagnosticoChatbot.objects.filter(idPaciente_id=user_id)
            .order_by("-fecha")
            .values("resumenPaciente", "resumenProfesional", "posiblesAreas", "recomendaciones", "nivelRiesgo", "requiereAtencionUrgente", "fecha")
        )

        # Anamnesis
        anamnesis = None
        try:
            anam = Anamnesis.objects.prefetch_related("familiares").get(idPaciente_id=user_id)
            anamnesis = anam.to_dict()
        except:
            anamnesis = None

        # Conversaciones chat (mensajes)
        from apps.chatbot.models import MensajesChat
        mensajes = list(
            MensajesChat.objects.filter(idEmisor_id=user_id) | MensajesChat.objects.filter(idReceptor_id=user_id)
        )
        mensajes = list(MensajesChat.objects.filter(
            models.Q(idEmisor_id=user_id) | models.Q(idReceptor_id=user_id)
        ).order_by("fecha").values("idEmisor_id", "idReceptor_id", "mensaje", "leido", "fecha"))

        # Citas
        citas = list(
            Citas.objects.filter(idPaciente_id=user_id)
            .select_related("idProfesional")
            .order_by("-fecha", "-hora")
            .values("idCita", "idProfesional__nombre", "fecha", "hora", "tipoCita", "tipoSesion", "estado", "motivo")
        )

        # Facturas
        facturas = list(
            Facturas.objects.filter(idPaciente_id=user_id)
            .select_related("idProfesional")
            .order_by("-fecha")
            .values("idFactura", "idProfesional__nombre", "monto", "estadoPago", "fecha", "metodoPago", "fechaPago")
        )

        # Items de factura
        facturas_ids = [f["idFactura"] for f in facturas]
        items = list(
            ItemsFactura.objects.filter(idFactura__in=facturas_ids)
            .values("idFactura_id", "descripcion", "precioUnitario")
        ) if facturas_ids else []

        # Documentos
        documentos = list(
            DocumentosPaciente.objects.filter(idPaciente_id=user_id)
            .order_by("-fecha")
            .values("idDocumento", "nombreArchivo", "rutaArchivo", "tipoMime", "tamanoArchivo", "descripcion", "fecha", "eliminado")
        )

        # Consentimientos
        from apps.authentication.models import ConsentimientoUsuario
        consentimientos = list(
            ConsentimientoUsuario.objects.filter(idUsuario_id=user_id)
            .order_by("-fecha")
            .values("tipo", "version", "aceptado", "fecha", "ip")
        )

        # Solicitudes de derechos
        from apps.patients.models import SolicitudDerechos
        solicitudes = list(
            SolicitudDerechos.objects.filter(idUsuario_id=user_id)
            .order_by("-fecha")
            .values("tipo", "descripcion", "estado", "fecha", "fechaLimite", "fechaRespuesta", "respuesta", "prorrogada")
        )

        return {
            "cuenta": {
                "idUsuario": user.idUsuario,
                "nombre": user.nombre,
                "email": user.email,
                "rol": user.rol,
                "estadoCuenta": user.estadoCuenta,
                "activo": user.activo,
                "email_verificado": user.email_verificado,
                "fechaRegistro": user.fechaRegistro.isoformat() if user.fechaRegistro else None,
                "fotoPerfil": user.fotoPerfil,
            },
            "perfil": perfil.to_dict() if perfil else None,
            "conversaciones_chatbot": conversaciones,
            "prediagnosticos": prediagnosticos,
            "anamnesis": anamnesis,
            "mensajes_chat": mensajes,
            "citas": citas,
            "facturas": facturas,
            "items_factura": items,
            "documentos": documentos,
            "consentimientos": consentimientos,
            "solicitudes_derechos": solicitudes,
        }

    def anonimizar_cuenta(self, user_id, password_confirm):
        """
        Anonimiza la cuenta del usuario (derecho de supresión).
        - Nombre → "Usuario eliminado"
        - Email → dirección única inválida
        - Contraseña inutilizada
        - Foto y teléfono vacíos
        - activo=False, estadoCuenta="Suspendida"
        - Borra ConversacionesChatbot y datos de chat
        - Si RETENER_HISTORIA_CLINICA=True: conserva anamnesis, prediagnosticos, documentos clínicos, facturas
        Retorna (success, message)
        """
        from django.conf import settings
        from django.utils import timezone
        from django.db import transaction
        from apps.chatbot.models import ConversacionesChatbot, MensajesChat
        from apps.authentication.models import Register
        from apps.authentication.security import SecurityHelper

        try:
            user = Register.objects.get(idUsuario=user_id)
        except Register.DoesNotExist:
            return False, "Usuario no encontrado"

        # Verificar contraseña
        if not SecurityHelper.verify_password(password_confirm, user.contrasena):
            return False, "Contraseña incorrecta"

        # Verificar RETENER_HISTORIA_CLINICA
        retener = getattr(settings, "RETENER_HISTORIA_CLINICA", True)

        with transaction.atomic():
            # 1. Borrar conversaciones chatbot y mensajes chat
            ConversacionesChatbot.objects.filter(idPaciente_id=user_id).delete()
            from apps.chatbot.models import MensajesChat
            MensajesChat.objects.filter(
                models.Q(idEmisor_id=user_id) | models.Q(idReceptor_id=user_id)
            ).delete()

            # 2. Si no retener historia clínica, borrar datos clínicos
            if not retener:
                from apps.patients.models import EvolucionPaciente, Anamnesis, Familiar, PrediagnosticoChatbot
                from apps.documents.models import DocumentosClinicos, DocumentosPaciente
                from apps.scheduling.models import Citas
                from apps.billing.models import Facturas, ItemsFactura

                EvolucionPaciente.objects.filter(idPaciente_id=user_id).delete()
                PrediagnosticoChatbot.objects.filter(idPaciente_id=user_id).delete()
                Familiar.objects.filter(idAnamnesis__idPaciente_id=user_id).delete()
                Anamnesis.objects.filter(idPaciente_id=user_id).delete()
                DocumentosPaciente.objects.filter(idPaciente_id=user_id).delete()
                DocumentosClinicos.objects.filter(idPaciente_id=user_id).delete()
                Citas.objects.filter(idPaciente_id=user_id).delete()
                ItemsFactura.objects.filter(idFactura__idPaciente_id=user_id).delete()
                Facturas.objects.filter(idPaciente_id=user_id).delete()
            else:
                # Solo anonimizar citas futuras
                from apps.scheduling.models import Citas
                Citas.objects.filter(
                    idPaciente_id=user_id,
                    fecha__gte=timezone.now().date()
                ).delete()

            # 3. Anonimizar usuario
            email_anonimo = f"usuario_eliminado_{user_id}@{timezone.now().timestamp()}.invalid"
            user.nombre = "Usuario eliminado"
            user.email = email_anonimo
            user.contrasena = "!"  # Contraseña inutilizada
            user.fotoPerfil = None
            user.activo = False
            user.estadoCuenta = "Suspendida"
            user.email_verificado = False
            user.save(update_fields=[
                "nombre", "email", "password", "fotoPerfil",
                "activo", "estadoCuenta", "email_verificado"
            ])

            # 4. Limpiar perfil
            from apps.patients.models import PerfilPaciente
            PerfilPaciente.objects.filter(idPaciente_id=user_id).update(
                numeroTelefonico=None,
                consentimientoDatos=False,
                consentimiento_chatbot=False,
            )

            # 5. Crear solicitud de derechos de supresión
            from apps.patients.models import SolicitudDerechos
            SolicitudDerechos.objects.create(
                idUsuario_id=user_id,
                tipo="supresion",
                descripcion="Solicitud de eliminación de cuenta por parte del titular",
                estado="respondida",
                fechaLimite=timezone.now().date(),
                fechaRespuesta=timezone.now(),
                respuesta="Cuenta anonimizada y suspendida según derecho de supresión (Ley 1581/2012)"
            )

            return True, "Cuenta anonimizada y suspendida. Los datos de historia clínica se conservan según configuración RETENER_HISTORIA_CLINICA."
