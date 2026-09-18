import pytest
from unittest.mock import MagicMock

from apps.scheduling.services import AppointmentService


@pytest.fixture
def mock_appointment_repo():
    return MagicMock()


@pytest.fixture
def appointment_service(mock_appointment_repo):
    svc = AppointmentService()
    svc.repo = mock_appointment_repo
    return svc
