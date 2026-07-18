import pytest
from unittest.mock import MagicMock

from apps.chatbot.services import ChatbotService


@pytest.fixture
def mock_chat_repo():
    return MagicMock()


@pytest.fixture
def mock_chatbot_config_repo():
    return MagicMock()


@pytest.fixture
def mock_appointment_repo():
    return MagicMock()


@pytest.fixture
def chatbot_service(mock_chat_repo, mock_chatbot_config_repo, mock_appointment_repo):
    svc = ChatbotService()
    svc.chat_repo = mock_chat_repo
    svc.config_repo = mock_chatbot_config_repo
    svc.appointment_repo = mock_appointment_repo
    return svc
