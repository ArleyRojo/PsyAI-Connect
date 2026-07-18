from unittest.mock import patch, MagicMock

import pytest

from apps.professionals.services import ProfessionalService


# ── ProfessionalService.get_profile ───────────────────────────────────────────


class TestGetProfile:
    def test_not_found(self, professional_service, mock_professional_repo):
        mock_professional_repo.get_professional_profile.return_value = None
        payload, status = professional_service.get_profile(999)
        assert status == 404

    def test_returns_profile(self, professional_service, mock_professional_repo):
        mock_professional_repo.get_professional_profile.return_value = {
            "idUsuario": 1,
            "nombre": "Dr. García",
            "especialidad": "Psicología Clínica",
        }
        payload, status = professional_service.get_profile(1)
        assert status == 200
        assert payload["perfil"]["especialidad"] == "Psicología Clínica"


# ── ProfessionalService.update_profile ────────────────────────────────────────


class TestUpdateProfile:
    def test_empty_data(self, professional_service):
        payload, status = professional_service.update_profile({})
        assert status == 400

    def test_missing_all_fields(self, professional_service):
        payload, status = professional_service.update_profile({"nombre": "Solo nombre"})
        assert status == 400

    def test_with_especialidad(self, professional_service, mock_professional_repo):
        payload, status = professional_service.update_profile({
            "idUsuario": 1,
            "especialidad": "Psicología Clínica",
        })
        assert status == 200
        mock_professional_repo.update_professional_profile.assert_called_once()

    def test_with_licencia(self, professional_service, mock_professional_repo):
        payload, status = professional_service.update_profile({
            "idUsuario": 1,
            "licencia": "LIC-12345",
        })
        assert status == 200


# ── ProfessionalService.get_dashboard ─────────────────────────────────────────


class TestGetDashboard:
    def test_returns_dashboard(self, professional_service, mock_professional_repo):
        mock_professional_repo.get_dashboard_stats.return_value = {
            "pacientes_activos": 10,
            "citas_hoy": 3,
            "citas_pendientes": 5,
            "actividades": [],
            "proximas_citas": [],
            "reportes": {"total": 20, "completados": 15, "pendientes": 5},
            "evolucion": {"promedio_energia": 3.5, "pacientes_sin_evolucion": 2},
            "alertas": [],
        }
        payload, status = professional_service.get_dashboard(1)
        assert status == 200
        assert payload["success"] is True
        assert payload["pacientes_activos"] == 10


# ── ProfessionalService.list_patients ─────────────────────────────────────────


class TestListPatients:
    def test_returns_patients(self, professional_service, mock_professional_repo):
        mock_professional_repo.list_professional_patients.return_value = [
            {"idUsuario": 1, "nombre": "Juan"},
        ]
        payload, status = professional_service.list_patients(1)
        assert status == 200
        assert len(payload["pacientes"]) == 1


# ── ProfessionalService.save_diagnosis ────────────────────────────────────────


class TestSaveDiagnosis:
    def test_missing_id_paciente(self, professional_service):
        payload, status = professional_service.save_diagnosis(1, {})
        assert status == 400
        assert "idpaciente" in payload["message"].lower()

    def test_successful_save(self, professional_service, mock_professional_repo):
        payload, status = professional_service.save_diagnosis(1, {
            "idPaciente": 5,
            "sintomas": "Ansiedad",
            "diagnostico": "TAD",
        })
        assert status == 200
        mock_professional_repo.save_diagnosis.assert_called_once()


# ── ProfessionalService.diagnosis_history ─────────────────────────────────────


class TestDiagnosisHistory:
    def test_returns_history(self, professional_service, mock_professional_repo):
        mock_professional_repo.get_diagnosis_history.return_value = [
            {"sintomas": "Ansiedad", "diagnostico": "TAD"},
        ]
        payload, status = professional_service.diagnosis_history(1)
        assert status == 200
        assert len(payload["historial"]) == 1


# ── ProfessionalService.create_report ─────────────────────────────────────────


class TestCreateReport:
    def test_not_own_patient(self, professional_service, mock_professional_repo):
        mock_professional_repo.professional_has_patient.return_value = False
        payload, status = professional_service.create_report(1, {
            "idPaciente": 99,
            "tipoReporte": "general",
        })
        assert status == 403

    def test_successful_create(self, professional_service, mock_professional_repo):
        mock_professional_repo.professional_has_patient.return_value = True
        mock_professional_repo.get_latest_patient_diagnosis.return_value = None
        payload, status = professional_service.create_report(1, {
            "idPaciente": 5,
            "tipoReporte": "general",
        })
        assert status == 200
        mock_professional_repo.create_report.assert_called_once()


# ── ProfessionalService.update_report ─────────────────────────────────────────


class TestUpdateReport:
    def test_successful_update(self, professional_service, mock_professional_repo):
        payload, status = professional_service.update_report(1, {
            "idReporte": 10,
            "tipoReporte": "evolución",
        })
        assert status == 200
        mock_professional_repo.update_report.assert_called_once()


# ── ProfessionalService.delete_report ─────────────────────────────────────────


class TestDeleteReport:
    def test_successful_delete(self, professional_service, mock_professional_repo):
        payload, status = professional_service.delete_report(1, 10)
        assert status == 200
        mock_professional_repo.delete_report.assert_called_once_with(1, 10)


# ── ProfessionalService.get_deleted_reports ───────────────────────────────────


class TestGetDeletedReports:
    def test_returns_deleted(self, professional_service, mock_professional_repo):
        mock_professional_repo.get_deleted_reports.return_value = [
            {"idReporte": 10, "eliminado": True},
        ]
        payload, status = professional_service.get_deleted_reports(1)
        assert status == 200
        assert len(payload["reportes"]) == 1


# ── ProfessionalService.all_evolution ─────────────────────────────────────────


class TestAllEvolution:
    def test_returns_evolution(self, professional_service, mock_professional_repo):
        mock_professional_repo.get_all_patient_evolution.return_value = [
            {"estadoEmocional": "Ansioso"},
        ]
        payload, status = professional_service.all_evolution(1)
        assert status == 200
        assert len(payload["historial"]) == 1


# ── ProfessionalService.get_patient_chatbot_history ───────────────────────────


class TestGetPatientChatbotHistory:
    def test_not_own_patient(self, professional_service, mock_professional_repo):
        mock_professional_repo.professional_has_patient.return_value = False
        payload, status = professional_service.get_patient_chatbot_history(1, 99)
        assert status == 403

    def test_no_chatbot_data(self, professional_service, mock_professional_repo):
        mock_professional_repo.professional_has_patient.return_value = True
        mock_professional_repo.get_latest_patient_diagnosis.return_value = None
        payload, status = professional_service.get_patient_chatbot_history(1, 5)
        assert status == 200
        assert payload["success"] is True
