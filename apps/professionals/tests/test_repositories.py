import pytest
from datetime import date, timedelta

from apps.authentication.models import Register
from apps.professionals.models import PerfilProfesional, PacientesProfesional, Reportes, Diagnostico
from apps.professionals.repositories import ProfessionalRepository
from apps.patients.models import PerfilPaciente


@pytest.fixture
def repo():
    return ProfessionalRepository()


@pytest.fixture
def professional_user(django_user_model):
    return django_user_model.objects.create_user(
        email="pro@test.com",
        nombre="Dr. García",
        password="TestPass123",
        rol="profesional",
    )


@pytest.fixture
def patient_user(django_user_model):
    return django_user_model.objects.create_user(
        email="pac@test.com",
        nombre="Juan Pérez",
        password="TestPass123",
        rol="paciente",
    )


@pytest.fixture
def professional_profile(professional_user):
    return PerfilProfesional.objects.create(
        idProfesional=professional_user,
        especialidad="Psicología Clínica",
        tarjetaProfesional="TAR-12345",
        numeroRethus="RETHUS-12345",
        experiencia="10 años",
    )


@pytest.fixture
def patient_profile(patient_user):
    return PerfilPaciente.objects.create(
        idPaciente=patient_user,
        genero="M",
        edad=30,
        numeroTelefonico="3001234567",
    )


@pytest.fixture
def professional_patient(professional_user, patient_user):
    return PacientesProfesional.objects.create(
        idProfesional=professional_user,
        idPaciente=patient_user,
    )


# ── get_professional_profile ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestGetProfessionalProfile:
    def test_returns_dict(self, repo, professional_user, professional_profile):
        result = repo.get_professional_profile(professional_user.idUsuario)
        assert isinstance(result, dict)
        assert result["nombre"] == "Dr. García"
        assert result["especialidad"] == "Psicología Clínica"
        assert result["tarjetaProfesional"] == "TAR-12345"

    def test_returns_none_when_not_found(self, repo):
        result = repo.get_professional_profile(9999)
        assert result is None

    def test_user_without_profile(self, repo, professional_user):
        result = repo.get_professional_profile(professional_user.idUsuario)
        assert result is not None
        assert result["especialidad"] is None
        assert result["tarjetaProfesional"] is None


# ── update_professional_profile ──────────────────────────────────────────────


@pytest.mark.django_db
class TestUpdateProfessionalProfile:
    def test_updates_especialidad(self, repo, professional_user, professional_profile):
        repo.update_professional_profile({
            "idUsuario": professional_user.idUsuario,
            "especialidad": "Neuropsicología",
        })
        professional_profile.refresh_from_db()
        assert professional_profile.especialidad == "Neuropsicología"

    def test_updates_tarjeta_profesional(self, repo, professional_user, professional_profile):
        repo.update_professional_profile({
            "idUsuario": professional_user.idUsuario,
            "tarjetaProfesional": "TAR-99999",
        })
        professional_profile.refresh_from_db()
        assert professional_profile.tarjetaProfesional == "TAR-99999"

    def test_updates_numero_rethus(self, repo, professional_user, professional_profile):
        repo.update_professional_profile({
            "idUsuario": professional_user.idUsuario,
            "numeroRethus": "RETHUS-99999",
        })
        professional_profile.refresh_from_db()
        assert professional_profile.numeroRethus == "RETHUS-99999"

    def test_updates_experiencia(self, repo, professional_user, professional_profile):
        repo.update_professional_profile({
            "idUsuario": professional_user.idUsuario,
            "experiencia": "5 años",
        })
        professional_profile.refresh_from_db()
        assert professional_profile.experiencia == "5 años"

    def test_no_profile_exists(self, repo, professional_user):
        repo.update_professional_profile({
            "idUsuario": professional_user.idUsuario,
            "especialidad": "Test",
        })


# ── list_professional_patients ───────────────────────────────────────────────


@pytest.mark.django_db
class TestListProfessionalPatients:
    def test_returns_list(self, repo, professional_user, patient_user, professional_patient, patient_profile):
        result = repo.list_professional_patients(professional_user.idUsuario)
        assert isinstance(result, list)

    def test_includes_patient_info(self, repo, professional_user, patient_user, professional_patient, patient_profile):
        result = repo.list_professional_patients(professional_user.idUsuario)
        assert len(result) > 0
        patient_data = next(p for p in result if p["idUsuario"] == patient_user.idUsuario)
        assert patient_data["nombre"] == "Juan Pérez"
        assert patient_data["edad"] == 30


# ── save_diagnosis / get_diagnosis_history ───────────────────────────────────


@pytest.mark.django_db
class TestDiagnosisCRUD:
    def test_save_creates_diagnosis(self, repo, professional_user, patient_user, professional_patient):
        data = {
            "idPaciente": patient_user.idUsuario,
            "sintomas": "Ansiedad generalizada",
            "diagnostico": "Trastorno de Ansiedad",
            "tratamiento": "Terapia cognitivo-conductual",
            "fecha_diagnostico": date.today(),
        }
        repo.save_diagnosis(professional_user.idUsuario, data)

        d = Diagnostico.objects.filter(
            idAsignacion__idProfesional=professional_user,
            idAsignacion__idPaciente=patient_user,
        ).first()
        assert d is not None
        assert d.sintomas == "Ansiedad generalizada"
        assert d.diagnostico == "Trastorno de Ansiedad"

    def test_save_accumulates_diagnoses(self, repo, professional_user, patient_user, professional_patient):
        data = {
            "idPaciente": patient_user.idUsuario,
            "sintomas": "Ansiedad",
            "diagnostico": "TAD",
            "tratamiento": "Terapia",
            "fecha_diagnostico": date.today(),
        }
        repo.save_diagnosis(professional_user.idUsuario, data)

        data["sintomas"] = "Ansiedad severa"
        repo.save_diagnosis(professional_user.idUsuario, data)

        diagnosticos = Diagnostico.objects.filter(
            idAsignacion__idProfesional=professional_user,
            idAsignacion__idPaciente=patient_user,
        )
        assert diagnosticos.count() == 2

    def test_get_history_returns_list(self, repo, professional_user, patient_user, professional_patient):
        data = {
            "idPaciente": patient_user.idUsuario,
            "sintomas": "Ansiedad",
            "diagnostico": "TAD",
            "tratamiento": "Terapia",
            "fecha_diagnostico": date.today(),
        }
        repo.save_diagnosis(professional_user.idUsuario, data)

        history = repo.get_diagnosis_history(professional_user.idUsuario)
        assert isinstance(history, list)
        assert len(history) == 1
        assert history[0]["diagnostico"] == "TAD"

    def test_history_excludes_empty_diagnosis(self, repo, professional_user, patient_user, professional_patient):
        data = {
            "idPaciente": patient_user.idUsuario,
            "sintomas": "Ninguno",
            "diagnostico": "",
            "tratamiento": "Ninguno",
            "fecha_diagnostico": date.today(),
        }
        repo.save_diagnosis(professional_user.idUsuario, data)

        history = repo.get_diagnosis_history(professional_user.idUsuario)
        assert len(history) == 0


# ── create_report / get_report_overview ──────────────────────────────────────


@pytest.mark.django_db
class TestReportCRUD:
    def test_create_report(self, repo, professional_user, patient_user, professional_patient):
        data = {
            "idPaciente": patient_user.idUsuario,
            "tipoReporte": "general",
            "fechaInicio": date.today(),
            "fechaFin": date.today() + timedelta(days=7),
            "sintomas": "Insomnio",
            "diagnostico": "Insomnio crónico",
            "tratamiento": "Higiene del sueño",
        }
        repo.create_report(professional_user.idUsuario, data)

        report = Reportes.objects.get(
            idProfesional=professional_user,
            idPaciente=patient_user,
        )
        assert report.tipoReporte == "general"
        assert report.estado == "Completado"

    def test_create_report_without_patient(self, repo, professional_user):
        data = {
            "tipoReporte": "general",
            "fechaInicio": date.today(),
        }
        repo.create_report(professional_user.idUsuario, data)

        report = Reportes.objects.get(idProfesional=professional_user)
        assert report.idPaciente is None

    def test_get_report_overview(self, repo, professional_user, patient_user, professional_patient):
        data = {
            "idPaciente": patient_user.idUsuario,
            "tipoReporte": "general",
            "fechaInicio": date.today(),
        }
        repo.create_report(professional_user.idUsuario, data)

        overview = repo.get_report_overview(professional_user.idUsuario)
        assert "stats" in overview
        assert "reportes" in overview
        assert overview["stats"]["total"] == 1

    def test_update_report(self, repo, professional_user, patient_user, professional_patient):
        data = {
            "idPaciente": patient_user.idUsuario,
            "tipoReporte": "general",
            "fechaInicio": date.today(),
        }
        repo.create_report(professional_user.idUsuario, data)

        report = Reportes.objects.get(idProfesional=professional_user)
        repo.update_report(professional_user.idUsuario, {
            "idReporte": report.idReporte,
            "tipoReporte": "evolución",
            "estado": "Pendiente",
        })

        report.refresh_from_db()
        assert report.tipoReporte == "evolución"
        assert report.estado == "Pendiente"

    def test_delete_report(self, repo, professional_user, patient_user, professional_patient):
        data = {
            "idPaciente": patient_user.idUsuario,
            "tipoRepote": "general",
            "fechaInicio": date.today(),
        }
        repo.create_report(professional_user.idUsuario, data)

        report = Reportes.objects.get(idProfesional=professional_user)
        repo.delete_report(professional_user.idUsuario, report.idReporte)

        report.refresh_from_db()
        assert report.eliminado is True


# ── get_deleted_reports ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestGetDeletedReports:
    def test_returns_soft_deleted(self, repo, professional_user, patient_user, professional_patient):
        Reportes.objects.create(
            idProfesional=professional_user,
            idPaciente=patient_user,
            tipoReporte="general",
            fechaInicio=date.today(),
            eliminado=True,
        )

        result = repo.get_deleted_reports(professional_user.idUsuario)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["tipoReporte"] == "general"

    def test_excludes_non_deleted(self, repo, professional_user, patient_user, professional_patient):
        Reportes.objects.create(
            idProfesional=professional_user,
            idPaciente=patient_user,
            tipoReporte="general",
            fechaInicio=date.today(),
            eliminado=False,
        )

        result = repo.get_deleted_reports(professional_user.idUsuario)
        assert len(result) == 0

    def test_empty_when_none_deleted(self, repo, professional_user):
        result = repo.get_deleted_reports(professional_user.idUsuario)
        assert result == []


# ── patient_can_view_payment_info ───────────────────────────────────────────────


@pytest.mark.django_db
class TestPatientCanViewPaymentInfo:
    def test_with_asignacion_returns_true(self, repo, professional_user, patient_user):
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(
            idProfesional=professional_user, idPaciente=patient_user
        )
        assert repo.patient_can_view_payment_info(professional_user.idUsuario, patient_user.idUsuario) is True

    def test_without_asignacion_returns_false(self, repo, professional_user, patient_user):
        assert repo.patient_can_view_payment_info(professional_user.idUsuario, patient_user.idUsuario) is False

    def test_with_cita_returns_true(self, repo, professional_user, patient_user):
        from apps.scheduling.models import Citas
        from datetime import date, time
        Citas.objects.create(
            idPaciente=patient_user,
            idProfesional=professional_user,
            fecha=date.today(),
            hora=time(10, 0),
            estado="Confirmada",
        )
        assert repo.patient_can_view_payment_info(professional_user.idUsuario, patient_user.idUsuario) is True

    def test_with_factura_returns_true(self, repo, professional_user, patient_user):
        from apps.billing.models import Facturas
        Facturas.objects.create(
            idPaciente=patient_user,
            idProfesional=professional_user,
            monto=50000,
            estadoPago="Pendiente",
        )
        assert repo.patient_can_view_payment_info(professional_user.idUsuario, patient_user.idUsuario) is True

    def test_other_patient_returns_false(self, repo, professional_user, patient_user):
        from apps.authentication.models import Register
        other_patient = Register.objects.create_user(
            email="other@test.com", password="pass", nombre="Otro", rol="paciente"
        )
        # First patient has factura
        from apps.billing.models import Facturas
        Facturas.objects.create(
            idPaciente=patient_user,
            idProfesional=professional_user,
            monto=50000,
            estadoPago="Pendiente",
        )
        # Other patient should not have access
        assert repo.patient_can_view_payment_info(professional_user.idUsuario, other_patient.idUsuario) is False

    def test_other_profesional_returns_false(self, repo, professional_user, patient_user):
        from apps.authentication.models import Register
        other_prof = Register.objects.create_user(
            email="otherprof@test.com", password="pass", nombre="Otro Prof", rol="profesional"
        )
        # Patient has factura with first professional
        from apps.billing.models import Facturas
        Facturas.objects.create(
            idPaciente=patient_user,
            idProfesional=professional_user,
            monto=50000,
            estadoPago="Pendiente",
        )
        # Should not have access to other professional's info
        assert repo.patient_can_view_payment_info(other_prof.idUsuario, patient_user.idUsuario) is False

    def test_cita_with_other_profesional_returns_false(self, repo, professional_user, patient_user):
        from apps.authentication.models import Register
        from apps.scheduling.models import Citas
        from datetime import date, time
        other_prof = Register.objects.create_user(
            email="otherprof@test.com", password="pass", nombre="Otro Prof", rol="profesional"
        )
        # Patient has cita with OTHER professional
        Citas.objects.create(
            idPaciente=patient_user,
            idProfesional=other_prof,
            fecha=date.today(),
            hora=time(10, 0),
            estado="Confirmada",
        )
        # Should not have access to this professional's info
        assert repo.patient_can_view_payment_info(professional_user.idUsuario, patient_user.idUsuario) is False

    def test_factura_with_other_profesional_returns_false(self, repo, professional_user, patient_user):
        from apps.authentication.models import Register
        from apps.billing.models import Facturas
        other_prof = Register.objects.create_user(
            email="otherprof@test.com", password="pass", nombre="Otro Prof", rol="profesional"
        )
        # Patient has factura with OTHER professional
        Facturas.objects.create(
            idPaciente=patient_user,
            idProfesional=other_prof,
            monto=50000,
            estadoPago="Pendiente",
        )
        # Should not have access to this professional's info
        assert repo.patient_can_view_payment_info(professional_user.idUsuario, patient_user.idUsuario) is False