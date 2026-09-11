import json
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory

from apps.core.permissions import IsAuthenticatedDRF
from apps.documents.views import (
    AutorizacionToggleView,
    DocumentoPacienteDashboardViewSet,
    DocumentoPacienteOwnViewSet,
    DocumentoProfesionalViewSet,
)


@pytest.fixture
def rf():
    return APIRequestFactory()


def _auth_profesional(_self, request, view):
    request.user_id = 1
    request.user_role = "profesional"
    request.user_name = "Prof Test"
    return True


def _auth_paciente(_self, request, view):
    request.user_id = 1
    request.user_role = "paciente"
    request.user_name = "Paciente Test"
    return True


@pytest.fixture
def mock_auth_profesional():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_profesional):
        yield


@pytest.fixture
def mock_auth_paciente():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_paciente):
        yield


# ── DocumentoProfesionalViewSet list (GET) ────────────────────────────────


class TestDocumentoProfesionalListViewGET:
    def test_requires_auth(self, rf):
        req = rf.get("/api/documentos/profesional/5")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = DocumentoProfesionalViewSet.as_view({"get": "list"})
            resp = view(req, id_paciente=5)

        assert resp.status_code == 403

    def test_returns_docs(self, rf, mock_auth_profesional):
        req = rf.get("/api/documentos/profesional/5")
        req.session = MagicMock()

        with patch("apps.documents.views.documento_service") as mock_svc:
            mock_svc.list_patient_docs.return_value = (
                {"success": True, "documentos": []},
                200,
            )
            view = DocumentoProfesionalViewSet.as_view({"get": "list"})
            resp = view(req, id_paciente=5)

        assert resp.status_code == 200
        assert resp.data["success"] is True


# ── DocumentoProfesionalViewSet create (POST) ────────────────────────────


class TestDocumentoProfesionalListViewPOST:
    def test_requires_auth(self, rf):
        req = rf.post("/api/documentos/profesional/5")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = DocumentoProfesionalViewSet.as_view({"post": "create"})
            resp = view(req, id_paciente=5)

        assert resp.status_code == 403

    def test_upload_requires_file(self, rf, mock_auth_profesional):
        req = rf.post("/api/documentos/profesional/5")
        req.session = MagicMock()

        view = DocumentoProfesionalViewSet.as_view({"post": "create"})
        resp = view(req, id_paciente=5)

        assert resp.status_code == 400
        assert resp.data["success"] is False

    def test_upload_success(self, rf, mock_auth_profesional):
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile(
            "test.pdf", b"%PDF-1.4" + b"\x00" * 100, content_type="application/pdf"
        )
        req = rf.post(
            "/api/documentos/profesional/5",
            {"categoria": "Otro", "visibilidad": "privado", "notasInternas": ""},
        )
        req.FILES["archivo"] = file
        req.session = MagicMock()

        with patch("apps.documents.views.documento_service") as mock_svc:
            mock_svc.upload_profesional_doc.return_value = (
                {"success": True, "idDocumento": 1, "message": "Guardado"},
                201,
            )
            view = DocumentoProfesionalViewSet.as_view({"post": "create"})
            resp = view(req, id_paciente=5)

        assert resp.status_code == 201
        assert resp.data["success"] is True


# ── DocumentoProfesionalViewSet partial_update (PATCH) ────────────────────


class TestDocumentoProfesionalDetailViewPATCH:
    def test_requires_auth(self, rf):
        req = rf.patch("/api/documentos/profesional/doc/1")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = DocumentoProfesionalViewSet.as_view({"patch": "partial_update"})
            resp = view(req, id_documento=1)

        assert resp.status_code == 403

    def test_toggles_visibility(self, rf, mock_auth_profesional):
        req = rf.patch("/api/documentos/profesional/doc/1")
        req.session = MagicMock()

        with patch("apps.documents.views.documento_service") as mock_svc:
            mock_svc.toggle_doc_visibility.return_value = (
                {"success": True, "visibilidad": "compartido", "message": "Actualizado"},
                200,
            )
            view = DocumentoProfesionalViewSet.as_view({"patch": "partial_update"})
            resp = view(req, id_documento=1)

        assert resp.status_code == 200
        assert resp.data["visibilidad"] == "compartido"


# ── DocumentoProfesionalViewSet destroy (DELETE) ──────────────────────────


class TestDocumentoProfesionalDetailViewDELETE:
    def test_requires_auth(self, rf):
        req = rf.delete("/api/documentos/profesional/doc/1")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = DocumentoProfesionalViewSet.as_view({"delete": "destroy"})
            resp = view(req, id_documento=1)

        assert resp.status_code == 403

    def test_delete_success(self, rf, mock_auth_profesional):
        req = rf.delete("/api/documentos/profesional/doc/1")
        req.session = MagicMock()

        with patch("apps.documents.views.documento_service") as mock_svc:
            mock_svc.delete_profesional_doc.return_value = (
                {"success": True, "message": "Eliminado"},
                200,
            )
            view = DocumentoProfesionalViewSet.as_view({"delete": "destroy"})
            resp = view(req, id_documento=1)

        assert resp.status_code == 200
        assert resp.data["success"] is True


# ── DocumentoPacienteDashboardViewSet list (GET) ──────────────────────────


class TestDocumentoPacienteDashboardViewGET:
    def test_requires_auth(self, rf):
        req = rf.get("/api/documentos/paciente/dashboard")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = DocumentoPacienteDashboardViewSet.as_view({"get": "list"})
            resp = view(req)

        assert resp.status_code == 403

    def test_returns_dashboard(self, rf, mock_auth_paciente):
        req = rf.get("/api/documentos/paciente/dashboard")
        req.session = MagicMock()

        with patch("apps.documents.views.documento_service") as mock_svc:
            mock_svc.list_patient_dashboard.return_value = {
                "success": True,
                "compartidos": [],
                "propios": [],
            }
            view = DocumentoPacienteDashboardViewSet.as_view({"get": "list"})
            resp = view(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True


# ── DocumentoPacienteOwnViewSet list (GET) ────────────────────────────────


class TestDocumentoPacienteOwnListViewGET:
    def test_requires_auth(self, rf):
        req = rf.get("/api/documentos/paciente")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = DocumentoPacienteOwnViewSet.as_view({"get": "list"})
            resp = view(req)

        assert resp.status_code == 403

    def test_returns_own_docs(self, rf, mock_auth_paciente):
        req = rf.get("/api/documentos/paciente")
        req.session = MagicMock()

        with patch("apps.documents.views.documento_service") as mock_svc:
            mock_svc.repo = MagicMock()
            mock_svc.repo.list_patient_own_docs.return_value = []
            mock_svc._format_size.return_value = "1.0 KB"
            mock_svc._format_date.return_value = "01 Jan 2026"
            view = DocumentoPacienteOwnViewSet.as_view({"get": "list"})
            resp = view(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True


# ── DocumentoPacienteOwnViewSet create (POST) ─────────────────────────────


class TestDocumentoPacienteOwnListViewPOST:
    def test_requires_auth(self, rf):
        req = rf.post("/api/documentos/paciente")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = DocumentoPacienteOwnViewSet.as_view({"post": "create"})
            resp = view(req)

        assert resp.status_code == 403

    def test_upload_requires_file(self, rf, mock_auth_paciente):
        req = rf.post("/api/documentos/paciente")
        req.session = MagicMock()

        view = DocumentoPacienteOwnViewSet.as_view({"post": "create"})
        resp = view(req)

        assert resp.status_code == 400

    def test_upload_success(self, rf, mock_auth_paciente):
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile(
            "doc.pdf", b"%PDF-1.4" + b"\x00" * 100, content_type="application/pdf"
        )
        req = rf.post("/api/documentos/paciente", {"descripcion": "Test"})
        req.FILES["archivo"] = file
        req.session = MagicMock()

        with patch("apps.documents.views.documento_service") as mock_svc:
            mock_svc.upload_patient_doc.return_value = (
                {"success": True, "idDocumento": 1, "message": "Subido"},
                201,
            )
            view = DocumentoPacienteOwnViewSet.as_view({"post": "create"})
            resp = view(req)

        assert resp.status_code == 201
        assert resp.data["success"] is True


# ── AutorizacionToggleView POST ───────────────────────────────────────────


class TestAutorizacionToggleViewPOST:
    def test_requires_auth(self, rf):
        req = rf.post("/api/documentos/autorizacion/1")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = AutorizacionToggleView.as_view()
            resp = view(req, id_documento=1)

        assert resp.status_code == 403

    def test_toggle_success(self, rf, mock_auth_paciente):
        req = rf.post(
            "/api/documentos/autorizacion/1",
            data=json.dumps({"idPaciente": 5}),
            content_type="application/json",
        )
        req.session = MagicMock()

        with patch("apps.documents.views.documento_service") as mock_svc:
            mock_svc.toggle_autorizacion.return_value = (
                {"success": True, "autorizado": True, "message": "Acceso concedido"},
                200,
            )
            view = AutorizacionToggleView.as_view()
            resp = view(req, id_documento=1)

        assert resp.status_code == 200
        assert resp.data["autorizado"] is True
