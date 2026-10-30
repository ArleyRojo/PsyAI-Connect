from django.db import models
from django.db.models import Q, Count, Value, CharField
from django.db.models.functions import Lower, Coalesce
from django.utils import timezone

from apps.authentication.models import Register
from apps.professionals.models import PerfilProfesional, PacientesProfesional, Reportes, Diagnostico
from apps.patients.models import EvolucionPaciente, PerfilPaciente


class ProfessionalRepository:
    def get_professional_profile(self, user_id):
        try:
            user = Register.objects.get(idUsuario=user_id)
        except Register.DoesNotExist:
            return None
        try:
            perfil = PerfilProfesional.objects.get(idProfesional=user_id)
        except PerfilProfesional.DoesNotExist:
            perfil = None
        return {
            "nombre": user.nombre,
            "email": user.email,
            "fotoPerfil": user.fotoPerfil,
            "fechaRegistro": user.fechaRegistro,
            "especialidad": perfil.especialidad if perfil else None,
            "tarjetaProfesional": perfil.tarjetaProfesional if perfil else None,
            "numeroRethus": perfil.numeroRethus if perfil else None,
            "experiencia": perfil.experiencia if perfil else None,
            "estado": perfil.estado if perfil else None,
            "edad": perfil.edad if perfil else None,
            "genero": perfil.genero if perfil else None,
            "verificado": perfil.verificado if perfil else False,
            "fechaVerificacion": perfil.fechaVerificacion if perfil else None,
            "verificadoPor": perfil.verificadoPor_id if perfil else None,
        }

    def update_professional_profile(self, data):
        user_id = data.get("idUsuario")
        perfil = PerfilProfesional.objects.filter(idProfesional=user_id).first()
        if perfil:
            perfil.especialidad = data.get("especialidad", perfil.especialidad)
            perfil.tarjetaProfesional = data.get("tarjetaProfesional", perfil.tarjetaProfesional)
            perfil.numeroRethus = data.get("numeroRethus", perfil.numeroRethus)
            perfil.experiencia = data.get("experiencia", perfil.experiencia)
            perfil.save(update_fields=["especialidad", "tarjetaProfesional", "numeroRethus", "experiencia"])

    def list_professional_patients(self, professional_id):
        from django.db.models import OuterRef, Subquery

        latest_diag_subquery = Diagnostico.objects.filter(
            idAsignacion__idProfesional_id=professional_id,
            idAsignacion__idPaciente_id=OuterRef('idPaciente_id')
        ).exclude(diagnostico__isnull=True).exclude(diagnostico="").order_by('-fechaDiagnostico', '-fecha')

        assigned_patients = PacientesProfesional.objects.filter(
            idProfesional_id=professional_id
        ).select_related('idPaciente').order_by('idPaciente__nombre')

        perfil_data = {
            p.idPaciente_id: p
            for p in PerfilPaciente.objects.filter(
                idPaciente_id__in=assigned_patients.values_list('idPaciente_id', flat=True)
            )
        }

        result = []
        for pp in assigned_patients:
            if not pp.idPaciente:
                continue
            p = perfil_data.get(pp.idPaciente_id)
            latest_diag = Diagnostico.objects.filter(
                idAsignacion__idProfesional_id=professional_id,
                idAsignacion__idPaciente_id=pp.idPaciente_id
            ).exclude(diagnostico__isnull=True).exclude(diagnostico="").order_by('-fechaDiagnostico', '-fecha').first()

            result.append({
                "idUsuario": pp.idPaciente.idUsuario,
                "nombre": pp.idPaciente.nombre,
                "fotoPerfil": pp.idPaciente.fotoPerfil,
                "edad": p.edad if p else None,
                "genero": p.genero if p else None,
                "contacto": (p.numeroTelefonico if p and p.numeroTelefonico else pp.idPaciente.email),
                "ultimoDiagnostico": latest_diag.diagnostico if latest_diag else None,
            })
        return result

    def list_patients_for_chat(self):
        # Solo profesionales verificados
        perfil_data = {
            p.idPaciente_id: p
            for p in PerfilPaciente.objects.all()
        }
        users = Register.objects.filter(rol="paciente").order_by("nombre")
        return [
            {
                "idUsuario": u.idUsuario,
                "nombre": u.nombre,
                "fotoPerfil": u.fotoPerfil,
                "edad": perfil_data.get(u.idUsuario, None)
                and perfil_data[u.idUsuario].edad,
                "genero": perfil_data.get(u.idUsuario, None)
                and perfil_data[u.idUsuario].genero,
                "contacto": (
                    perfil_data[u.idUsuario].numeroTelefonico
                    if perfil_data.get(u.idUsuario) and perfil_data[u.idUsuario].numeroTelefonico
                    else u.email
                ),
            }
            for u in users
        ]

    def list_verified_professionals(self):
        """Lista solo profesionales verificados para el chat."""
        professionals = Register.objects.filter(
            rol="profesional",
            perfil_profesional__verificado=True
        ).order_by("nombre")
        return [
            {
                "idUsuario": u.idUsuario,
                "nombre": u.nombre,
                "fotoPerfil": u.fotoPerfil,
                "especialidad": u.perfil_profesional.especialidad if hasattr(u, 'perfil_profesional') and u.perfil_profesional else None,
                "fotoPerfil": u.fotoPerfil,
            }
            for u in professionals
        ]

    def save_diagnosis(self, professional_id, data):
        from django.db import transaction
        with transaction.atomic():
            asignacion, _ = PacientesProfesional.objects.get_or_create(
                idProfesional_id=professional_id,
                idPaciente_id=data.get("idPaciente"),
            )
            fecha_diag = data.get("fecha_diagnostico")
            if not fecha_diag:
                fecha_diag = timezone.localdate()
            elif isinstance(fecha_diag, str):
                try:
                    fecha_diag = date.fromisoformat(fecha_diag)
                except Exception:
                    fecha_diag = timezone.localdate()

            return Diagnostico.objects.create(
                idAsignacion=asignacion,
                sintomas=data.get("sintomas"),
                diagnostico=data.get("diagnostico"),
                tratamiento=data.get("tratamiento"),
                fechaDiagnostico=fecha_diag,
            )

    def get_diagnosis_history(self, professional_id):
        rows = (
            Diagnostico.objects.filter(
                idAsignacion__idProfesional_id=professional_id,
            )
            .exclude(diagnostico__isnull=True)
            .exclude(diagnostico="")
            .select_related("idAsignacion__idPaciente")
            .order_by("-fechaDiagnostico", "-fecha")
        )
        return [
            {
                "paciente": r.idAsignacion.idPaciente.nombre if (r.idAsignacion and r.idAsignacion.idPaciente) else None,
                "fechaRaw": r.fechaDiagnostico,
                "sintomas": r.sintomas,
                "diagnostico": r.diagnostico,
                "tratamiento": r.tratamiento,
            }
            for r in rows
        ]

    def get_report_overview(self, professional_id):
        stats = (
            Reportes.objects.filter(
                idProfesional_id=professional_id,
                eliminado=False,
            )
            .aggregate(
                total=Count("idReporte"),
                completados=Count("idReporte", filter=Q(estado="Completado")),
                pendientes=Count("idReporte", filter=Q(estado="Pendiente")),
            )
        )
        reportes_rows = (
            Reportes.objects.filter(
                idProfesional_id=professional_id,
                eliminado=False,
            )
            .select_related("idPaciente")
            .order_by("-fechaInicio")
        )
        reportes = [
            {
                "idReporte": r.idReporte,
                "idPaciente": r.idPaciente_id,
                "tipoReporte": r.tipoReporte,
                "estado": r.estado,
                "fechaInicio": r.fechaInicio.strftime("%d/%m/%Y") if r.fechaInicio else None,
                "fechaFin": r.fechaFin.strftime("%d/%m/%Y") if r.fechaFin else None,
                "sintomas": r.sintomas,
                "diagnostico": r.diagnostico,
                "tratamiento": r.tratamiento,
                "paciente": r.idPaciente.nombre if r.idPaciente else "General",
            }
            for r in reportes_rows
        ]
        pacientes = (
            Register.objects.filter(
                rol="paciente",
                pacientes_asignados__idProfesional_id=professional_id,
            )
            .exclude(
                pacientes_asignados__idProfesional_id=professional_id,
                pacientes_asignados__idPaciente__isnull=False,
            )
            .distinct()
            .values("idUsuario", "nombre")
        )
        return {"stats": stats, "reportes": reportes, "pacientes": list(pacientes)}

    def create_report(self, professional_id, data):
        Reportes.objects.create(
            idProfesional_id=professional_id,
            idPaciente_id=data.get("idPaciente") or None,
            tipoReporte=data.get("tipoReporte"),
            fechaInicio=data.get("fechaInicio") or None,
            fechaFin=data.get("fechaFin") or None,
            sintomas=data.get("sintomas"),
            diagnostico=data.get("diagnostico"),
            tratamiento=data.get("tratamiento"),
            estado="Completado",
        )

    def get_latest_patient_diagnosis(self, professional_id, patient_id):
        latest = (
            Diagnostico.objects.filter(
                idAsignacion__idProfesional_id=professional_id,
                idAsignacion__idPaciente_id=patient_id,
            )
            .exclude(diagnostico__isnull=True)
            .exclude(diagnostico="")
            .order_by("-fechaDiagnostico")
            .first()
        )
        if latest:
            return {"sintomas": latest.sintomas, "diagnostico": latest.diagnostico, "tratamiento": latest.tratamiento}
        return None

    def update_report(self, professional_id, data):
        report = Reportes.objects.filter(
            idReporte=data.get("idReporte"),
            idProfesional_id=professional_id,
        ).first()
        if report:
            report.tipoReporte = data.get("tipoReporte", report.tipoReporte)
            report.estado = data.get("estado", report.estado)
            report.save(update_fields=["tipoReporte", "estado"])

    def delete_report(self, professional_id, report_id):
        report = Reportes.objects.filter(
            idReporte=report_id,
            idProfesional_id=professional_id,
        ).first()
        if report:
            report.eliminado = True
            report.save(update_fields=["eliminado"])

    def get_deleted_reports(self, professional_id):
        rows = (
            Reportes.objects.filter(
                idProfesional_id=professional_id,
                eliminado=True,
            )
            .select_related("idPaciente")
            .order_by("-fechaInicio")
        )
        return [
            {
                "idReporte": r.idReporte,
                "idPaciente": r.idPaciente_id,
                "tipoReporte": r.tipoReporte,
                "estado": r.estado,
                "fechaInicio": r.fechaInicio.strftime("%d/%m/%Y") if r.fechaInicio else None,
                "fechaFin": r.fechaFin.strftime("%d/%m/%Y") if r.fechaFin else None,
                "paciente": r.idPaciente.nombre if r.idPaciente else "General",
            }
            for r in rows
        ]

    def get_all_patient_evolution(self, professional_id):
        rows = (
            EvolucionPaciente.objects.select_related("idPaciente")
            .filter(idPaciente__rol="paciente")
            .order_by("-fecha")
        )
        return [
            {
                "idEvolucion": e.idEvolucion,
                "idPaciente": e.idPaciente_id,
                "estadoEmocional": e.estadoEmocional,
                "nivelEnergia": e.nivelEnergia,
                "notasPersonales": e.notasPersonales,
                "fecha": e.fecha.strftime("%d/%m/%Y") if e.fecha else None,
                "fechaRaw": e.fecha,
                "paciente": e.idPaciente.nombre if e.idPaciente else None,
            }
            for e in rows
        ]

    def professional_has_patient(self, professional_id, patient_id):
        return PacientesProfesional.objects.filter(
            idProfesional_id=professional_id,
            idPaciente_id=patient_id,
        ).exclude(
            Q(idPaciente__isnull=True)
        ).exists()

    def patient_can_view_payment_info(self, professional_id, patient_id):
        """
        Return True if the patient has at least one relationship with the professional:
        - PacientesProfesional row (assigned patient)
        - Cita (appointment) in Citas table
        - Factura (invoice) in Facturas table
        """
        # 1. Check PacientesProfesional assignment
        if PacientesProfesional.objects.filter(
            idProfesional_id=professional_id,
            idPaciente_id=patient_id,
        ).exists():
            return True

        # 2. Check Citas (appointments)
        try:
            from apps.scheduling.models import Citas
            if Citas.objects.filter(
                idProfesional_id=professional_id,
                idPaciente_id=patient_id,
            ).exists():
                return True
        except (ImportError, LookupError):
            pass

        # 3. Check Facturas (invoices)
        try:
            from apps.billing.models import Facturas
            if Facturas.objects.filter(
                idProfesional_id=professional_id,
                idPaciente_id=patient_id,
            ).exists():
                return True
        except (ImportError, LookupError):
            pass

        return False

    def get_dashboard_stats(self, professional_id):
        from django.db.models import Count, Q, F, Value, CharField
        from django.db.models.functions import Coalesce
        from datetime import timedelta
        from django.utils import timezone

        today = timezone.localdate()
        week_later = today + timedelta(days=7)
        month_ago = today - timedelta(days=30)
        two_weeks_ago = today - timedelta(days=14)

        try:
            from apps.scheduling.models import Citas
            citas_qs = Citas.objects.filter(idProfesional_id=professional_id)
            stats_citas = citas_qs.aggregate(
                pacientes_activos=Count(
                    "idPaciente", filter=~Q(estado="Cancelada"), distinct=True
                ),
                citas_hoy=Count(
                    "idCita", filter=Q(fecha=today, estado__in=["Pendiente", "Confirmada", "Completada"])
                ),
                citas_pendientes=Count(
                    "idCita", filter=Q(estado="Pendiente")
                ),
            )

            actividades_qs = (
                citas_qs.filter(estado__in=["Pendiente", "Confirmada", "Completada"])
                .select_related("idPaciente")
                .order_by("-fecha", "-hora")[:3]
            )
            actividades = [
                {
                    "paciente": c.idPaciente.nombre if c.idPaciente else None,
                    "fecha": c.fecha,
                    "hora": c.hora,
                    "tipoCita": c.tipoCita,
                    "estado": c.estado,
                    "idCita": c.idCita,
                }
                for c in actividades_qs
            ]

            proximas_qs = (
                citas_qs.filter(
                    estado__in=["Pendiente", "Confirmada"],
                    fecha__gte=today,
                    fecha__lte=week_later,
                )
                .select_related("idPaciente")
                .order_by("fecha", "hora")[:10]
            )
            proximas_citas = [
                {
                    "idCita": c.idCita,
                    "paciente": c.idPaciente.nombre if c.idPaciente else None,
                    "idPaciente": c.idPaciente_id,
                    "fotoPerfil": c.idPaciente.fotoPerfil if c.idPaciente else None,
                    "fecha": c.fecha,
                    "hora": c.hora,
                    "tipoCita": c.tipoCita,
                    "estado": c.estado,
                }
                for c in proximas_qs
            ]

            citas_no_canceladas = citas_qs.exclude(estado="Cancelada")

        except (ImportError, LookupError):
            stats_citas = {
                "pacientes_activos": 0,
                "citas_hoy": 0,
                "citas_pendientes": 0,
            }
            actividades = []
            proximas_citas = []
            citas_no_canceladas = None

        reportes_stats = Reportes.objects.filter(
            idProfesional_id=professional_id, eliminado=False
        ).aggregate(
            total=Count("idReporte"),
            completados=Count("idReporte", filter=Q(estado="Completado")),
            pendientes=Count("idReporte", filter=Q(estado="Pendiente")),
        )

        evolucion_data = None
        emocion_data = None
        if citas_no_canceladas is not None:
            pacientes_con_citas = citas_no_canceladas.values("idPaciente").distinct().count()
            citas_paciente_ids = citas_no_canceladas.values_list("idPaciente", flat=True).distinct()
            pacientes_con_evolucion = (
                EvolucionPaciente.objects.filter(
                    idPaciente_id__in=citas_paciente_ids,
                    fecha__gte=two_weeks_ago,
                ).values("idPaciente").distinct().count()
            )
            pacientes_sin_evolucion = pacientes_con_citas - pacientes_con_evolucion

            emocion_data = EvolucionPaciente.objects.filter(
                idPaciente_id__in=citas_paciente_ids,
                fecha__gte=month_ago,
            ).aggregate(
                nivel_energia_promedio=models.Avg("nivelEnergia"),
                total_registros=Count("idEvolucion"),
            )

            evolucion_data = {
                "pacientes_con_citas": pacientes_con_citas,
                "pacientes_con_evolucion_reciente": pacientes_con_evolucion,
                "pacientes_sin_evolucion": pacientes_sin_evolucion,
            }

        alertas = []
        try:
            if citas_no_canceladas is not None:
                por_confirmar_hoy = citas_no_canceladas.filter(
                    estado="Pendiente", fecha=today
                ).count()
                por_confirmar_proximas = citas_no_canceladas.filter(
                    estado="Pendiente",
                    fecha__gt=today,
                    fecha__lte=today + timedelta(days=3),
                ).count()
                if por_confirmar_hoy:
                    alertas.append({
                        "tipo": "warning", "icono": "fa-clock",
                        "titulo": "Citas por confirmar hoy",
                        "mensaje": f"{por_confirmar_hoy} cita(s) pendiente(s) de confirmación",
                        "accion": "ver_agenda",
                    })
                if por_confirmar_proximas:
                    alertas.append({
                        "tipo": "info", "icono": "fa-calendar-day",
                        "titulo": "Citas por confirmar (próx. 3 días)",
                        "mensaje": f"{por_confirmar_proximas} cita(s) pendiente(s)",
                        "accion": "ver_agenda",
                    })
        except Exception:
            pass

        reportes_pendientes = Reportes.objects.filter(
            idProfesional_id=professional_id,
            estado="Pendiente",
            eliminado=False,
        ).count()
        if reportes_pendientes:
            alertas.append({
                "tipo": "warning", "icono": "fa-file-text",
                "titulo": "Reportes pendientes",
                "mensaje": f"{reportes_pendientes} reporte(s) por completar",
                "accion": "ver_reportes",
            })

        if evolucion_data and evolucion_data.get("pacientes_sin_evolucion", 0) > 0:
            alertas.append({
                "tipo": "info", "icono": "fa-heart-pulse",
                "titulo": "Pacientes sin evolución reciente",
                "mensaje": f"{evolucion_data['pacientes_sin_evolucion']} paciente(s) sin registro en 14 días",
                "accion": "ver_pacientes",
            })

        nivel_energia = None
        total_registros = 0
        if emocion_data:
            nivel_energia = (
                round(emocion_data["nivel_energia_promedio"], 1)
                if emocion_data.get("nivel_energia_promedio") else None
            )
            total_registros = emocion_data.get("total_registros") or 0

        return {
            "pacientes_activos": stats_citas.get("pacientes_activos") or 0,
            "citas_hoy": stats_citas.get("citas_hoy") or 0,
            "citas_pendientes": stats_citas.get("citas_pendientes") or 0,
            "actividades": actividades,
            "proximas_citas": proximas_citas,
            "reportes": {
                "total": reportes_stats.get("total") or 0,
                "completados": reportes_stats.get("completados") or 0,
                "pendientes": reportes_stats.get("pendientes") or 0,
            },
            "evolucion": {
                "pacientes_con_citas": evolucion_data["pacientes_con_citas"] if evolucion_data else 0,
                "pacientes_con_evolucion_reciente": evolucion_data["pacientes_con_evolucion_reciente"] if evolucion_data else 0,
                "pacientes_sin_evolucion": evolucion_data["pacientes_sin_evolucion"] if evolucion_data else 0,
                "nivel_energia_promedio": nivel_energia,
                "total_registros": total_registros,
            } if evolucion_data else None,
            "alertas": alertas,
        }
