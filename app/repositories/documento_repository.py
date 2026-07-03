from sqlalchemy import select
from app.database.session import db_session
from app.models.documentos_clinicos import DocumentosClinicos
from app.models.documentos_paciente import DocumentosPaciente
from app.models.autorizaciones_documento import AutorizacionesDocumento
from app.models.register import Register


class DocumentoRepository:
    def list_profesional_docs(self, professional_id, patient_id):
        with db_session() as session:
            stmt = select(DocumentosClinicos).where(
                DocumentosClinicos.idProfesional == professional_id,
                DocumentosClinicos.idPaciente == patient_id,
                DocumentosClinicos.eliminado == False,
            ).order_by(DocumentosClinicos.fecha.desc())
            docs = session.execute(stmt).scalars().all()
            return [d.to_dict() for d in docs]

    def create_profesional_doc(self, professional_id, patient_id, nombre, ruta, mime, tamano, categoria, visibilidad, notas):
        with db_session() as session:
            doc = DocumentosClinicos(
                idProfesional=professional_id,
                idPaciente=patient_id,
                nombreArchivo=nombre,
                rutaArchivo=ruta,
                tipoMime=mime,
                tamanoArchivo=tamano,
                categoria=categoria,
                visibilidad=visibilidad,
                notasInternas=notas,
            )
            session.add(doc)
            return doc.idDocumento

    def update_doc_visibility(self, doc_id, professional_id, visibilidad):
        with db_session() as session:
            stmt = select(DocumentosClinicos).where(
                DocumentosClinicos.idDocumento == doc_id,
                DocumentosClinicos.idProfesional == professional_id,
                DocumentosClinicos.eliminado == False,
            )
            doc = session.execute(stmt).scalar_one_or_none()
            if doc:
                doc.visibilidad = visibilidad
                return True
            return False

    def soft_delete_profesional_doc(self, doc_id, professional_id):
        with db_session() as session:
            stmt = select(DocumentosClinicos).where(
                DocumentosClinicos.idDocumento == doc_id,
                DocumentosClinicos.idProfesional == professional_id,
            )
            doc = session.execute(stmt).scalar_one_or_none()
            if doc:
                doc.eliminado = True
                return True
            return False

    def list_shared_docs_for_patient(self, patient_id):
        with db_session() as session:
            stmt = select(
                DocumentosClinicos.idDocumento, DocumentosClinicos.nombreArchivo,
                DocumentosClinicos.tipoMime, DocumentosClinicos.tamanoArchivo,
                DocumentosClinicos.categoria, DocumentosClinicos.fecha,
                Register.nombre.label("profesionalNombre"),
            ).join(Register, DocumentosClinicos.idProfesional == Register.idUsuario).where(
                DocumentosClinicos.idPaciente == patient_id,
                DocumentosClinicos.visibilidad == "compartido",
                DocumentosClinicos.eliminado == False,
            ).order_by(DocumentosClinicos.fecha.desc())
            rows = session.execute(stmt).all()
            return [
                {
                    "idDocumento": r[0], "nombreArchivo": r[1], "tipoMime": r[2],
                    "tamanoArchivo": r[3], "categoria": r[4], "fecha": r[5],
                    "profesionalNombre": r[6],
                }
                for r in rows
            ]

    def list_patient_own_docs(self, patient_id):
        with db_session() as session:
            stmt = select(DocumentosPaciente).where(
                DocumentosPaciente.idPaciente == patient_id,
                DocumentosPaciente.eliminado == False,
            ).order_by(DocumentosPaciente.fecha.desc())
            docs = session.execute(stmt).scalars().all()
            return [d.to_dict() for d in docs]

    def create_patient_doc(self, patient_id, nombre, ruta, mime, tamano, descripcion):
        with db_session() as session:
            doc = DocumentosPaciente(
                idPaciente=patient_id,
                nombreArchivo=nombre,
                rutaArchivo=ruta,
                tipoMime=mime,
                tamanoArchivo=tamano,
                descripcion=descripcion,
            )
            session.add(doc)
            return doc.idDocumento

    def soft_delete_patient_doc(self, doc_id, patient_id):
        with db_session() as session:
            stmt = select(DocumentosPaciente).where(
                DocumentosPaciente.idDocumento == doc_id,
                DocumentosPaciente.idPaciente == patient_id,
            )
            doc = session.execute(stmt).scalar_one_or_none()
            if doc:
                doc.eliminado = True
                return True
            return False

    def get_autorizacion(self, documento_id, professional_id):
        with db_session() as session:
            stmt = select(AutorizacionesDocumento).where(
                AutorizacionesDocumento.idDocumento == documento_id,
                AutorizacionesDocumento.idProfesional == professional_id,
            )
            auth = session.execute(stmt).scalar_one_or_none()
            if auth:
                return auth.to_dict()
            return None

    def set_autorizacion(self, documento_id, professional_id, revocado=0):
        with db_session() as session:
            stmt = select(AutorizacionesDocumento).where(
                AutorizacionesDocumento.idDocumento == documento_id,
                AutorizacionesDocumento.idProfesional == professional_id,
            )
            auth = session.execute(stmt).scalar_one_or_none()
            if auth:
                auth.revocado = bool(revocado)
                if revocado:
                    from datetime import datetime
                    auth.fechaRevocacion = datetime.utcnow()
            else:
                session.add(AutorizacionesDocumento(
                    idDocumento=documento_id,
                    idProfesional=professional_id,
                    revocado=bool(revocado),
                ))

    def get_patient_doc_by_id(self, doc_id, patient_id):
        with db_session() as session:
            stmt = select(DocumentosPaciente).where(
                DocumentosPaciente.idDocumento == doc_id,
                DocumentosPaciente.idPaciente == patient_id,
                DocumentosPaciente.eliminado == False,
            )
            doc = session.execute(stmt).scalar_one_or_none()
            if doc:
                return {"idDocumento": doc.idDocumento, "nombreArchivo": doc.nombreArchivo, "rutaArchivo": doc.rutaArchivo}
            return None

    def get_patient_doc_by_id_any(self, doc_id):
        with db_session() as session:
            stmt = select(DocumentosPaciente).where(
                DocumentosPaciente.idDocumento == doc_id,
                DocumentosPaciente.eliminado == False,
            )
            doc = session.execute(stmt).scalar_one_or_none()
            if doc:
                return {"idDocumento": doc.idDocumento, "nombreArchivo": doc.nombreArchivo, "rutaArchivo": doc.rutaArchivo, "idPaciente": doc.idPaciente}
            return None

    def get_profesional_doc_by_id(self, doc_id, professional_id):
        with db_session() as session:
            stmt = select(DocumentosClinicos).where(
                DocumentosClinicos.idDocumento == doc_id,
                DocumentosClinicos.idProfesional == professional_id,
                DocumentosClinicos.eliminado == False,
            )
            doc = session.execute(stmt).scalar_one_or_none()
            if doc:
                return {"idDocumento": doc.idDocumento, "nombreArchivo": doc.nombreArchivo, "rutaArchivo": doc.rutaArchivo, "visibilidad": doc.visibilidad}
            return None
