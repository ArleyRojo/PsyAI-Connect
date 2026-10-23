from unittest.mock import patch, MagicMock

import pytest

from apps.documents.services import DocumentoService


# ── DocumentoService.list_patient_docs ────────────────────────────────────────


class TestListPatientDocs:
    def test_returns_docs(self, documento_service, mock_documento_repo):
        mock_documento_repo.list_profesional_docs.return_value = [
            {
                "idDocumento": 1,
                "nombreArchivo": "historia.pdf",
                "tipoMime": "application/pdf",
                "tamanoArchivo": 1024,
                "categoria": "general",
                "visibilidad": "privado",
                "notasInternas": "Notas",
                "fecha": None,
            },
        ]
        result = documento_service.list_patient_docs(1, 5)
        assert result["success"] is True
        assert len(result["documentos"]) == 1
        assert result["documentos"][0]["nombre"] == "historia.pdf"


# ── DocumentoService.upload_profesional_doc ───────────────────────────────────


class TestUploadProfesionalDoc:
    def test_invalid_extension(self, documento_service):
        fake_file = MagicMock()
        fake_file.name = "doc.exe"
        fake_file.size = 1000
        result, status = documento_service.upload_profesional_doc(1, 5, fake_file, "general", "privado", "")
        assert status == 400

    def test_file_too_large(self, documento_service):
        fake_file = MagicMock()
        fake_file.name = "doc.pdf"
        fake_file.size = 50 * 1024 * 1024
        result, status = documento_service.upload_profesional_doc(1, 5, fake_file, "general", "privado", "")
        assert status == 400

    @patch("apps.documents.services.os.makedirs")
    @patch("apps.documents.services.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=MagicMock)
    def test_valid_upload(self, mock_open, mock_exists, mock_makedirs, documento_service, mock_documento_repo):
        mock_documento_repo.create_profesional_doc.return_value = 1
        fake_file = MagicMock()
        fake_file.name = "historia.pdf"
        fake_file.size = 1000
        fake_file.read.return_value = b"%PDF-1.4" + b"\x00" * 100
        fake_file.content_type = "application/pdf"
        result, status = documento_service.upload_profesional_doc(1, 5, fake_file, "general", "privado", "Notas")
        assert status == 201
        assert result["success"] is True
        mock_documento_repo.create_profesional_doc.assert_called_once()

    @patch("apps.documents.services.os.makedirs")
    @patch("apps.documents.services.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=MagicMock)
    def test_upload_normalizes_ui_categories(self, mock_open, mock_exists, mock_makedirs, documento_service, mock_documento_repo):
        mock_documento_repo.create_profesional_doc.return_value = 1
        fake_file = MagicMock()
        fake_file.name = "historia.pdf"
        fake_file.size = 1000
        fake_file.read.return_value = b"%PDF-1.4" + b"\x00" * 100
        fake_file.content_type = "application/pdf"
        for categoria_ui, expected in [
            ("sesion_inicial", "Historia Clinica"),
            ("evaluacion", "Diagnostico"),
            ("evolucion", "Evolucion"),
            ("consentimiento", "Consentimiento"),
            ("plan_terapeutico", "Otro"),
            ("otro", "Otro"),
            ("", "Otro"),
        ]:
            mock_documento_repo.create_profesional_doc.reset_mock()
            result, status = documento_service.upload_profesional_doc(1, 5, fake_file, categoria_ui, "privado", "")
            assert status == 201
            kwargs = mock_documento_repo.create_profesional_doc.call_args.kwargs
            assert kwargs["categoria"] == expected


# ── DocumentoService.toggle_doc_visibility ────────────────────────────────────


class TestToggleDocVisibility:
    def test_not_found(self, documento_service, mock_documento_repo):
        mock_documento_repo.get_profesional_doc_by_id.return_value = None
        result, status = documento_service.toggle_doc_visibility(999, 1)
        assert status == 404

    def test_successful_toggle(self, documento_service, mock_documento_repo):
        mock_documento_repo.get_profesional_doc_by_id.return_value = {
            "idDocumento": 1,
            "visibilidad": "privado",
        }
        result, status = documento_service.toggle_doc_visibility(1, 1)
        assert status == 200
        assert result["success"] is True
        assert result["visibilidad"] == "compartido"


# ── DocumentoService.delete_profesional_doc ───────────────────────────────────


class TestDeleteProfesionalDoc:
    def test_not_found(self, documento_service, mock_documento_repo):
        mock_documento_repo.soft_delete_profesional_doc.return_value = False
        result, status = documento_service.delete_profesional_doc(999, 1)
        assert status == 404

    def test_successful_delete(self, documento_service, mock_documento_repo):
        mock_documento_repo.soft_delete_profesional_doc.return_value = True
        # La vista hace "payload, status_code = ...": el servicio debe devolver una tupla.
        result, status = documento_service.delete_profesional_doc(1, 1)
        assert status == 200
        assert result["success"] is True


# ── DocumentoService.list_patient_dashboard ───────────────────────────────────


class TestListPatientDashboard:
    def test_returns_dashboard(self, documento_service, mock_documento_repo):
        mock_documento_repo.list_shared_docs_for_patient.return_value = [
            {
                "idDocumento": 1,
                "nombreArchivo": "compartido.pdf",
                "tipoMime": "application/pdf",
                "tamanoArchivo": 1024,
                "categoria": "general",
                "fecha": None,
                "profesionalNombre": "Dr. Garcia",
            },
        ]
        mock_documento_repo.list_patient_own_docs.return_value = [
            {
                "idDocumento": 2,
                "nombreArchivo": "mi_doc.pdf",
                "tipoMime": "application/pdf",
                "tamanoArchivo": 2048,
                "descripcion": "Mi documento",
                "fecha": None,
            },
        ]
        result = documento_service.list_patient_dashboard(5)
        assert result["success"] is True
        assert len(result["compartidos"]) == 1
        assert len(result["propios"]) == 1


# ── DocumentoService.upload_patient_doc ───────────────────────────────────────


class TestUploadPatientDoc:
    def test_invalid_extension(self, documento_service):
        fake_file = MagicMock()
        fake_file.name = "doc.bat"
        fake_file.size = 1000
        result, status = documento_service.upload_patient_doc(5, fake_file, "Desc")
        assert status == 400

    @patch("apps.documents.services.os.makedirs")
    @patch("apps.documents.services.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=MagicMock)
    def test_valid_upload(self, mock_open, mock_exists, mock_makedirs, documento_service, mock_documento_repo):
        mock_documento_repo.create_patient_doc.return_value = 3
        fake_file = MagicMock()
        fake_file.name = "documento.pdf"
        fake_file.size = 1000
        fake_file.read.return_value = b"%PDF-1.4" + b"\x00" * 100
        fake_file.content_type = "application/pdf"
        result, status = documento_service.upload_patient_doc(5, fake_file, "Mi documento")
        assert status == 201
        assert result["success"] is True


# ── DocumentoService.delete_patient_doc ───────────────────────────────────────


class TestDeletePatientDoc:
    def test_not_found(self, documento_service, mock_documento_repo):
        mock_documento_repo.soft_delete_patient_doc.return_value = False
        result, status = documento_service.delete_patient_doc(999, 5)
        assert status == 404

    def test_successful_delete(self, documento_service, mock_documento_repo):
        mock_documento_repo.soft_delete_patient_doc.return_value = True
        # La vista hace "payload, status_code = ...": el servicio debe devolver una tupla.
        result, status = documento_service.delete_patient_doc(1, 5)
        assert status == 200
        assert result["success"] is True


# ── DocumentoService.toggle_autorizacion ──────────────────────────────────────


class TestToggleAutorizacion:
    def test_not_found(self, documento_service, mock_documento_repo):
        mock_documento_repo.get_patient_doc_by_id.return_value = None
        result, status = documento_service.toggle_autorizacion(999, 5, 1)
        assert status == 404

    def test_successful_toggle_grant(self, documento_service, mock_documento_repo):
        mock_documento_repo.get_patient_doc_by_id.return_value = {"idDocumento": 1}
        mock_documento_repo.get_autorizacion.return_value = None
        result, status = documento_service.toggle_autorizacion(1, 5, 1)
        assert status == 200
        assert result["success"] is True
        assert result["autorizado"] is True

    def test_successful_toggle_revoke(self, documento_service, mock_documento_repo):
        mock_documento_repo.get_patient_doc_by_id.return_value = {"idDocumento": 1}
        mock_documento_repo.get_autorizacion.return_value = {"revocado": False}
        result, status = documento_service.toggle_autorizacion(1, 5, 1)
        assert status == 200
        assert result["success"] is True
        assert result["autorizado"] is False


# ── DocumentoService._validate_upload ─────────────────────────────────────────


class TestValidateUpload:
    def test_valid_file(self, documento_service):
        fake_file = MagicMock()
        fake_file.name = "doc.pdf"
        fake_file.size = 1000
        filename, error = documento_service._validate_upload(fake_file)
        assert filename is not None
        assert error is None

    def test_invalid_extension(self, documento_service):
        fake_file = MagicMock()
        fake_file.name = "doc.exe"
        fake_file.size = 1000
        filename, error = documento_service._validate_upload(fake_file)
        assert filename is None
        assert error is not None

    def test_oversized_file(self, documento_service):
        fake_file = MagicMock()
        fake_file.name = "doc.pdf"
        fake_file.size = 100 * 1024 * 1024
        filename, error = documento_service._validate_upload(fake_file, max_size_mb=20)
        assert filename is None
        assert error is not None
