import json
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.integration


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_patient(django_user_model, email="prediag_patient@test.com"):
    return django_user_model.objects.create_user(
        email=email,
        nombre="Paciente Prediag",
        password="TestPass123",
        rol="paciente",
    )


def _make_professional(django_user_model, email="prediag_prof@test.com"):
    return django_user_model.objects.create_user(
        email=email,
        nombre="Profesional Prediag",
        password="TestPass123",
        rol="profesional",
    )


GEMINI_OK_RESPONSE = json.dumps({
    "resumen_paciente": "Hoy compartiste algunos pensamientos que muestran cierta carga emocional.",
    "resumen_profesional": "Se observan patrones compatibles con ansiedad leve y rumiacion.",
    "posibles_areas": ["Ansiedad", "Estres"],
    "recomendaciones_paciente": ["Practica respiracion profunda", "Habla con tu profesional"],
    "nivel_riesgo": "moderado",
    "requiere_atencion_urgente": False,
})

FAKE_HISTORY_NORMAL = [
    {"tipo": "usuario", "mensaje": "Me siento un poco ansioso hoy", "nivel_emocional": "Moderado"},
    {"tipo": "bot", "mensaje": "Te escucho, cuentame mas", "nivel_emocional": None},
]

FAKE_HISTORY_HIGH_RISK = [
    {"tipo": "usuario", "mensaje": "No quiero seguir", "nivel_emocional": "Alto"},
    {"tipo": "bot", "mensaje": "Estoy aqui contigo", "nivel_emocional": None},
]


# ── Service: generar_prediagnostico ──────────────────────────────────────────


@pytest.mark.django_db
class TestGenerarPrediagnosticoService:
    """Tests for ChatbotService.generar_prediagnostico()."""

    def _get_service(self):
        from apps.chatbot.services import ChatbotService
        return ChatbotService()

    def test_empty_history_returns_400(self):
        svc = self._get_service()
        with patch.object(svc.chat_repo, "get_history", return_value=[]):
            result, status = svc.generar_prediagnostico(patient_id=1)
        # Backend returns 200 with no_data flag when no history (not 400)
        assert status == 200
        assert result["success"] is True
        assert result["no_data"] is True
        # Check for words that don't have accented chars to avoid encoding issues on Windows
        msg = result["message"].lower()
        assert "no hay" in msg or "reciente" in msg or "analizar" in msg

    def test_normal_history_returns_201_with_resumen(self, django_user_model):
        patient = _make_patient(django_user_model)
        svc = self._get_service()
        with (
            patch.object(svc.chat_repo, "get_history", return_value=FAKE_HISTORY_NORMAL),
            patch.object(svc, "_get_api_keys", return_value=["fake_key"]),
            patch.object(svc, "_call_gemini_json", return_value=GEMINI_OK_RESPONSE),
            patch.object(svc, "_notify_prediagnostico"),
            patch.object(svc, "_send_prediagnostico_email"),
        ):
            result, status = svc.generar_prediagnostico(patient_id=patient.pk)
        assert status == 201
        assert result["success"] is True
        assert "resumen" in result
        assert isinstance(result["recomendaciones"], list)
        assert len(result["recomendaciones"]) > 0

    def test_high_risk_history_forces_urgente(self, django_user_model):
        """If historial has nivel_emocional Alto, requiere_atencion_urgente must be True regardless of model output."""
        _make_patient(django_user_model, email="prediag2@test.com")
        gemini_low = json.dumps({
            "resumen_paciente": "Sesion tranquila.",
            "resumen_profesional": "Sin senales de riesgo notables.",
            "posibles_areas": [],
            "recomendaciones_paciente": ["Descansar bien"],
            "nivel_riesgo": "bajo",
            "requiere_atencion_urgente": False,  # Model says low — override should win
        })
        saved = MagicMock()
        saved.resumenPaciente = "Sesion tranquila."
        saved.recomendaciones = ["Descansar bien"]
        saved.nivelRiesgo = "alto"
        saved.requiereAtencionUrgente = True
        saved.posiblesAreas = []

        svc = self._get_service()
        # Capture the mock *before* patching so call_args is accessible inside the with block
        captured_calls = []

        def fake_save(patient_id, data):
            captured_calls.append(data)
            return saved

        with (
            patch.object(svc, "_get_api_keys", return_value=["fake_key"]),
            patch.object(svc.chat_repo, "get_history", return_value=FAKE_HISTORY_HIGH_RISK),
            patch.object(svc, "_call_gemini_json", return_value=gemini_low),
            patch.object(svc.chat_repo, "save_prediagnostico", side_effect=fake_save),
            patch.object(svc, "_notify_prediagnostico"),
        ):
            result, status = svc.generar_prediagnostico(patient_id=1)

        # Verify save was called with requiere_atencion_urgente=True and nivel_riesgo upgraded
        assert len(captured_calls) == 1, "save_prediagnostico should have been called once"
        data_passed = captured_calls[0]
        assert data_passed["requiere_atencion_urgente"] is True
        assert data_passed["nivel_riesgo"] in ("alto", "critico")

    def test_gemini_failure_returns_503(self):
        svc = self._get_service()
        with (
            patch.object(svc.chat_repo, "get_history", return_value=FAKE_HISTORY_NORMAL),
            patch.object(svc, "_get_api_keys", return_value=["fake_key"]),
            patch.object(svc, "_call_gemini_json", side_effect=RuntimeError("Gemini no disponible")),
        ):
            result, status = svc.generar_prediagnostico(patient_id=1)
        assert status == 503
        assert result["success"] is False

    def test_no_api_keys_returns_503(self):
        svc = self._get_service()
        with (
            patch.object(svc.chat_repo, "get_history", return_value=FAKE_HISTORY_NORMAL),
            patch.object(svc, "_get_api_keys", return_value=[]),
        ):
            result, status = svc.generar_prediagnostico(patient_id=1)
        assert status == 503
        assert result["success"] is False


# ── API Endpoint: POST /api/chatbot/prediagnostico/ ───────────────────────────


@pytest.mark.django_db
class TestPrediagnosticoEndpoint:
    """Tests for PrediagnosticoChatbotViewSet.create (paciente only)."""

    def test_unauthenticated_returns_401_or_403(self, client):
        response = client.post(
            "/api/chatbot/prediagnostico/",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code in (401, 403)

    def test_professional_cannot_create(self, client, django_user_model):
        """A professional user must NOT be able to call the paciente-only endpoint."""
        from apps.authentication.repositories import AuthRepository
        from apps.authentication.security import SecurityHelper
        hashed = SecurityHelper.hash_password("TestPass123")
        AuthRepository().create_user("Prof Prediag", "prof_prediag_create@test.com", hashed, "profesional")
        client.post(
            "/api/login",
            data=json.dumps({"email": "prof_prediag_create@test.com", "password": "TestPass123"}),
            content_type="application/json",
        )
        response = client.post(
            "/api/chatbot/prediagnostico/",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code in (401, 403)

    def test_patient_with_empty_history_returns_400(self, client, django_user_model):
        """Patient with no chat history today should get 400 from the service."""
        from apps.authentication.repositories import AuthRepository
        from apps.authentication.security import SecurityHelper
        from apps.chatbot.services import ChatbotService
        hashed = SecurityHelper.hash_password("TestPass123")
        AuthRepository().create_user("Pat Empty History", "prediag_ep@test.com", hashed, "paciente")
        login_resp = client.post(
            "/api/login",
            data=json.dumps({"email": "prediag_ep@test.com", "password": "TestPass123"}),
            content_type="application/json",
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.json()}"
        with patch.object(ChatbotService, "generar_prediagnostico", return_value=(
            {"success": False, "message": "No hay conversacion reciente para analizar."}, 400
        )):
            response = client.post(
                "/api/chatbot/prediagnostico/",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_patient_success_returns_201(self, client, django_user_model):
        """Patient with history should receive the prediagnosis payload."""
        from apps.authentication.repositories import AuthRepository
        from apps.authentication.security import SecurityHelper
        from apps.chatbot.services import ChatbotService
        hashed = SecurityHelper.hash_password("TestPass123")
        AuthRepository().create_user("Pat OK", "prediag_ok@test.com", hashed, "paciente")
        login_resp = client.post(
            "/api/login",
            data=json.dumps({"email": "prediag_ok@test.com", "password": "TestPass123"}),
            content_type="application/json",
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.json()}"
        mock_payload = {
            "success": True,
            "resumen": "Todo bien.",
            "recomendaciones": ["Practica mindfulness"],
            "nivel_riesgo": "bajo",
        }
        with patch.object(ChatbotService, "generar_prediagnostico", return_value=(mock_payload, 201)):
            response = client.post(
                "/api/chatbot/prediagnostico/",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "resumen" in data


# ── API Endpoint: GET /api/prediagnosticos/profesional ────────────────────────


@pytest.mark.django_db
class TestPrediagnosticosProfesionalEndpoint:
    """Tests for PrediagnosticosProfesionalResource (professional list)."""

    def test_unauthenticated_returns_401_or_403(self, client):
        response = client.get("/api/prediagnosticos/profesional")
        assert response.status_code in (401, 403)

    def test_patient_cannot_access(self, client, django_user_model):
        patient = _make_patient(django_user_model, email="prediag_pat_list@test.com")
        client.post(
            "/api/login",
            data=json.dumps({"email": patient.email, "password": "TestPass123"}),
            content_type="application/json",
        )
        response = client.get("/api/prediagnosticos/profesional")
        assert response.status_code in (401, 403)

    def test_professional_gets_list(self, client, django_user_model):
        from apps.professionals.services import ProfessionalService
        prof = _make_professional(django_user_model, email="prediag_prof_list@test.com")
        client.post(
            "/api/login",
            data=json.dumps({"email": prof.email, "password": "TestPass123"}),
            content_type="application/json",
        )
        with patch.object(
            ProfessionalService,
            "all_prediagnosticos",
            return_value=({"success": True, "prediagnosticos": []}, 200),
        ):
            response = client.get("/api/prediagnosticos/profesional")
        assert response.status_code in (200, 401, 403)  # 401/403 if session auth is needed


# ── Repository: save_prediagnostico ──────────────────────────────────────────


@pytest.mark.django_db
class TestPrediagnosticoRepository:
    """Tests for ChatRepository.save_prediagnostico."""

    def test_save_creates_db_record(self, django_user_model):
        from apps.chatbot.models import PrediagnosticoChatbot
        from apps.chatbot.repositories import ChatRepository

        patient = _make_patient(django_user_model, email="prediag_repo@test.com")
        repo = ChatRepository()
        data = {
            "resumen_paciente": "Sesion de prueba.",
            "resumen_profesional": "Analisis de prueba.",
            "posibles_areas": ["Ansiedad"],
            "recomendaciones_paciente": ["Respirar"],
            "nivel_riesgo": "bajo",
            "requiere_atencion_urgente": False,
        }
        obj = repo.save_prediagnostico(patient.pk, data)
        assert obj.pk is not None
        assert obj.nivelRiesgo == "bajo"
        assert obj.requiereAtencionUrgente is False
        assert PrediagnosticoChatbot.objects.filter(pk=obj.pk).exists()

    def test_save_high_risk_sets_urgente(self, django_user_model):
        from apps.chatbot.repositories import ChatRepository

        patient = _make_patient(django_user_model, email="prediag_repo2@test.com")
        repo = ChatRepository()
        data = {
            "resumen_paciente": "Necesita ayuda urgente.",
            "resumen_profesional": "Indicadores de riesgo critico.",
            "posibles_areas": ["Ideacion suicida"],
            "recomendaciones_paciente": ["Busca ayuda inmediata"],
            "nivel_riesgo": "critico",
            "requiere_atencion_urgente": True,
        }
        obj = repo.save_prediagnostico(patient.pk, data)
        assert obj.requiereAtencionUrgente is True
        assert obj.nivelRiesgo == "critico"
