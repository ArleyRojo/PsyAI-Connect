import pytest
from unittest.mock import MagicMock

from apps.patients.services import PatientService


@pytest.fixture
def mock_patient_repo():
    return MagicMock()


@pytest.fixture
def patient_service(mock_patient_repo):
    svc = PatientService()
    svc.repo = mock_patient_repo
    return svc
