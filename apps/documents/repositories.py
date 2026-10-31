from datetime import datetime

from django.db.models import F, CharField, Value
from django.db.models.functions import Concat

from apps.documents.models import (
    AutorizacionesDocumento,
    DocumentosClinicos,
    DocumentosPaciente,
)
from apps.authentication.models import Register


class DocumentoRepository:
    def list_profesional_docs(self, professional_id, patient_id):
        docs = DocumentosClinicos.objects.filter(
            idProfesional_id=professional_id,
            idPaciente_id=patient_id,
            eliminado=False,
        ).order_by("-fecha")
        return [d.to_dict() for d in docs]

    def create_profesional_doc(
        self, professional_id, patient_id, nombre, ruta, mime, tamano, categoria, visibilidad, notas
    ):
        doc = DocumentosClinicos.objects.create(
            idProfesional_id=professional_id,
            idPaciente_id=patient_id,
            nombreArchivo=nombre,
            rutaArchivo=ruta,
            tipoMime=mime,
            tamanoArchivo=tamano,
            categoria=categoria,
            visibilidad=visibilidad,
            notasInternas=notas,
        )
        return doc.idDocumento

    def update_doc_visibility(self, doc_id, professional_id, visibilidad):
        updated = DocumentosClinicos.objects.filter(
            idDocumento=doc_id,
            idProfesional_id=professional_id,
            eliminado=False,
        ).update(visibilidad=visibilidad)
        return updated > 0

    def soft_delete_profesional_doc(self, doc_id, professional_id):
        updated = DocumentosClinicos.objects.filter(
            idDocumento=doc_id,
            idProfesional_id=professional_id,
        ).update(eliminado=True)
        return updated > 0

    def list_shared_docs_for_patient(self, patient_id):
        docs = (
            DocumentosClinicos.objects.filter(
                idPaciente_id=patient_id,
                visibilidad="compartido",
                eliminado=False,
            )
            .select_related("idProfesional")
            .order_by("-fecha")
        )
        return [
            {
                "idDocumento": d.idDocumento,
                "nombreArchivo": d.nombreArchivo,
                "tipoMime": d.tipoMime,
                "tamanoArchivo": d.tamanoArchivo,
                "categoria": d.categoria,
                "fecha": d.fecha,
                "profesionalNombre": d.idProfesional.nombre,
            }
            for d in docs
        ]

    def list_patient_own_docs(self, patient_id):
        docs = DocumentosPaciente.objects.filter(
            idPaciente_id=patient_id,
            eliminado=False,
        ).order_by("-fecha")
        return [d.to_dict() for d in docs]

    def create_patient_doc(self, patient_id, nombre, ruta, mime, tamano, descripcion):
        doc = DocumentosPaciente.objects.create(
            idPaciente_id=patient_id,
            nombreArchivo=nombre,
            rutaArchivo=ruta,
            tipoMime=mime,
            tamanoArchivo=tamano,
            descripcion=descripcion,
        )
        return doc.idDocumento

    def soft_delete_patient_doc(self, doc_id, patient_id):
        updated = DocumentosPaciente.objects.filter(
            idDocumento=doc_id,
            idPaciente_id=patient_id,
        ).update(eliminado=True)
        return updated > 0

    def get_autorizacion(self, documento_id, professional_id):
        auth = AutorizacionesDocumento.objects.filter(
            idDocumento_id=documento_id,
            idProfesional_id=professional_id,
        ).first()
        if auth:
            return auth.to_dict()
        return None

    def set_autorizacion(self, documento_id, professional_id, revocado=0):
        auth = AutorizacionesDocumento.objects.filter(
            idDocumento_id=documento_id,
            idProfesional_id=professional_id,
        ).first()
        if auth:
            auth.revocado = bool(revocado)
            if revocado:
                auth.fechaRevocacion = datetime.utcnow()
            auth.save(update_fields=["revocado", "fechaRevocacion"])
        else:
            AutorizacionesDocumento.objects.create(
                idDocumento_id=documento_id,
                idProfesional_id=professional_id,
                revocado=bool(revocado),
            )

    def get_patient_doc_by_id(self, doc_id, patient_id):
        doc = DocumentosPaciente.objects.filter(
            idDocumento=doc_id,
            idPaciente_id=patient_id,
            eliminado=False,
        ).first()
        if doc:
            return {
                "idDocumento": doc.idDocumento,
                "nombreArchivo": doc.nombreArchivo,
                "rutaArchivo": doc.rutaArchivo,
            }
        return None

    def get_patient_doc_by_id_any(self, doc_id):
        doc = DocumentosPaciente.objects.filter(
            idDocumento=doc_id,
            eliminado=False,
        ).first()
        if doc:
            return {
                "idDocumento": doc.idDocumento,
                "nombreArchivo": doc.nombreArchivo,
                "rutaArchivo": doc.rutaArchivo,
                "idPaciente": doc.idPaciente_id,
            }
        return None

    def get_profesional_doc_by_id(self, doc_id, professional_id):
        doc = DocumentosClinicos.objects.filter(
            idDocumento=doc_id,
            idProfesional_id=professional_id,
            eliminado=False,
        ).first()
        if doc:
            return {
                "idDocumento": doc.idDocumento,
                "nombreArchivo": doc.nombreArchivo,
                "rutaArchivo": doc.rutaArchivo,
                "visibilidad": doc.visibilidad,
                "idPaciente": doc.idPaciente_id,
            }
        return None
