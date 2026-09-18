import io
from unittest.mock import patch, MagicMock

import pytest

from apps.patients.services import PatientService


# ── PatientService.get_patient_profile ────────────────────────────────────────


class TestGetPatientProfile:
    def test_not_found(self, patient_service, mock_patient_repo):
        mock_patient_repo.get_patient_profile.return_value = None
        payload, status = patient_service.get_patient_profile(999)
        assert status == 404

    def test_returns_profile(self, patient_service, mock_patient_repo):
        mock_patient_repo.get_patient_profile.return_value = {
            "idUsuario": 1,
            "nombre": "Juan",
            "email": "juan@test.com",
        }
        payload, status = patient_service.get_patient_profile(1)
        assert status == 200
        assert payload["success"] is True
        assert payload["perfil"]["nombre"] == "Juan"


# ── PatientService.update_patient_profile ─────────────────────────────────────


class TestUpdatePatientProfile:
    def test_missing_phone(self, patient_service):
        payload, status = patient_service.update_patient_profile({"idUsuario": 1})
        assert status == 400
        assert "numerotelefonico" in payload["message"].lower()

    def test_successful_update(self, patient_service, mock_patient_repo):
        payload, status = patient_service.update_patient_profile({
            "idUsuario": 1,
            "numeroTelefonico": "3001234567",
        })
        assert status == 200
        assert payload["success"] is True
        mock_patient_repo.update_patient_profile.assert_called_once()


# ── PatientService.get_chatbot_consent ────────────────────────────────────────


class TestGetChatbotConsent:
    def test_returns_consent(self, patient_service, mock_patient_repo):
        mock_patient_repo.get_chatbot_consent.return_value = True
        payload, status = patient_service.get_chatbot_consent(1)
        assert status == 200
        assert payload["consentimiento_chatbot"] is True


# ── PatientService.update_chatbot_consent ─────────────────────────────────────


class TestUpdateChatbotConsent:
    def test_sets_consent_true(self, patient_service, mock_patient_repo):
        payload, status = patient_service.update_chatbot_consent(1, True)
        assert status == 200
        mock_patient_repo.update_chatbot_consent.assert_called_once_with(1, True)

    def test_coerces_truthy_value(self, patient_service, mock_patient_repo):
        payload, status = patient_service.update_chatbot_consent(1, 1)
        assert status == 200
        mock_patient_repo.update_chatbot_consent.assert_called_once_with(1, True)


# ── PatientService.save_chatbot_survey ────────────────────────────────────────


class TestSaveChatbotSurvey:
    def test_missing_utilidad(self, patient_service):
        payload, status = patient_service.save_chatbot_survey(1, {
            "claridad": 5,
            "recomendaria": "si",
        })
        assert status == 400

    def test_missing_claridad(self, patient_service):
        payload, status = patient_service.save_chatbot_survey(1, {
            "utilidad": 5,
            "recomendaria": "si",
        })
        assert status == 400

    def test_missing_recomendaria(self, patient_service):
        payload, status = patient_service.save_chatbot_survey(1, {
            "utilidad": 5,
            "claridad": 5,
        })
        assert status == 400

    def test_successful_save(self, patient_service, mock_patient_repo):
        payload, status = patient_service.save_chatbot_survey(1, {
            "utilidad": 5,
            "claridad": 4,
            "recomendaria": "si",
        })
        assert status == 200
        assert payload["success"] is True
        mock_patient_repo.save_chatbot_survey.assert_called_once()


# ── PatientService.save_evolution ─────────────────────────────────────────────


class TestSaveEvolution:
    def test_successful_save(self, patient_service, mock_patient_repo):
        payload, status = patient_service.save_evolution(1, {
            "estadoEmocional": "Ansioso",
            "nivelEnergia": 3,
            "notasPersonales": "Me siento mejor",
        })
        assert status == 200
        mock_patient_repo.create_patient_evolution.assert_called_once()


# ── PatientService.get_evolution_history ──────────────────────────────────────


class TestGetEvolutionHistory:
    def test_returns_history(self, patient_service, mock_patient_repo):
        mock_patient_repo.get_patient_evolution_history.return_value = [
            {"estadoEmocional": "Ansioso", "nivelEnergia": 3},
        ]
        payload, status = patient_service.get_evolution_history(1)
        assert status == 200
        assert len(payload["historial"]) == 1


# ── PatientService.list_patients ──────────────────────────────────────────────


class TestListPatients:
    def test_returns_paginated_list(self, patient_service, mock_patient_repo):
        mock_patient_repo.list_patients.return_value = [
            {"idUsuario": 1, "nombre": "Juan"},
            {"idUsuario": 2, "nombre": "Maria"},
        ]
        payload, status = patient_service.list_patients(page=1, limit=20)
        assert status == 200
        assert len(payload["pacientes"]) == 2


# ── PatientService.list_professionals ─────────────────────────────────────────


class TestListProfessionals:
    def test_returns_professionals(self, patient_service, mock_patient_repo):
        mock_patient_repo.list_professionals.return_value = [
            {"idUsuario": 10, "nombre": "Dr. Garcia"},
        ]
        payload, status = patient_service.list_professionals()
        assert status == 200
        assert len(payload["profesionales"]) == 1


# ── PatientService.update_profile_photo ───────────────────────────────────────


class TestUpdateProfilePhoto:
    def test_no_file(self, patient_service):
        payload, status = patient_service.update_profile_photo(1, None)
        assert status == 400

    def test_invalid_extension(self, patient_service):
        fake_file = MagicMock()
        fake_file.name = "photo.bmp"
        fake_file.size = 1000
        payload, status = patient_service.update_profile_photo(1, fake_file)
        assert status == 400

    def test_file_too_large(self, patient_service):
        fake_file = MagicMock()
        fake_file.name = "photo.jpg"
        fake_file.size = 50 * 1024 * 1024  # 50MB
        payload, status = patient_service.update_profile_photo(1, fake_file)
        assert status == 400

    @patch("apps.patients.services.os.path.exists", return_value=True)
    @patch("apps.patients.services.os.makedirs")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("apps.patients.services.settings")
    def test_valid_upload(self, mock_settings, mock_open, mock_makedirs, mock_exists, patient_service, mock_patient_repo):
        mock_settings.MEDIA_ROOT = "/tmp"
        mock_settings.MAX_UPLOAD_SIZE_MB = 10
        fake_file = MagicMock()
        fake_file.name = "photo.jpg"
        fake_file.size = 1000
        fake_file.read.return_value = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        fake_file.content_type = "image/jpeg"
        payload, status = patient_service.update_profile_photo(1, fake_file)
        assert status == 200
        assert payload["success"] is True
        mock_patient_repo.update_profile_photo.assert_called_once()
