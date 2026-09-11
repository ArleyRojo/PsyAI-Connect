import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.authentication.models import Register
from apps.documents.models import DocumentosClinicos, DocumentosPaciente, AutorizacionesDocumento
from apps.documents.repositories import DocumentoRepository


@pytest.fixture
def professional(db):
    return Register.objects.create_user(
        email="pro@test.com",
        nombre="Dr. Test",
        password="TestPass123",
        rol="profesional",
    )


@pytest.fixture
def patient(db):
    return Register.objects.create_user(
        email="pac@test.com",
        nombre="Paciente Test",
        password="TestPass123",
        rol="paciente",
    )


@pytest.fixture
def repo():
    return DocumentoRepository()


@pytest.mark.django_db
class TestListProfesionalDocs:
    def test_returns_list_for_patient(self, repo, professional, patient):
        DocumentosClinicos.objects.create(
            idProfesional=professional,
            idPaciente=patient,
            nombreArchivo="historia.pdf",
            rutaArchivo="uploads/historia.pdf",
            categoria="Otro",
            visibilidad="privado",
        )
        DocumentosClinicos.objects.create(
            idProfesional=professional,
            idPaciente=patient,
            nombreArchivo="otro.pdf",
            rutaArchivo="uploads/otro.pdf",
            categoria="Otro",
            visibilidad="compartido",
        )
        docs = repo.list_profesional_docs(professional.idUsuario, patient.idUsuario)
        assert len(docs) == 2
        names = {d["nombreArchivo"] for d in docs}
        assert names == {"historia.pdf", "otro.pdf"}

    def test_excludes_deleted(self, repo, professional, patient):
        DocumentosClinicos.objects.create(
            idProfesional=professional,
            idPaciente=patient,
            nombreArchivo="deleted.pdf",
            rutaArchivo="uploads/deleted.pdf",
            categoria="Otro",
            eliminado=True,
        )
        docs = repo.list_profesional_docs(professional.idUsuario, patient.idUsuario)
        assert len(docs) == 0

    def test_excludes_other_professional(self, repo, professional, patient):
        other_pro = Register.objects.create_user(
            email="other@test.com", nombre="Other", password="pass", rol="profesional"
        )
        DocumentosClinicos.objects.create(
            idProfesional=other_pro,
            idPaciente=patient,
            nombreArchivo="other.pdf",
            rutaArchivo="uploads/other.pdf",
            categoria="Otro",
        )
        docs = repo.list_profesional_docs(professional.idUsuario, patient.idUsuario)
        assert len(docs) == 0


@pytest.mark.django_db
class TestCreateProfesionalDoc:
    def test_creates_and_returns_id(self, repo, professional, patient):
        doc_id = repo.create_profesional_doc(
            professional.idUsuario, patient.idUsuario,
            nombre="test.pdf", ruta="uploads/test.pdf",
            mime="application/pdf", tamano=1024,
            categoria="Otro", visibilidad="privado", notas=None,
        )
        assert doc_id is not None
        doc = DocumentosClinicos.objects.get(idDocumento=doc_id)
        assert doc.nombreArchivo == "test.pdf"
        assert doc.visibilidad == "privado"


@pytest.mark.django_db
class TestUpdateDocVisibility:
    def test_toggles_visibility(self, repo, professional, patient):
        doc = DocumentosClinicos.objects.create(
            idProfesional=professional,
            idPaciente=patient,
            nombreArchivo="vis.pdf",
            rutaArchivo="uploads/vis.pdf",
            visibilidad="privado",
        )
        updated = repo.update_doc_visibility(doc.idDocumento, professional.idUsuario, "compartido")
        assert updated is True
        doc.refresh_from_db()
        assert doc.visibilidad == "compartido"

    def test_returns_false_for_nonexistent(self, repo, professional):
        updated = repo.update_doc_visibility(999, professional.idUsuario, "compartido")
        assert updated is False


@pytest.mark.django_db
class TestSoftDeleteProfesionalDoc:
    def test_soft_deletes(self, repo, professional, patient):
        doc = DocumentosClinicos.objects.create(
            idProfesional=professional,
            idPaciente=patient,
            nombreArchivo="del.pdf",
            rutaArchivo="uploads/del.pdf",
        )
        deleted = repo.soft_delete_profesional_doc(doc.idDocumento, professional.idUsuario)
        assert deleted is True
        doc.refresh_from_db()
        assert doc.eliminado is True

    def test_returns_false_for_nonexistent(self, repo, professional):
        deleted = repo.soft_delete_profesional_doc(999, professional.idUsuario)
        assert deleted is False


@pytest.mark.django_db
class TestListSharedDocsForPatient:
    def test_returns_shared_docs(self, repo, professional, patient):
        DocumentosClinicos.objects.create(
            idProfesional=professional,
            idPaciente=patient,
            nombreArchivo="shared.pdf",
            rutaArchivo="uploads/shared.pdf",
            visibilidad="compartido",
        )
        DocumentosClinicos.objects.create(
            idProfesional=professional,
            idPaciente=patient,
            nombreArchivo="private.pdf",
            rutaArchivo="uploads/private.pdf",
            visibilidad="privado",
        )
        docs = repo.list_shared_docs_for_patient(patient.idUsuario)
        assert len(docs) == 1
        assert docs[0]["nombreArchivo"] == "shared.pdf"
        assert docs[0]["profesionalNombre"] == "Dr. Test"

    def test_excludes_deleted(self, repo, professional, patient):
        DocumentosClinicos.objects.create(
            idProfesional=professional,
            idPaciente=patient,
            nombreArchivo="deleted.pdf",
            rutaArchivo="uploads/deleted.pdf",
            visibilidad="compartido",
            eliminado=True,
        )
        docs = repo.list_shared_docs_for_patient(patient.idUsuario)
        assert len(docs) == 0


@pytest.mark.django_db
class TestListPatientOwnDocs:
    def test_returns_own_docs(self, repo, patient):
        DocumentosPaciente.objects.create(
            idPaciente=patient,
            nombreArchivo="own.pdf",
            rutaArchivo="uploads/own.pdf",
        )
        docs = repo.list_patient_own_docs(patient.idUsuario)
        assert len(docs) == 1
        assert docs[0]["nombreArchivo"] == "own.pdf"

    def test_excludes_deleted(self, repo, patient):
        DocumentosPaciente.objects.create(
            idPaciente=patient,
            nombreArchivo="deleted.pdf",
            rutaArchivo="uploads/deleted.pdf",
            eliminado=True,
        )
        docs = repo.list_patient_own_docs(patient.idUsuario)
        assert len(docs) == 0

    def test_excludes_other_patient(self, repo, patient):
        other_pac = Register.objects.create_user(
            email="other@test.com", nombre="Other", password="pass", rol="paciente"
        )
        DocumentosPaciente.objects.create(
            idPaciente=other_pac,
            nombreArchivo="other.pdf",
            rutaArchivo="uploads/other.pdf",
        )
        docs = repo.list_patient_own_docs(patient.idUsuario)
        assert len(docs) == 0


@pytest.mark.django_db
class TestCreatePatientDoc:
    def test_creates_and_returns_id(self, repo, patient):
        doc_id = repo.create_patient_doc(
            patient.idUsuario,
            nombre="patient.pdf", ruta="uploads/patient.pdf",
            mime="application/pdf", tamano=2048,
            descripcion="Mi documento",
        )
        assert doc_id is not None
        doc = DocumentosPaciente.objects.get(idDocumento=doc_id)
        assert doc.nombreArchivo == "patient.pdf"
        assert doc.descripcion == "Mi documento"
