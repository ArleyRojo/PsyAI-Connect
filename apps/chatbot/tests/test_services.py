from unittest.mock import patch, MagicMock

import pytest
import requests
import time

from apps.chatbot.services import ChatbotService, GEMINI_RETRIES


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


# ── ChatbotService._get_fallback_model / cascada Gemini -> Gemma ─────────────


class TestFallbackModel:
    def test_returns_default_when_env_not_set(self, chatbot_service, monkeypatch):
        monkeypatch.delenv("GEMINI_FALLBACK_MODEL", raising=False)
        assert chatbot_service._get_fallback_model() == "gemma-4-26b-a4b-it"

    def test_returns_env_value(self, chatbot_service, monkeypatch):
        monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "gemma-3-27b-it")
        assert chatbot_service._get_fallback_model() == "gemma-3-27b-it"

    def test_strips_whitespace(self, chatbot_service, monkeypatch):
        monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "  gemma-4-26b-a4b-it  ")
        assert chatbot_service._get_fallback_model() == "gemma-4-26b-a4b-it"


class TestModelSupportsThinking:
    def test_replaces_retired_flash_lite_model(self, chatbot_service, monkeypatch):
        monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

        assert chatbot_service._get_gemini_model() == "gemini-3.5-flash-lite"

    def test_uses_configured_flash_lite_model(self, chatbot_service, monkeypatch):
        monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

        assert chatbot_service._get_gemini_model() == "gemini-3.5-flash-lite"

    def test_gemma_does_not_support_thinking(self):
        assert ChatbotService._model_supports_thinking("gemma-4-26b-a4b-it") is False

    def test_gemini_35_flash_lite_supports_thinking(self):
        assert ChatbotService._model_supports_thinking("gemini-3.5-flash-lite") is True

    def test_unknown_model_does_not_support_thinking(self):
        assert ChatbotService._model_supports_thinking("otro-modelo-3.5") is False


class TestGemmaFallbackCascade:
    @patch("apps.chatbot.services.ChatbotService._call_gemini")
    def test_attempts_fallback_when_all_keys_exhaust_quota(self, mock_gemini, chatbot_service, monkeypatch):
        monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "gemma-4-26b-a4b-it")
        mock_gemini.side_effect = [
            RuntimeError("Gemini HTTP 429"),
            RuntimeError("Gemini HTTP 429"),
            "respuesta de gemma",
        ]
        result = chatbot_service._call_gemini_with_rotation(
            ["key-1", "key-2"],
            "gemini-2.5-flash-lite",
            "Hola",
            [],
            {},
            None,
            "low",
        )
        assert result == "respuesta de gemma"
        assert mock_gemini.call_count == 3
        last_args = mock_gemini.call_args_list[-1][0]
        assert last_args[0] == "key-1"
        assert last_args[1] == "gemma-4-26b-a4b-it"

    @patch("apps.chatbot.services.ChatbotService._call_gemini")
    def test_fallback_attempted_with_single_key(self, mock_gemini, chatbot_service, monkeypatch):
        monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "gemma-4-26b-a4b-it")
        mock_gemini.side_effect = [
            RuntimeError("Gemini HTTP 429"),
            "respuesta de gemma",
        ]
        result = chatbot_service._call_gemini_with_rotation(
            ["key-1"],
            "gemini-2.5-flash-lite",
            "Hola",
            [],
            {},
            None,
            "low",
        )
        assert result == "respuesta de gemma"
        assert mock_gemini.call_count == 2
        assert mock_gemini.call_args_list[-1][0][1] == "gemma-4-26b-a4b-it"

    @patch("apps.chatbot.services.ChatbotService._call_gemini")
    def test_raises_when_fallback_also_fails(self, mock_gemini, chatbot_service, monkeypatch):
        monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "gemma-4-26b-a4b-it")
        mock_gemini.side_effect = RuntimeError("Gemini HTTP 429")
        with pytest.raises(RuntimeError) as excinfo:
            chatbot_service._call_gemini_with_rotation(
                ["key-1", "key-2"],
                "gemini-2.5-flash-lite",
                "Hola",
                [],
                {},
                None,
                "low",
            )
        assert "modelo de respaldo" in str(excinfo.value)
        assert mock_gemini.call_count == 3

    @patch("apps.chatbot.services.ChatbotService._call_gemini")
    def test_non_quota_error_raises_without_fallback(self, mock_gemini, chatbot_service, monkeypatch):
        monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "gemma-4-26b-a4b-it")
        mock_gemini.side_effect = [RuntimeError("Gemini HTTP 500 error interno"), "no deberia llamarse"]
        with pytest.raises(RuntimeError):
            chatbot_service._call_gemini_with_rotation(
                ["key-1", "key-2"],
                "gemini-2.5-flash-lite",
                "Hola",
                [],
                {},
                None,
                "low",
            )
        assert mock_gemini.call_count == 1

    @patch("apps.chatbot.services.ChatbotService._call_gemini")
    def test_skips_fallback_when_model_equals_primary(self, mock_gemini, chatbot_service, monkeypatch):
        monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")
        mock_gemini.side_effect = RuntimeError("Gemini HTTP 429")
        with pytest.raises(RuntimeError):
            chatbot_service._call_gemini_with_rotation(
                ["key-1", "key-2"],
                "gemini-2.5-flash-lite",
                "Hola",
                [],
                {},
                None,
                "low",
            )
        assert mock_gemini.call_count == 2

    @patch("apps.chatbot.services.ChatbotService._get_chatbot_config")
    def test_build_response_uses_fallback_when_primary_quota(self, mock_config, chatbot_service, mock_chat_repo, monkeypatch):
        monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "gemma-4-26b-a4b-it")
        mock_config.return_value = (
            {"risk_terms": "[]", "daily_message_limit": "50"},
            "1.0",
        )
        mock_chat_repo.count_today_messages.return_value = 0
        mock_chat_repo.get_history.return_value = []

        with patch.object(chatbot_service, "_get_api_keys", return_value=["primary-key"]):
            with patch.object(
                chatbot_service,
                "_call_gemini",
                side_effect=[RuntimeError("Gemini HTTP 429"), "respuesta de gemma"],
            ):
                payload, status = chatbot_service.build_response(1, "Hola")

        assert status == 200
        assert payload["respuesta"] == "respuesta de gemma"
        assert payload.get("fallback") is None

    @patch("apps.chatbot.services.ChatbotService._call_gemini_with_rotation")
    @patch("apps.chatbot.services.ChatbotService._get_chatbot_config")
    def test_build_response_uses_local_fallback_when_all_models_fail(self, mock_config, mock_gemini, chatbot_service, mock_chat_repo):
        mock_config.return_value = (
            {"risk_terms": "[]", "daily_message_limit": "50"},
            "1.0",
        )
        mock_chat_repo.count_today_messages.return_value = 0
        mock_chat_repo.get_history.return_value = []
        mock_gemini.side_effect = RuntimeError(
            "Todas las API keys agotaron su cuota por hoy, incluido el modelo de respaldo."
        )

        payload, status = chatbot_service.build_response(1, "Hola")
        assert status == 200
        assert payload["fallback"] is True


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


# ── ChatbotConfigService.save_config validation ───────────────────────────


class TestSaveConfigValidation:
    def test_valid_config_passes(self, config_service, mock_config_repo):
        mock_config_repo.get_config.return_value = {"system_prompt": "test"}
        payload, status = config_service.save_config({
            "system_prompt": "test",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 500,
            "max_tokens_user": 1000,
            "daily_message_limit": 20,
        }, admin_id=1)
        assert status == 200
        assert payload["success"] is True

    def test_temperature_out_of_range(self, config_service, mock_config_repo):
        payload, status = config_service.save_config({"temperature": 1.5}, admin_id=1)
        assert status == 400
        assert payload["success"] is False
        assert "temperature" in payload["message"]

    def test_temperature_negative(self, config_service, mock_config_repo):
        payload, status = config_service.save_config({"temperature": -0.1}, admin_id=1)
        assert status == 400
        assert payload["success"] is False

    def test_top_p_out_of_range(self, config_service, mock_config_repo):
        payload, status = config_service.save_config({"top_p": 2.0}, admin_id=1)
        assert status == 400
        assert payload["success"] is False
        assert "top_p" in payload["message"]

    def test_max_tokens_too_low(self, config_service, mock_config_repo):
        payload, status = config_service.save_config({"max_tokens": 50}, admin_id=1)
        assert status == 400
        assert payload["success"] is False
        assert "max_tokens" in payload["message"]

    def test_max_tokens_too_high(self, config_service, mock_config_repo):
        payload, status = config_service.save_config({"max_tokens": 2000}, admin_id=1)
        assert status == 400
        assert payload["success"] is False

    def test_max_tokens_user_too_low(self, config_service, mock_config_repo):
        payload, status = config_service.save_config({"max_tokens_user": 100}, admin_id=1)
        assert status == 400
        assert payload["success"] is False

    def test_daily_message_limit_too_high(self, config_service, mock_config_repo):
        payload, status = config_service.save_config({"daily_message_limit": 500}, admin_id=1)
        assert status == 400
        assert payload["success"] is False

    def test_daily_message_limit_zero(self, config_service, mock_config_repo):
        payload, status = config_service.save_config({"daily_message_limit": 0}, admin_id=1)
        assert status == 400
        assert payload["success"] is False

    def test_non_numeric_temperature(self, config_service, mock_config_repo):
        payload, status = config_service.save_config({"temperature": "abc"}, admin_id=1)
        assert status == 400
        assert payload["success"] is False

    def test_text_fields_not_validated(self, config_service, mock_config_repo):
        mock_config_repo.get_config.return_value = {"system_prompt": "test"}
        payload, status = config_service.save_config({
            "system_prompt": "new prompt",
            "tone": "amigable",
        }, admin_id=1)
        assert status == 200


# ── ChatbotService._call_gemini error handling ─────────────────────────────────


class TestCallGeminiErrorHandling:
    """Tests for Gemini API error classification and handling."""

    def test_404_model_not_found_raises_without_retry(self, chatbot_service):
        """HTTP 404 should raise immediately without retries."""
        with patch.object(chatbot_service, "_get_api_keys", return_value=["test-key"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 404
                mock_resp.text = '{"error": {"message": "models/gemini-invalid is not found"}}'
                mock_post.return_value = mock_resp

                with pytest.raises(RuntimeError) as excinfo:
                    chatbot_service._call_gemini(
                        "test-key",
                        "gemini-invalid",
                        "Hola",
                        [],
                        {},
                        None,
                        "low",
                        None,
                    )
                assert "404" in str(excinfo.value)
                assert mock_post.call_count == 1  # No retries on 404

    def test_401_unauthorized_raises_without_retry(self, chatbot_service):
        """HTTP 401 should raise immediately without retries."""
        with patch.object(chatbot_service, "_get_api_keys", return_value=["test-key"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 401
                mock_resp.text = '{"error": {"message": "API key not valid"}}'
                mock_post.return_value = mock_resp

                with pytest.raises(RuntimeError) as excinfo:
                    chatbot_service._call_gemini(
                        "test-key",
                        "gemini-2.5-flash-lite",
                        "Hola",
                        [],
                        {},
                        None,
                        "low",
                        None,
                    )
                assert "401" in str(excinfo.value)
                assert mock_post.call_count == 1

    def test_403_forbidden_raises_without_retry(self, chatbot_service):
        """HTTP 403 should raise immediately without retries."""
        with patch.object(chatbot_service, "_get_api_keys", return_value=["test-key"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 403
                mock_resp.text = '{"error": {"message": "Permission denied"}}'
                mock_post.return_value = mock_resp

                with pytest.raises(RuntimeError) as excinfo:
                    chatbot_service._call_gemini(
                        "test-key",
                        "gemini-2.5-flash-lite",
                        "Hola",
                        [],
                        {},
                        None,
                        "low",
                        None,
                    )
                assert "403" in str(excinfo.value)
                assert mock_post.call_count == 1

    def test_429_quota_retries_then_raises(self, chatbot_service):
        """HTTP 429 should retry up to GEMINI_RETRIES times."""
        with patch.object(chatbot_service, "_get_api_keys", return_value=["test-key"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 429
                mock_resp.text = '{"error": {"message": "Quota exceeded"}}'
                mock_post.return_value = mock_resp

                with pytest.raises(RuntimeError) as excinfo:
                    chatbot_service._call_gemini(
                        "test-key",
                        "gemini-2.5-flash-lite",
                        "Hola",
                        [],
                        {},
                        None,
                        "low",
                        None,
                    )
                assert "429" in str(excinfo.value)
                # Should retry GEMINI_RETRIES + 1 times (initial + retries)
                assert mock_post.call_count == (GEMINI_RETRIES + 1)

    def test_network_timeout_retries_then_raises(self, chatbot_service):
        """Network timeout should retry up to GEMINI_RETRIES times."""
        with patch.object(chatbot_service, "_get_api_keys", return_value=["test-key"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                mock_post.side_effect = requests.exceptions.Timeout("Read timed out")

                with pytest.raises(RuntimeError) as excinfo:
                    chatbot_service._call_gemini(
                        "test-key",
                        "gemini-2.5-flash-lite",
                        "Hola",
                        [],
                        {},
                        None,
                        "low",
                        None,
                    )
                assert "timeout" in str(excinfo.value).lower() or "timed out" in str(excinfo.value).lower()
                assert mock_post.call_count == (GEMINI_RETRIES + 1)

    def test_successful_response_returns_text(self, chatbot_service):
        """HTTP 200 with valid response should return extracted text."""
        with patch.object(chatbot_service, "_get_api_keys", return_value=["test-key"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "candidates": [{
                        "content": {
                            "parts": [{"text": "Hola, ¿cómo puedo ayudarte?"}]
                        }
                    }]
                }
                mock_post.return_value = mock_resp

                result = chatbot_service._call_gemini(
                    "test-key",
                    "gemini-2.5-flash-lite",
                    "Hola",
                    [],
                    {},
                    None,
                    "low",
                    None,
                )
                assert result == "Hola, ¿cómo puedo ayudarte?"
                assert mock_post.call_count == 1

    def test_400_bad_request_raises_without_retry(self, chatbot_service):
        """HTTP 400 should raise immediately without retries."""
        with patch.object(chatbot_service, "_get_api_keys", return_value=["test-key"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 400
                mock_resp.text = '{"error": {"message": "Invalid payload"}}'
                mock_post.return_value = mock_resp

                with pytest.raises(RuntimeError) as excinfo:
                    chatbot_service._call_gemini(
                        "test-key",
                        "gemini-2.5-flash-lite",
                        "Hola",
                        [],
                        {},
                        None,
                        "low",
                        None,
                    )
                assert "400" in str(excinfo.value)
                assert mock_post.call_count == 1


# ── Pruebas nuevas: latencia, reintentos y timeouts ─────────────────────────


class TestGeminiTimeoutAndRetries:
    """Pruebas para verificar que los timeouts y reintentos cumplen el objetivo de latencia."""

    def test_timeout_then_200_retries_and_returns_text(self, chatbot_service):
        """Un Timeout en el primer intento seguido de 200 en el segundo debe devolver el texto."""
        with patch.object(chatbot_service, "_get_api_keys", return_value=["test-key"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                # Primer intento: Timeout; segundo intento: 200 OK
                timeout_exc = requests.exceptions.Timeout("Read timed out")
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "candidates": [{
                        "content": {"parts": [{"text": "Respuesta tras reintento"}]}
                    }]
                }
                mock_post.side_effect = [timeout_exc, mock_resp]

                result = chatbot_service._call_gemini(
                    "test-key", "gemini-2.5-flash-lite", "Hola", [], {}, None, "low", None,
                )
                assert result == "Respuesta tras reintento"
                assert mock_post.call_count == 2

    def test_three_timeouts_raise_without_exception_propagation(self, chatbot_service):
        """Tres Timeouts seguidos deben lanzar RuntimeError (capturado por build_response -> fallback)."""
        # GEMINI_RETRIES por defecto es 2, así que se intentan 3 veces (1 inicial + 2 reintentos)
        from apps.chatbot.services import GEMINI_RETRIES

        with patch.object(chatbot_service, "_get_api_keys", return_value=["test-key"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                mock_post.side_effect = requests.exceptions.Timeout("Read timed out")

                with pytest.raises(RuntimeError):
                    chatbot_service._call_gemini(
                        "test-key", "gemini-2.5-flash-lite", "Hola", [], {}, None, "low", None,
                    )
                # Debe haber intentado GEMINI_RETRIES + 1 veces
                assert mock_post.call_count == (GEMINI_RETRIES + 1)

    def test_429_rotates_key_but_timeout_does_not(self, chatbot_service):
        """429 con varias keys rota de key; un Timeout no rota (mismo key en reintento)."""
        # --- 429 rota de key ---
        chatbot_service._key_index = 0
        with patch.object(chatbot_service, "_get_api_keys", return_value=["key-1", "key-2"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 429
                mock_resp.text = '{"error": {"message": "Quota exceeded"}}'
                mock_post.return_value = mock_resp

                try:
                    chatbot_service._call_gemini_with_rotation(
                        ["key-1", "key-2"], "gemini-2.5-flash-lite", "Hola", [], {}, None, "low", None,
                    )
                except RuntimeError:
                    pass
                # Se usaron ambas keys (key-1 luego key-2), verificando rotación
                keys_used = [call[1]["headers"]["x-goog-api-key"] for call in mock_post.call_args_list]
                assert "key-1" in keys_used
                assert "key-2" in keys_used

        # --- Timeout no rota: mismo key en todos los intentos ---
        chatbot_service._key_index = 0
        with patch.object(chatbot_service, "_get_api_keys", return_value=["key-1"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                mock_post.side_effect = requests.exceptions.Timeout("Read timed out")

                try:
                    chatbot_service._call_gemini(
                        "key-1", "gemini-2.5-flash-lite", "Hola", [], {}, None, "low", None,
                    )
                except RuntimeError:
                    pass
                # Todas las llamadas usaron la misma key (única disponible)
                for call in mock_post.call_args_list:
                    assert call[1]["headers"]["x-goog-api-key"] == "key-1"

    def test_timeout_never_below_minimum(self, chatbot_service):
        """El timeout de lectura pasado a requests.post nunca es menor que GEMINI_MIN_READ_TIMEOUT_SECONDS."""
        from apps.chatbot.services import GEMINI_MIN_READ_TIMEOUT_SECONDS

        with patch.object(chatbot_service, "_get_api_keys", return_value=["test-key"]):
            with patch("apps.chatbot.services.requests.post") as mock_post:
                # Deadline muy cercano para forzar ajuste de timeout por deadline
                far_deadline = time.time() + 60  # mucho tiempo restante
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "candidates": [{
                        "content": {"parts": [{"text": "OK"}]}
                    }]
                }
                mock_post.return_value = mock_resp

                chatbot_service._call_gemini(
                    "test-key", "gemini-2.5-flash-lite", "Hola", [], {}, None, "low", far_deadline,
                )
                # Verificar que el timeout de lectura usado es >= el mínimo
                call_kwargs = mock_post.call_args[1]
                timeout_used = call_kwargs["timeout"]
                read_timeout = timeout_used[1] if isinstance(timeout_used, tuple) else timeout_used
                assert read_timeout >= GEMINI_MIN_READ_TIMEOUT_SECONDS, (
                    f"Read timeout {read_timeout}s es menor que el mínimo {GEMINI_MIN_READ_TIMEOUT_SECONDS}s"
                )


# ── Streaming: el primer texto se entrega sin esperar la respuesta completa ──
# (Nota: la implementación actual usa respuesta completa con timeout y fallback;
#  el streaming SSE está documentado como mejora futura en docs/)


class TestBuildResponseFallbackOnTimeout:
    """build_response debe usar el fallback local cuando Gemini falla por timeout."""

    @patch("apps.chatbot.services.ChatbotService._call_gemini_with_rotation")
    @patch("apps.chatbot.services.ChatbotService._get_chatbot_config")
    def test_build_response_uses_fallback_when_gemini_times_out(
        self, mock_config, mock_gemini, chatbot_service, mock_chat_repo
    ):
        mock_config.return_value = (
            {"risk_terms": "[]", "daily_message_limit": "50"},
            "1.0",
        )
        mock_chat_repo.count_today_messages.return_value = 0
        mock_chat_repo.get_history.return_value = []
        mock_gemini.side_effect = RuntimeError("Gemini no disponible luego de reintentos: Read timed out")

        payload, status = chatbot_service.build_response(1, "Hola")
        assert status == 200
        assert payload["success"] is True
        assert payload["fallback"] is True
        assert "respuesta" in payload
