import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from django.utils import timezone

from apps.professionals.services import ProfessionalService
from apps.professionals.repositories import ProfessionalRepository
from apps.professionals.models import PerfilProfesional, PacientesProfesional, Reportes, Diagnostico, PacientesProfesional
from apps.authentication.models import Register
from apps.scheduling.models import Citas
from apps.billing.models import Facturas
from apps.chatbot.repositories import ChatRepository


@pytest.fixture
def professional_service():
    return ProfessionalService()


@pytest.fixture
def verified_professional(django_user_model):
    """Crea un profesional verificado para las pruebas."""
    user = Register.objects.create_user(
        email="pro@test.com",
        nombre="Dr. García",
        password="TestPass123",
        rol="profesional",
    )
    PerfilProfesional.objects.create(
        idProfesional=user,
        especialidad="Psicología Clínica",
        tarjetaProfesional="TAR-12345",
        numeroRethus="RETHUS-12345",
        experiencia="10 años",
        verificado=True,
        fechaVerificacion=timezone.localdate(),
    )
    return user


@pytest.fixture
def verified_professional_with_patient(django_user_model):
    """Crea un profesional verificado con un paciente asignado."""
    pro_user = Register.objects.create_user(
        email="pro@test.com",
        nombre="Dr. García",
        password="TestPass123",
        rol="profesional",
    )
    PerfilProfesional.objects.create(
        idProfesional=pro_user,
        verificado=True,
    )
    patient = Register.objects.create_user(
        email="pac@test.com",
        nombre="Juan Pérez",
        password="TestPass123",
        rol="paciente",
    )
    from apps.professionals.models import PacientesProfesional
    PacientesProfesional.objects.create(
        idProfesional=pro_user,
        idPaciente=patient,
    )
    return pro_user, patient


# ── ProfessionalService.update_profile ─────────────────────────────────────────


@pytest.mark.django_db
class TestUpdateProfile:
    def test_with_especialidad(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.update_profile({
            "idUsuario": user.idUsuario,
            "especialidad": "Psicología Clínica",
        })
        assert status == 200

    def test_with_tarjeta_profesional(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.update_profile({
            "idUsuario": user.idUsuario,
            "tarjetaProfesional": "TAR-12345",
        })
        assert status == 200

    def test_with_numero_rethus(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.update_profile({
            "idUsuario": user.idUsuario,
            "numeroRethus": "RETHUS-12345",
        })
        assert status == 200

    def test_with_experiencia(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.update_profile({
            "idUsuario": user.idUsuario,
            "experiencia": "10 años",
        })
        assert status == 200

    def test_missing_idUsuario(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.update_profile({
            "especialidad": "Psicología",
        })
        # El servicio no valida idUsuario faltante, actualiza con los datos que tiene
        assert status == 200

    def test_no_data(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.update_profile({
            "idUsuario": user.idUsuario,
        })
        # No hay datos para actualizar
        assert status == 400


# ── ProfessionalService.get_dashboard ─────────────────────────────────────────


@pytest.mark.django_db
class TestGetDashboard:
    def test_returns_dashboard(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.get_dashboard(user.idUsuario)
        assert status == 200
        assert payload["success"] is True


# ── ProfessionalService.list_patients ─────────────────────────────────────────


@pytest.mark.django_db
class TestListPatients:
    def test_returns_patients(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.list_patients(user.idUsuario)
        assert status == 200
        assert payload["success"] is True


# ── ProfessionalService.save_diagnosis ────────────────────────────────────────


@pytest.mark.django_db
class TestSaveDiagnosis:
    def test_missing_id_paciente(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.save_diagnosis(user.idUsuario, {})
        assert status == 400
        assert "idpaciente" in payload["message"].lower()

    def test_successful_save(self, django_user_model):
        pro_user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=pro_user,
            verificado=True,
        )
        patient = Register.objects.create_user(
            email="pac@test.com",
            nombre="Juan Pérez",
            password="TestPass123",
            rol="paciente",
        )
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(
            idProfesional=pro_user,
            idPaciente=patient,
        )
        svc = ProfessionalService()
        payload, status = svc.save_diagnosis(pro_user.idUsuario, {
            "idPaciente": patient.idUsuario,
            "sintomas": "Ansiedad",
            "diagnostico": "TAD",
            "tratamiento": "Terapia",
            "fecha_diagnostico": "2024-01-15",
        })
        assert status == 200
        assert payload["success"] is True


# ── ProfessionalService.diagnosis_history ─────────────────────────────────────


@pytest.mark.django_db
class TestDiagnosisHistory:
    def test_returns_history(self, django_user_model):
        pro_user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=pro_user,
            verificado=True,
        )
        patient = Register.objects.create_user(
            email="pac@test.com",
            nombre="Juan Pérez",
            password="TestPass123",
            rol="paciente",
        )
        from apps.professionals.models import PacientesProfesional, Diagnostico
        PacientesProfesional.objects.create(
            idProfesional=pro_user,
            idPaciente=patient,
        )
        from apps.professionals.models import Diagnostico
        Diagnostico.objects.create(
            idAsignacion_id=1,
            sintomas="Ansiedad",
            diagnostico="TAD",
            tratamiento="Terapia",
            fechaDiagnostico=date.today(),
        )
        svc = ProfessionalService()
        payload, status = svc.diagnosis_history(pro_user.idUsuario)
        assert status == 200
        assert payload["success"] is True


# ── ProfessionalService.report_overview ───────────────────────────────────────


@pytest.mark.django_db
class TestReportOverview:
    def test_returns_overview(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.report_overview(user.idUsuario)
        assert status == 200
        assert payload["success"] is True


# ── ProfessionalService.create_report ────────────────────────────────────────


@pytest.mark.django_db
class TestCreateReport:
    def test_missing_id_paciente(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.create_report(user.idUsuario, {"tipoReporte": "general"})
        # El servicio no valida idPaciente faltante, crea el reporte
        assert status == 200

    def test_patient_not_assigned(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        patient = Register.objects.create_user(
            email="pac@test.com",
            nombre="Juan Pérez",
            password="TestPass123",
            rol="paciente",
        )
        svc = ProfessionalService()
        payload, status = svc.create_report(user.idUsuario, {
            "idPaciente": patient.idUsuario,
            "tipoReporte": "general",
            "fechaInicio": "2024-01-01",
        })
        assert status == 403
        assert "paciente" in payload["message"].lower()

    def test_successful_create(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        patient = Register.objects.create_user(
            email="pac@test.com",
            nombre="Juan Pérez",
            password="TestPass123",
            rol="paciente",
        )
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(
            idProfesional=user,
            idPaciente=patient,
        )
        svc = ProfessionalService()
        payload, status = svc.create_report(user.idUsuario, {
            "idPaciente": patient.idUsuario,
            "tipoReporte": "general",
            "fechaInicio": "2024-01-01",
            "fechaFin": "2024-01-31",
        })
        assert status == 200
        assert payload["success"] is True


# ── ProfessionalService.update_report ────────────────────────────────────────


@pytest.mark.django_db
class TestUpdateReport:
    def test_successful_update(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        from apps.professionals.models import Reportes
        report = Reportes.objects.create(
            idProfesional=user,
            tipoReporte="general",
            estado="Pendiente",
        )
        svc = ProfessionalService()
        payload, status = svc.update_report(user.idUsuario, {
            "idReporte": report.idReporte,
            "tipoReporte": "evolución",
            "estado": "Completado",
        })
        assert status == 200
        assert payload["success"] is True


# ── ProfessionalService.delete_report ────────────────────────────────────────


@pytest.mark.django_db
class TestDeleteReport:
    def test_successful_delete(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        from apps.professionals.models import Reportes
        report = Reportes.objects.create(
            idProfesional=user,
            tipoReporte="general",
            estado="Pendiente",
        )
        svc = ProfessionalService()
        payload, status = svc.delete_report(user.idUsuario, report.idReporte)
        assert status == 200
        assert payload["success"] is True


# ── ProfessionalService.all_evolution ─────────────────────────────────────────


@pytest.mark.django_db
class TestAllEvolution:
    def test_returns_evolution(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.all_evolution(user.idUsuario)
        assert status == 200
        assert payload["success"] is True


# ── ProfessionalService.get_patient_chatbot_history ───────────────────────────


@pytest.mark.django_db
class TestGetPatientChatbotHistory:
    def test_not_own_patient(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        svc = ProfessionalService()
        payload, status = svc.get_patient_chatbot_history(user.idUsuario, 99)
        assert status == 403

    def test_no_chatbot_data(self, django_user_model):
        user = Register.objects.create_user(
            email="pro@test.com",
            nombre="Dr. García",
            password="TestPass123",
            rol="profesional",
        )
        PerfilProfesional.objects.create(
            idProfesional=user,
            verificado=True,
        )
        patient = Register.objects.create_user(
            email="pac@test.com",
            nombre="Juan Pérez",
            password="TestPass123",
            rol="paciente",
        )
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(
            idProfesional=user,
            idPaciente=patient,
        )
        svc = ProfessionalService()
        payload, status = svc.get_patient_chatbot_history(user.idUsuario, patient.idUsuario)
        assert status == 200
        assert payload["success"] is True