from datetime import date, time, datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from apps.scheduling.services import AppointmentService


# ── AppointmentService.create_appointment ─────────────────────────────────────


class TestCreateAppointment:
    def test_missing_required_fields(self, appointment_service):
        payload, status = appointment_service.create_appointment(1, {})
        assert status == 400

    def test_slot_occupied_by_different_patient(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_appointment_in_slot.return_value = {
            "idCita": 10,
            "idPaciente": 2,
        }
        payload, status = appointment_service.create_appointment(1, {
            "idProfesional": 5,
            "fecha": "2025-06-15",
            "hora": "10:00",
            "motivo": "Sesion",
            "tipoCita": "Presencial",
        })
        assert status == 409

    def test_same_patient_rebooks_cancels_old(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_appointment_in_slot.return_value = {
            "idCita": 10,
            "idPaciente": 1,
        }
        mock_appointment_repo.create_appointment.return_value = 20
        payload, status = appointment_service.create_appointment(1, {
            "idProfesional": 5,
            "fecha": "2025-06-15",
            "hora": "10:00",
            "motivo": "Sesion",
            "tipoCita": "Presencial",
        })
        assert status == 200
        mock_appointment_repo.cancel_patient_appointment.assert_called_once_with(
            10, 1, "Reemplazada por nuevo intento de agendamiento"
        )

    def test_successful_creation(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_appointment_in_slot.return_value = None
        mock_appointment_repo.create_appointment.return_value = 20
        payload, status = appointment_service.create_appointment(1, {
            "idProfesional": 5,
            "fecha": "2025-06-15",
            "hora": "10:00",
            "motivo": "Sesion",
            "tipoCita": "Presencial",
        })
        assert status == 200
        assert payload["idCita"] == 20


# ── AppointmentService.get_available_times ────────────────────────────────────


class TestGetAvailableTimes:
    def test_no_availability(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_daily_availability.return_value = []
        payload, status = appointment_service.get_available_times(5, "2025-06-15")
        assert status == 200
        assert payload["horarios"] == []

    def test_returns_slots(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_daily_availability.return_value = [
            {"hora_inicio": time(9, 0), "hora_fin": time(10, 0)},
        ]
        mock_appointment_repo.get_taken_times.return_value = ["09:00"]
        payload, status = appointment_service.get_available_times(5, "2025-06-15")
        assert status == 200
        assert "09:30" in payload["horarios"]
        assert "09:00" not in payload["horarios"]

    def test_with_timedelta_hours(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_daily_availability.return_value = [
            {"hora_inicio": timedelta(hours=9), "hora_fin": timedelta(hours=10)},
        ]
        mock_appointment_repo.get_taken_times.return_value = []
        payload, status = appointment_service.get_available_times(5, "2025-06-15")
        assert status == 200
        assert len(payload["horarios"]) == 2


# ── AppointmentService.list_professional_appointments ─────────────────────────


class TestListProfessionalAppointments:
    def test_returns_paginated(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_professional_appointments.return_value = [
            {"idCita": 1, "motivo": "Sesion"},
        ]
        payload, status = appointment_service.list_professional_appointments(5)
        assert status == 200
        assert len(payload["citas"]) == 1


# ── AppointmentService.get_taken_slots ────────────────────────────────────────


class TestGetTakenSlots:
    def test_returns_taken(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_taken_times_by_professional.return_value = ["09:00", "10:30"]
        payload, status = appointment_service.get_taken_slots(5, "2025-06-15")
        assert status == 200
        assert len(payload["horarios_ocupados"]) == 2


# ── AppointmentService.get_next_patient_appointment ──────────────────────────


class TestGetNextPatientAppointment:
    def test_returns_next(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_next_patient_appointment.return_value = {
            "idCita": 1,
            "fecha": datetime(2025, 6, 15),
            "hora": time(10, 0),
        }
        payload, status = appointment_service.get_next_patient_appointment(1)
        assert status == 200
        assert payload["cita"]["idCita"] == 1

    def test_no_appointment(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_next_patient_appointment.return_value = None
        payload, status = appointment_service.get_next_patient_appointment(1)
        assert status == 200
        assert payload["cita"] is None


# ── AppointmentService.update_status ──────────────────────────────────────────


class TestUpdateStatus:
    def test_invalid_status(self, appointment_service):
        payload, status = appointment_service.update_status(1, "Basura", 5)
        assert status == 400

    def test_not_found(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_appointment_owner.return_value = None
        payload, status = appointment_service.update_status(999, "Completada", 5)
        assert status == 404

    def test_not_own_appointment(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_appointment_owner.return_value = (10, 20)
        payload, status = appointment_service.update_status(1, "Completada", 99)
        assert status == 403

    def test_successful_update(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_appointment_owner.return_value = (5, 1)
        payload, status = appointment_service.update_status(1, "Completada", 5)
        assert status == 200
        mock_appointment_repo.update_appointment_status.assert_called_once_with(1, "Completada")


# ── AppointmentService.list_patient_appointments ─────────────────────────────


class TestListPatientAppointments:
    def test_returns_list(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_patient_appointments.return_value = [
            {"idCita": 1, "motivo": "Sesion"},
        ]
        payload, status = appointment_service.list_patient_appointments(1)
        assert status == 200
        assert len(payload["citas"]) == 1


# ── AppointmentService.cancel_appointment ─────────────────────────────────────


class TestCancelAppointment:
    def test_empty_motivo(self, appointment_service):
        payload, status = appointment_service.cancel_appointment(1, 1, "")
        assert status == 400

    def test_not_found(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_appointment_owner.return_value = None
        payload, status = appointment_service.cancel_appointment(999, 1, "Motivo")
        assert status == 404

    def test_successful_cancel(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_appointment_owner.return_value = (5, 1)
        payload, status = appointment_service.cancel_appointment(1, 1, "Cambio de planes")
        assert status == 200
        mock_appointment_repo.cancel_patient_appointment.assert_called_once()


# ── AppointmentService.cancel_professional_appointment ────────────────────────


class TestCancelProfessionalAppointment:
    def test_empty_motivo(self, appointment_service):
        payload, status = appointment_service.cancel_professional_appointment(1, 5, "")
        assert status == 400

    def test_not_own(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_appointment_owner.return_value = (99, 1)
        payload, status = appointment_service.cancel_professional_appointment(1, 5, "Motivo")
        assert status == 403

    def test_successful_cancel(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_appointment_owner.return_value = (5, 1)
        payload, status = appointment_service.cancel_professional_appointment(1, 5, "Emergencia")
        assert status == 200
        mock_appointment_repo.cancel_professional_appointment.assert_called_once()


# ── AppointmentService.get_available_dates ────────────────────────────────────


class TestGetAvailableDates:
    def test_no_availability(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_month_availability.return_value = []
        payload, status = appointment_service.get_available_dates(5, 2025, 6)
        assert status == 200
        assert payload["fechas"] == []

    def test_returns_dates(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_month_availability.return_value = [
            {"fecha": datetime(2025, 6, 15), "hora_inicio": time(9, 0), "hora_fin": time(10, 0)},
        ]
        mock_appointment_repo.get_month_taken_counts.return_value = {"2025-06-15": 1}
        payload, status = appointment_service.get_available_dates(5, 2025, 6)
        assert status == 200
        assert "2025-06-15" in payload["fechas"]

    def test_all_slots_taken(self, appointment_service, mock_appointment_repo):
        mock_appointment_repo.get_month_availability.return_value = [
            {"fecha": datetime(2025, 6, 15), "hora_inicio": time(9, 0), "hora_fin": time(9, 30)},
        ]
        mock_appointment_repo.get_month_taken_counts.return_value = {"2025-06-15": 1}
        payload, status = appointment_service.get_available_dates(5, 2025, 6)
        assert status == 200
        assert payload["fechas"] == []
