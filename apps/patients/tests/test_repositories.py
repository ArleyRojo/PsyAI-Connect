import pytest
from django.utils import timezone

from apps.authentication.models import Register
from apps.patients.models import PerfilPaciente, EvolucionPaciente
from apps.patients.repositories import PatientRepository


@pytest.mark.django_db
class TestGetPatientProfile:
    def test_returns_dict(self):
        user = Register.objects.create_user(
            email="pac@test.com",
            nombre="Juan",
            password="Abc123",
            rol="paciente",
        )
        repo = PatientRepository()
        result = repo.get_patient_profile(user.idUsuario)

        assert result is not None
        assert result["nombre"] == "Juan"
        assert result["email"] == "pac@test.com"

    def test_returns_none_for_nonexistent(self):
        repo = PatientRepository()
        assert repo.get_patient_profile(99999) is None

    def test_includes_perfil_fields(self):
        user = Register.objects.create_user(
            email="perfil@test.com",
            nombre="Maria",
            password="Abc123",
            rol="paciente",
        )
        PerfilPaciente.objects.create(
            idPaciente=user,
            genero="Femenino",
            edad=25,
            numeroTelefonico="3001234567",
            consentimiento_chatbot=True,
        )
        repo = PatientRepository()
        result = repo.get_patient_profile(user.idUsuario)

        assert result["genero"] == "Femenino"
        assert result["edad"] == 25
        assert result["numeroTelefonico"] == "3001234567"
        assert result["consentimiento_chatbot"] is True

    def test_returns_none_perfil_fields_when_no_profile(self):
        user = Register.objects.create_user(
            email="noperf@test.com",
            nombre="SinPerfil",
            password="Abc123",
            rol="paciente",
        )
        repo = PatientRepository()
        result = repo.get_patient_profile(user.idUsuario)

        assert result is not None
        assert result["edad"] is None
        assert result["genero"] is None


@pytest.mark.django_db
class TestUpdatePatientProfile:
    def test_updates_phone(self):
        user = Register.objects.create_user(
            email="update@test.com",
            nombre="Update",
            password="Abc123",
            rol="paciente",
        )
        repo = PatientRepository()
        repo.update_patient_profile({
            "idUsuario": user.idUsuario,
            "numeroTelefonico": "3119998877",
        })

        perfil = PerfilPaciente.objects.get(idPaciente=user)
        assert perfil.numeroTelefonico == "3119998877"

    def test_creates_profile_if_not_exists(self):
        user = Register.objects.create_user(
            email="newperf@test.com",
            nombre="NewPerf",
            password="Abc123",
            rol="paciente",
        )
        repo = PatientRepository()
        repo.update_patient_profile({
            "idUsuario": user.idUsuario,
            "numeroTelefonico": "3005551122",
        })

        perfil = PerfilPaciente.objects.get(idPaciente=user)
        assert perfil.numeroTelefonico == "3005551122"
        assert perfil.consentimiento_chatbot is False


@pytest.mark.django_db
class TestChatbotConsent:
    def test_get_returns_false_when_no_profile(self):
        repo = PatientRepository()
        assert repo.get_chatbot_consent(99999) is False

    def test_get_returns_true(self):
        user = Register.objects.create_user(
            email="consent@test.com",
            nombre="Consent",
            password="Abc123",
            rol="paciente",
        )
        PerfilPaciente.objects.create(
            idPaciente=user,
            consentimiento_chatbot=True,
        )
        repo = PatientRepository()
        assert repo.get_chatbot_consent(user.idUsuario) is True

    def test_update_sets_consent(self):
        user = Register.objects.create_user(
            email="updateconsent@test.com",
            nombre="UpdateConsent",
            password="Abc123",
            rol="paciente",
        )
        repo = PatientRepository()
        repo.update_chatbot_consent(user.idUsuario, True)

        perfil = PerfilPaciente.objects.get(idPaciente=user)
        assert perfil.consentimiento_chatbot is True

    def test_update_creates_profile(self):
        user = Register.objects.create_user(
            email="newconsent@test.com",
            nombre="NewConsent",
            password="Abc123",
            rol="paciente",
        )
        repo = PatientRepository()
        repo.update_chatbot_consent(user.idUsuario, True)

        perfil = PerfilPaciente.objects.get(idPaciente=user)
        assert perfil.consentimiento_chatbot is True


@pytest.mark.django_db
class TestPatientEvolution:
    def test_create_and_get(self):
        user = Register.objects.create_user(
            email="evo@test.com",
            nombre="Evo",
            password="Abc123",
            rol="paciente",
        )
        repo = PatientRepository()
        repo.create_patient_evolution(user.idUsuario, {
            "estadoEmocional": "Ansioso",
            "nivelEnergia": 3,
            "notasPersonales": "Me siento bien",
        })

        history = repo.get_patient_evolution_history(user.idUsuario)
        assert len(history) == 1
        assert history[0]["estadoEmocional"] == "Ansioso"
        assert history[0]["nivelEnergia"] == 3

    def test_empty_history(self):
        repo = PatientRepository()
        assert repo.get_patient_evolution_history(99999) == []

    def test_multiple_evolutions_ordered_by_date(self):
        user = Register.objects.create_user(
            email="multievo@test.com",
            nombre="MultiEvo",
            password="Abc123",
            rol="paciente",
        )
        repo = PatientRepository()
        repo.create_patient_evolution(user.idUsuario, {
            "estadoEmocional": "Triste",
            "nivelEnergia": 2,
        })
        repo.create_patient_evolution(user.idUsuario, {
            "estadoEmocional": "Feliz",
            "nivelEnergia": 5,
        })

        history = repo.get_patient_evolution_history(user.idUsuario)
        assert len(history) == 2
        assert history[0]["estadoEmocional"] == "Feliz"
        assert history[1]["estadoEmocional"] == "Triste"


@pytest.mark.django_db
class TestListPatients:
    def test_returns_patients(self):
        Register.objects.create_user(
            email="p1@test.com", nombre="Paciente 1", password="Abc123", rol="paciente"
        )
        Register.objects.create_user(
            email="p2@test.com", nombre="Paciente 2", password="Abc123", rol="paciente"
        )
        Register.objects.create_user(
            email="pro@test.com", nombre="Prof", password="Abc123", rol="profesional"
        )
        repo = PatientRepository()
        result = repo.list_patients()

        assert len(result) == 2
        assert all(p["nombre"].startswith("Paciente") for p in result)

    def test_pagination(self):
        for i in range(5):
            Register.objects.create_user(
                email=f"pag{i}@test.com",
                nombre=f"Paciente {i}",
                password="Abc123",
                rol="paciente",
            )
        repo = PatientRepository()
        page1 = repo.list_patients(page=1, limit=2)
        page2 = repo.list_patients(page=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0]["idUsuario"] != page2[0]["idUsuario"]


@pytest.mark.django_db
class TestListProfessionals:
    def test_returns_professionals(self):
        Register.objects.create_user(
            email="pro1@test.com", nombre="Dr. Garcia", password="Abc123", rol="profesional"
        )
        Register.objects.create_user(
            email="pro2@test.com", nombre="Dr. Lopez", password="Abc123", rol="profesional"
        )
        Register.objects.create_user(
            email="pac@test.com", nombre="Paciente", password="Abc123", rol="paciente"
        )
        repo = PatientRepository()
        result = repo.list_professionals()

        assert len(result) == 2
        assert all("Dr." in p["nombre"] for p in result)

    def test_empty_list(self):
        repo = PatientRepository()
        result = repo.list_professionals()
        assert result == []
