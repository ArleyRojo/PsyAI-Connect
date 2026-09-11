from datetime import date, time, timedelta

import pytest

from apps.scheduling.models import Citas, Disponibilidad
from apps.scheduling.repositories import AppointmentRepository
from apps.authentication.models import Register


@pytest.fixture
def repo():
    return AppointmentRepository()


@pytest.fixture
def paciente(db):
    return Register.objects.create(
        idUsuario=100,
        nombre="Paciente Test",
        email="paciente_test@test.com",
        contrasena="fake",
        rol="paciente",
    )


@pytest.fixture
def profesional(db):
    return Register.objects.create(
        idUsuario=200,
        nombre="Profesional Test",
        email="profesional_test@test.com",
        contrasena="fake",
        rol="profesional",
    )


@pytest.fixture
def cita(db, paciente, profesional):
    return Citas.objects.create(
        idPaciente=paciente,
        idProfesional=profesional,
        fecha=date(2027, 6, 15),
        hora=time(10, 0),
        tipoCita="Presencial",
        motivo="Sesion de prueba",
        estado="Pendiente",
    )


@pytest.mark.django_db
class TestGetAppointmentInSlot:
    def test_returns_dict_for_existing_pendiente(self, repo, cita, profesional):
        result = repo.get_appointment_in_slot(profesional.idUsuario, date(2027, 6, 15), time(10, 0))
        assert result is not None
        assert result["idCita"] == cita.idCita
        assert result["idPaciente"] == cita.idPaciente_id

    def test_returns_dict_for_non_pendiente_excluding_cancelada(self, repo, paciente, profesional):
        Citas.objects.create(
            idPaciente=paciente,
            idProfesional=profesional,
            fecha=date(2027, 6, 15),
            hora=time(11, 0),
            tipoCita="Virtual",
            motivo="Otra",
            estado="Completada",
        )
        result = repo.get_appointment_in_slot(profesional.idUsuario, date(2027, 6, 15), time(11, 0))
        assert result is not None

    def test_returns_none_for_empty_slot(self, repo, profesional):
        result = repo.get_appointment_in_slot(profesional.idUsuario, date(2027, 6, 15), time(14, 0))
        assert result is None

    def test_returns_none_for_cancelled_appointment(self, repo, paciente, profesional):
        Citas.objects.create(
            idPaciente=paciente,
            idProfesional=profesional,
            fecha=date(2027, 6, 15),
            hora=time(12, 0),
            tipoCita="Presencial",
            motivo="Cancelada",
            estado="Cancelada",
        )
        result = repo.get_appointment_in_slot(profesional.idUsuario, date(2027, 6, 15), time(12, 0))
        assert result is None


@pytest.mark.django_db
class TestGetTakenTimes:
    def test_returns_taken_times(self, repo, cita, profesional):
        times = repo.get_taken_times(profesional.idUsuario, date(2027, 6, 15))
        assert "10:00" in times

    def test_excludes_cancelled(self, repo, paciente, profesional):
        Citas.objects.create(
            idPaciente=paciente,
            idProfesional=profesional,
            fecha=date(2027, 6, 15),
            hora=time(11, 0),
            tipoCita="Presencial",
            motivo="Cancelada",
            estado="Cancelada",
        )
        times = repo.get_taken_times(profesional.idUsuario, date(2027, 6, 15))
        assert "11:00" not in times

    def test_returns_empty_for_no_appointments(self, repo, profesional):
        times = repo.get_taken_times(profesional.idUsuario, date(2027, 6, 15))
        assert times == []


@pytest.mark.django_db
class TestGetProfessionalAppointments:
    def test_returns_paginated_list(self, repo, cita, profesional):
        result = repo.get_professional_appointments(profesional.idUsuario)
        assert len(result) >= 1
        assert result[0]["idCita"] == cita.idCita

    def test_pending_only_filter(self, repo, paciente, profesional):
        Citas.objects.create(
            idPaciente=paciente,
            idProfesional=profesional,
            fecha=date(2027, 6, 15),
            hora=time(11, 0),
            tipoCita="Virtual",
            motivo="Completada",
            estado="Completada",
        )
        result = repo.get_professional_appointments(profesional.idUsuario, pending_only=True)
        assert all(c["estado"] == "Pendiente" for c in result)

    def test_pagination(self, repo, paciente, profesional):
        for i in range(5):
            Citas.objects.create(
                idPaciente=paciente,
                idProfesional=profesional,
                fecha=date(2027, 6, 15),
                hora=time(9 + i, 0),
                tipoCita="Presencial",
                motivo=f"Cita {i}",
                estado="Pendiente",
            )
        page1 = repo.get_professional_appointments(profesional.idUsuario, page=1, limit=2)
        assert len(page1) == 2


@pytest.mark.django_db
class TestGetNextPatientAppointment:
    def test_returns_next_appointment(self, repo, cita, paciente):
        result = repo.get_next_patient_appointment(paciente.idUsuario)
        assert result is not None
        assert result["tipoCita"] == "Presencial"

    def test_returns_none_if_no_pendiente(self, repo, paciente, profesional):
        Citas.objects.create(
            idPaciente=paciente,
            idProfesional=profesional,
            fecha=date(2027, 6, 15),
            hora=time(10, 0),
            tipoCita="Virtual",
            motivo="Completada",
            estado="Completada",
        )
        result = repo.get_next_patient_appointment(paciente.idUsuario)
        assert result is None

    def test_returns_none_for_empty(self, repo, paciente):
        result = repo.get_next_patient_appointment(paciente.idUsuario)
        assert result is None


@pytest.mark.django_db
class TestGetAppointmentOwner:
    def test_returns_tuple(self, repo, cita, profesional, paciente):
        result = repo.get_appointment_owner(cita.idCita)
        assert result == (profesional.idUsuario, paciente.idUsuario)

    def test_returns_none_for_nonexistent(self, repo):
        result = repo.get_appointment_owner(99999)
        assert result is None


@pytest.mark.django_db
class TestCreateAppointment:
    def test_creates_and_returns_id(self, repo, paciente, profesional):
        cita_id = repo.create_appointment(
            patient_id=paciente.idUsuario,
            professional_id=profesional.idUsuario,
            fecha=date(2027, 6, 15),
            hora=time(10, 0),
            tipo_cita="Presencial",
            motivo="Test",
        )
        assert cita_id is not None
        assert Citas.objects.filter(idCita=cita_id).exists()

    def test_created_appointment_has_correct_fields(self, repo, paciente, profesional):
        cita_id = repo.create_appointment(
            patient_id=paciente.idUsuario,
            professional_id=profesional.idUsuario,
            fecha=date(2027, 7, 1),
            hora=time(14, 30),
            tipo_cita="Virtual",
            motivo="Detalle",
        )
        cita = Citas.objects.get(idCita=cita_id)
        assert cita.estado == "Pendiente"
        assert cita.tipoCita == "Virtual"
        assert cita.fecha == date(2027, 7, 1)
        assert cita.hora == time(14, 30)
