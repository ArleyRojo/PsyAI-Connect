import pytest
from unittest.mock import patch, MagicMock
import os


class TestChatbotService:
    def test_build_response_returns_fallback_when_no_api_key(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}, clear=False):
            from app.services import chatbot_service
            with patch('app.services.chatbot_service.chat_repository') as mock_repo:
                mock_repo.get_history.return_value = []
                with patch('app.services.chatbot_service._get_config') as mock_config:
                    mock_config.return_value = {
                        'system_prompt': 'test',
                        'risk_terms': '[]',
                        'crisis_response': 'crisis',
                        'fallback_response': 'fallback message'
                    }
                    result, status = chatbot_service.build_response(1, 'test message')
                    assert status == 200
                    assert result.get('fallback') == True or result.get('respuesta') == 'fallback message'

    def test_get_history_returns_empty_for_no_history(self):
        from app.services import chatbot_service
        with patch('app.services.chatbot_service.chat_repository') as mock_repo:
            mock_repo.get_history.return_value = []
            result, status = chatbot_service.get_history(999)
            assert status == 200
            assert result.get('success') == True
            assert result.get('historial') == []


class TestChatbotRoutes:
    def test_enviar_endpoint_requires_auth(self, client):
        with client.session_transaction() as sess:
            sess.clear()
        response = client.post('/api/chatbot/enviar', json={'mensaje': 'hola'})
        assert response.status_code == 401