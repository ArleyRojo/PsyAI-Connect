import pytest
from unittest.mock import MagicMock, patch

from apps.authentication.services import AuthService


@pytest.fixture
def mock_auth_repo():
    return MagicMock()


@pytest.fixture
def mock_security_repo():
    repo = MagicMock()
    repo.check_rate_limit.return_value = (False, 0)
    repo.check_brute_force.return_value = (False, 0)
    return repo


@pytest.fixture
def auth_service(mock_auth_repo, mock_security_repo):
    svc = AuthService()
    svc.repo = mock_auth_repo
    svc.security_repo = mock_security_repo
    return svc
