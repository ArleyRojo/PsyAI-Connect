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
    mock_appointment_repo.save_appointment.side_effect = lambda appointment, fields=None: appointment.save(update_fields=fields) if fields else appointment.save()
    return svc
