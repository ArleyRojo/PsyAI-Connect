import pytest
from unittest.mock import MagicMock

from apps.admin_panel.services import AdminService


@pytest.fixture
def mock_admin_repo():
    return MagicMock()


@pytest.fixture
def admin_service(mock_admin_repo):
    svc = AdminService()
    svc.repo = mock_admin_repo
    return svc
