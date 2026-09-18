import pytest

from apps.authentication.models import Register
from apps.chatbot.models import ConversacionesChatbot
from apps.chatbot.repositories import ChatRepository


@pytest.fixture
def patient(db):
    return Register.objects.create(
        nombre="Paciente Test",
        email="paciente@test.com",
        contrasena="fake",
        rol="paciente",
        activo=True,
        estadoCuenta="Activa",
    )


@pytest.fixture
def repo():
    return ChatRepository()


@pytest.mark.django_db
class TestSaveConversation:
    def test_creates_record(self, repo, patient):
        repo.save_conversation(
            patient.idUsuario,
            "Hola",
            "Hola, como estas?",
            "Sin riesgo",
            None,
        )
        assert ConversacionesChatbot.objects.filter(
            idPaciente_id=patient.idUsuario
        ).exists()

    def test_stores_all_fields(self, repo, patient):
        repo.save_conversation(
            patient.idUsuario,
            "Me siento mal",
            "Lamento eso",
            "Medio",
            "suicidio",
        )
        conv = ConversacionesChatbot.objects.get(idPaciente_id=patient.idUsuario)
        assert conv.mensajeUsuario == "Me siento mal"
        assert conv.respuestaChatbot == "Lamento eso"
        assert conv.nivelEmocionalDetectado == "Medio"
        assert conv.palabrasRiesgoDetectadas == "suicidio"


@pytest.mark.django_db
class TestGetHistory:
    def test_returns_empty_when_none(self, repo, patient):
        result = repo.get_history(patient.idUsuario)
        assert result == []

    def test_returns_conversations_in_order(self, repo, patient):
        repo.save_conversation(patient.idUsuario, "msg1", "reply1", "Sin riesgo", None)
        repo.save_conversation(patient.idUsuario, "msg2", "reply2", "Sin riesgo", None)
        result = repo.get_history(patient.idUsuario, limit=10)
        assert len(result) == 4
        assert result[0]["tipo"] == "usuario"
        assert result[0]["mensaje"] == "msg1"
        assert result[2]["tipo"] == "usuario"
        assert result[2]["mensaje"] == "msg2"

    def test_limit_respected(self, repo, patient):
        for i in range(5):
            repo.save_conversation(patient.idUsuario, f"msg{i}", f"reply{i}", "Sin riesgo", None)
        result = repo.get_history(patient.idUsuario, limit=3)
        assert len(result) == 6


@pytest.mark.django_db
class TestDeleteHistory:
    def test_deletes_all(self, repo, patient):
        repo.save_conversation(patient.idUsuario, "msg1", "reply1", "Sin riesgo", None)
        repo.save_conversation(patient.idUsuario, "msg2", "reply2", "Sin riesgo", None)
        repo.delete_history(patient.idUsuario)
        assert ConversacionesChatbot.objects.filter(
            idPaciente_id=patient.idUsuario
        ).count() == 0

    def test_noop_when_empty(self, repo, patient):
        repo.delete_history(patient.idUsuario)
        assert ConversacionesChatbot.objects.filter(
            idPaciente_id=patient.idUsuario
        ).count() == 0


@pytest.mark.django_db
class TestCountTodayMessages:
    def test_returns_zero_when_none(self, repo, patient):
        from datetime import timezone as dt_timezone
        from django.utils import timezone
        with timezone.override(dt_timezone.utc):
            assert repo.count_today_messages(patient.idUsuario) == 0

    def test_counts_conversations_today(self, repo, patient):
        from datetime import timezone as dt_timezone
        from django.utils import timezone
        with timezone.override(dt_timezone.utc):
            repo.save_conversation(patient.idUsuario, "a", "b", "Sin riesgo", None)
            repo.save_conversation(patient.idUsuario, "c", "d", "Sin riesgo", None)
            assert repo.count_today_messages(patient.idUsuario) == 2


@pytest.mark.django_db
class TestGetAssignedProfessionals:
    def test_returns_empty_when_no_assignments(self, repo, patient):
        result = repo.get_assigned_professionals(patient.idUsuario)
        assert result == []


@pytest.mark.django_db
class TestGetPatientName:
    def test_returns_name(self, repo, patient):
        name = repo.get_patient_name(patient.idUsuario)
        assert name == "Paciente Test"

    def test_returns_none_when_not_found(self, repo):
        name = repo.get_patient_name(99999)
        assert name is None
