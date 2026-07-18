import pytest
from unittest.mock import MagicMock

from apps.professionals.services import ProfessionalService


@pytest.fixture
def mock_professional_repo():
    return MagicMock()


@pytest.fixture
def mock_chat_repo():
    return MagicMock()


@pytest.fixture
def professional_service(mock_professional_repo, mock_chat_repo):
    svc = ProfessionalService()
    svc.repo = mock_professional_repo
    svc.chat_repo = mock_chat_repo
    return svc
