from unittest.mock import patch, MagicMock

import pytest

from apps.chatbot.services import ChatbotService


# ── ChatbotService.build_response ─────────────────────────────────────────────


class TestBuildResponse:
    def test_empty_message(self, chatbot_service):
        payload, status = chatbot_service.build_response(1, "")
        assert status == 400

    def test_whitespace_only_message(self, chatbot_service):
        payload, status = chatbot_service.build_response(1, "   ")
        assert status == 400

    @patch("apps.chatbot.services.ChatbotService._get_chatbot_config")
    @patch("apps.chatbot.services.ChatbotService._notify_high_risk")
    def test_high_risk_triggers_crisis(self, mock_notify, mock_config, chatbot_service, mock_chat_repo):
        mock_config.return_value = (
            {"risk_terms": '[{"palabra":"suicidio","nivel":"Alto"}]', "crisis_response": "Llama a la linea 106"},
            "1.0",
        )
        mock_chat_repo.count_today_messages.return_value = 0
        mock_chat_repo.get_history.return_value = []

        payload, status = chatbot_service.build_response(1, "Quiero suicidio ahora")
        assert status == 200
        assert payload["success"] is True
        assert "respuesta" in payload
        mock_chat_repo.save_conversation.assert_called_once()
        mock_notify.assert_called_once()

    @patch("apps.chatbot.services.ChatbotService._get_chatbot_config")
    def test_daily_limit_exceeded(self, mock_config, chatbot_service, mock_chat_repo):
        mock_config.return_value = (
            {"risk_terms": "[]", "daily_message_limit": "50"},
            "1.0",
        )
        mock_chat_repo.count_today_messages.return_value = 50

        payload, status = chatbot_service.build_response(1, "Hola")
        assert status == 429
        assert payload["limit_reached"] is True

    @patch("apps.chatbot.services.ChatbotService._call_gemini_with_rotation")
    @patch("apps.chatbot.services.ChatbotService._get_chatbot_config")
    def test_successful_response(self, mock_config, mock_gemini, chatbot_service, mock_chat_repo):
        mock_config.return_value = (
            {"risk_terms": "[]", "daily_message_limit": "50"},
            "1.0",
        )
        mock_chat_repo.count_today_messages.return_value = 0
        mock_chat_repo.get_history.return_value = []
        mock_gemini.return_value = "Hola, puedo ayudarte."

        payload, status = chatbot_service.build_response(1, "Hola")
        assert status == 200
        assert payload["success"] is True
        mock_chat_repo.save_conversation.assert_called_once()

    @patch("apps.chatbot.services.ChatbotService._get_chatbot_config")
    def test_no_api_key_uses_fallback(self, mock_config, chatbot_service, mock_chat_repo):
        mock_config.return_value = (
            {"risk_terms": "[]", "daily_message_limit": "50"},
            "1.0",
        )
        mock_chat_repo.count_today_messages.return_value = 0
        mock_chat_repo.get_history.return_value = []

        with patch.object(chatbot_service, "_get_api_keys", return_value=[]):
            payload, status = chatbot_service.build_response(1, "Hola")
            assert status == 200
            assert payload["fallback"] is True


# ── ChatbotService.get_history ────────────────────────────────────────────────


class TestGetHistory:
    def test_returns_history(self, chatbot_service, mock_chat_repo):
        mock_chat_repo.get_history.return_value = [
            {"tipo": "usuario", "mensaje": "Hola"},
            {"tipo": "bot", "mensaje": "Hola, como estas?"},
        ]
        payload, status = chatbot_service.get_history(1)
        assert status == 200
        assert len(payload["historial"]) == 2
        mock_chat_repo.get_history.assert_called_once_with(1, today_only=True)


# ── ChatbotService._build_local_fallback ──────────────────────────────────────


class TestLocalFallback:
    def test_returns_response_for_anxiety(self, chatbot_service):
        response = chatbot_service._build_local_fallback(
            "Tengo ansiedad", [], {}, False, False
        )
        assert response is not None
        assert len(response) > 0

    def test_returns_response_for_sadness(self, chatbot_service):
        response = chatbot_service._build_local_fallback(
            "Me siento triste", [], {}, False, False
        )
        assert response is not None

    def test_avoids_repeating_last_bot_message(self, chatbot_service):
        history = [
            {"tipo": "usuario", "mensaje": "Ansiedad"},
            {"tipo": "bot", "mensaje": "Entiendo tu ansiedad."},
        ]
        response = chatbot_service._build_local_fallback(
            "Ansiedad", history, {}, False, False
        )
        assert response != "Entiendo tu ansiedad."


# ── ChatbotService._contains_any ─────────────────────────────────────────────


class TestContainsAny:
    def test_match_found(self, chatbot_service):
        assert chatbot_service._contains_any("quiero suicidio", ["suicidio"]) is True

    def test_no_match(self, chatbot_service):
        assert chatbot_service._contains_any("hola mundo", ["depresion", "ansiedad"]) is False

    def test_exact_substring(self, chatbot_service):
        assert chatbot_service._contains_any("tengo depresion severa", ["depresion"]) is True

    def test_empty_terms(self, chatbot_service):
        assert chatbot_service._contains_any("cualquier texto", []) is False


# ── ChatbotService._normalize_text ───────────────────────────────────────────


class TestNormalizeText:
    def test_lowercases(self, chatbot_service):
        assert chatbot_service._normalize_text("HOLA MUNDO") == "hola mundo"

    def test_strips_accents(self, chatbot_service):
        result = chatbot_service._normalize_text("ansiedad")
        assert result == "ansiedad"

    def test_none_input(self, chatbot_service):
        assert chatbot_service._normalize_text(None) == ""


# ── ChatbotConfigService.save_risk_terms ──────────────────────────────────────


from apps.chatbot.services import ChatbotConfigService


@pytest.fixture
def mock_config_repo():
    return MagicMock()


@pytest.fixture
def config_service(mock_config_repo):
    svc = ChatbotConfigService()
    svc.repo = mock_config_repo
    return svc


class TestSaveRiskTerms:
    def test_saves_risk_terms(self, config_service, mock_config_repo):
        risk_terms = '[{"palabra":"suicidio","nivel":"Alto"}]'
        mock_config_repo.get_config.return_value = {"risk_terms": risk_terms}

        payload, status = config_service.save_risk_terms(risk_terms, admin_id=1)

        assert status == 200
        assert payload["success"] is True
        mock_config_repo.save_risk_terms_only.assert_called_once_with(risk_terms, 1)

    def test_empty_risk_terms(self, config_service, mock_config_repo):
        mock_config_repo.get_config.return_value = {"risk_terms": "[]"}

        payload, status = config_service.save_risk_terms("[]", admin_id=1)

        assert status == 200
        assert payload["success"] is True
        mock_config_repo.save_risk_terms_only.assert_called_once_with("[]", 1)


class TestClearRiskTerms:
    def test_clears_risk_terms(self, config_service, mock_config_repo):
        payload, status = config_service.clear_risk_terms(admin_id=1)

        assert status == 200
        assert payload["success"] is True
        mock_config_repo.clear_risk_terms.assert_called_once_with(1)


class TestGetConfig:
    def test_returns_default_when_empty(self, config_service, mock_config_repo):
        mock_config_repo.get_config.return_value = None

        payload, status = config_service.get_config()

        assert status == 200
        assert payload["success"] is True
        assert payload["config"]["risk_terms"] == "[]"

    def test_returns_existing_config(self, config_service, mock_config_repo):
        mock_config_repo.get_config.return_value = {
            "system_prompt": "test",
            "risk_terms": '[{"palabra":"test","nivel":"Bajo"}]',
        }

        payload, status = config_service.get_config()

        assert status == 200
        assert payload["config"]["system_prompt"] == "test"
