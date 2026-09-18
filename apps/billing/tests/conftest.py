import pytest
from unittest.mock import MagicMock

from apps.billing.services import InvoiceService


@pytest.fixture
def mock_invoice_repo():
    return MagicMock()


@pytest.fixture
def invoice_service(mock_invoice_repo):
    svc = InvoiceService()
    svc.repo = mock_invoice_repo
    return svc
