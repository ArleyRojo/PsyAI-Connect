import pytest
from unittest.mock import MagicMock

from apps.documents.services import DocumentoService


@pytest.fixture
def mock_documento_repo():
    return MagicMock()


@pytest.fixture
def documento_service(mock_documento_repo):
    svc = DocumentoService()
    svc.repo = mock_documento_repo
    svc._professional_can_access_patient = lambda professional_id, patient_id: True
    return svc
