import os
import uuid

from django.conf import settings

from apps.documents.repositories import DocumentoRepository

UPLOAD_SUBDIR = "uploads/documentos"


class DocumentoService:
    def __init__(self):
        self.repo = DocumentoRepository()

    def _upload_dir(self):
        return os.path.join(settings.STATICFILES_DIRS[0], UPLOAD_SUBDIR) if settings.STATICFILES_DIRS else os.path.join(settings.BASE_DIR, "static", UPLOAD_SUBDIR)

    def _ensure_upload_dir(self):
        d = self._upload_dir()
        os.makedirs(d, exist_ok=True)
        return d

    def _safe_filename(self, filename):
        base, ext = os.path.splitext(filename)
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in base)
        unique = uuid.uuid4().hex[:8]
        return f"{safe}_{unique}{ext}"

    def _format_size(self, bytes_):
        if bytes_ is None:
            return None
        kb = bytes_ / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        return f"{kb/1024:.2f} MB"

    def _format_date(self, dt):
        if dt is None:
            return ""
        return dt.strftime("%d %b %Y") if hasattr(dt, "strftime") else str(dt)

    def _validate_upload(self, file, allowed_extensions=None, max_size_mb=20):
        if allowed_extensions is None:
            allowed_extensions = {"jpg", "jpeg", "png", "pdf", "doc", "docx", "gif", "webp"}
        name = file.name or ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in allowed_extensions:
            return None, f"Extensión no permitida: .{ext}"
        if hasattr(file, "size") and file.size > max_size_mb * 1024 * 1024:
            return None, f"El archivo excede el tamaño máximo de {max_size_mb}MB"
        return name, None

    def list_patient_docs(self, professional_id, patient_id):
        docs = self.repo.list_profesional_docs(professional_id, patient_id)
        result = []
        for d in docs:
            result.append({
                "id": d["idDocumento"],
                "nombre": d["nombreArchivo"],
                "mime": d["tipoMime"],
                "tamano": self._format_size(d["tamanoArchivo"]),
                "tamanoBytes": d["tamanoArchivo"],
                "categoria": d["categoria"],
                "visibilidad": d["visibilidad"],
                "notas": d["notasInternas"],
                "fecha": self._format_date(d["fecha"]),
            })
        return {"success": True, "documentos": result}

    def upload_profesional_doc(self, professional_id, patient_id, file, categoria, visibilidad, notas):
        original_name, error = self._validate_upload(file)
        if error:
            return {"success": False, "message": error}, 400

        upload_path = self._ensure_upload_dir()
        safe_name = self._safe_filename(original_name)

        file_data = file.read()
        file_size = len(file_data)
        with open(os.path.join(upload_path, safe_name), "wb") as f:
            f.write(file_data)

        ruta_relativa = f"{UPLOAD_SUBDIR}/{safe_name}"
        mime = getattr(file, "content_type", None) or "application/octet-stream"
        doc_id = self.repo.create_profesional_doc(
            professional_id, patient_id,
            nombre=original_name,
            ruta=ruta_relativa,
            mime=mime,
            tamano=file_size,
            categoria=categoria or "Otro",
            visibilidad=visibilidad or "privado",
            notas=notas or None,
        )
        return {"success": True, "idDocumento": doc_id, "message": "Documento guardado correctamente"}, 201

    def toggle_doc_visibility(self, doc_id, professional_id):
        doc = self.repo.get_profesional_doc_by_id(doc_id, professional_id)
        if not doc:
            return {"success": False, "message": "Documento no encontrado"}, 404

        new_vis = "compartido" if doc.get("visibilidad") != "compartido" else "privado"
        self.repo.update_doc_visibility(doc_id, professional_id, new_vis)
        return {"success": True, "visibilidad": new_vis, "message": "Visibilidad actualizada"}

    def delete_profesional_doc(self, doc_id, professional_id):
        ok = self.repo.soft_delete_profesional_doc(doc_id, professional_id)
        if not ok:
            return {"success": False, "message": "Documento no encontrado"}, 404
        return {"success": True, "message": "Documento eliminado"}

    def list_patient_dashboard(self, patient_id):
        compartidos = self.repo.list_shared_docs_for_patient(patient_id)
        propios = self.repo.list_patient_own_docs(patient_id)

        return {
            "success": True,
            "compartidos": [
                {
                    "id": d["idDocumento"],
                    "nombre": d["nombreArchivo"],
                    "mime": d["tipoMime"],
                    "tamano": self._format_size(d["tamanoArchivo"]),
                    "categoria": d["categoria"],
                    "fecha": self._format_date(d["fecha"]),
                    "profesional": d["profesionalNombre"],
                }
                for d in compartidos
            ],
            "propios": [
                {
                    "id": d["idDocumento"],
                    "nombre": d["nombreArchivo"],
                    "mime": d["tipoMime"],
                    "tamano": self._format_size(d["tamanoArchivo"]),
                    "descripcion": d["descripcion"],
                    "fecha": self._format_date(d["fecha"]),
                }
                for d in propios
            ],
        }

    def upload_patient_doc(self, patient_id, file, descripcion):
        original_name, error = self._validate_upload(file)
        if error:
            return {"success": False, "message": error}, 400

        upload_path = self._ensure_upload_dir()
        safe_name = self._safe_filename(original_name)

        file_data = file.read()
        file_size = len(file_data)
        with open(os.path.join(upload_path, safe_name), "wb") as f:
            f.write(file_data)

        ruta_relativa = f"{UPLOAD_SUBDIR}/{safe_name}"
        mime = getattr(file, "content_type", None) or "application/octet-stream"
        doc_id = self.repo.create_patient_doc(
            patient_id,
            nombre=original_name,
            ruta=ruta_relativa,
            mime=mime,
            tamano=file_size,
            descripcion=descripcion or None,
        )
        return {"success": True, "idDocumento": doc_id, "message": "Documento subido correctamente"}, 201

    def delete_patient_doc(self, doc_id, patient_id):
        ok = self.repo.soft_delete_patient_doc(doc_id, patient_id)
        if not ok:
            return {"success": False, "message": "Documento no encontrado"}, 404
        return {"success": True, "message": "Documento eliminado"}

    def toggle_autorizacion(self, documento_id, patient_id, professional_id):
        doc = self.repo.get_patient_doc_by_id(documento_id, patient_id)
        if not doc:
            return {"success": False, "message": "Documento no encontrado"}, 404

        aut = self.repo.get_autorizacion(documento_id, professional_id)
        if aut and not aut["revocado"]:
            self.repo.set_autorizacion(documento_id, professional_id, revocado=1)
            return {"success": True, "autorizado": False, "message": "Acceso revocado"}
        else:
            self.repo.set_autorizacion(documento_id, professional_id, revocado=0)
            return {"success": True, "autorizado": True, "message": "Acceso concedido"}

    def get_profesional_doc_for_download(self, id_documento, professional_id):
        doc = self.repo.get_profesional_doc_by_id(id_documento, professional_id)
        if not doc:
            return None, {"success": False, "message": "Documento no encontrado"}, 404
        return doc, None, 200

    def get_patient_doc_for_download(self, id_documento, user_id, rol):
        doc = self.repo.get_patient_doc_by_id_any(id_documento)
        if not doc:
            return None, {"success": False, "message": "Documento no encontrado"}, 404
        if rol == "paciente" and doc["idPaciente"] != user_id:
            return None, {"success": False, "message": "No autorizado"}, 403
        if rol == "profesional":
            aut = self.repo.get_autorizacion(id_documento, user_id)
            if not aut or aut.get("revocado"):
                return None, {"success": False, "message": "No autorizado"}, 403
        return doc, None, 200
