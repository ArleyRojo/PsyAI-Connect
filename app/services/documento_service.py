import os

from flask import current_app

from app.repositories import documento_repository
from app.utils.upload_validation import validate_upload

UPLOAD_SUBDIR = "uploads/documentos"


def _upload_dir():
    return os.path.join(current_app.root_path, "static", UPLOAD_SUBDIR)


def _ensure_upload_dir():
    d = _upload_dir()
    os.makedirs(d, exist_ok=True)
    return d


def _format_size(bytes_):
    if bytes_ is None:
        return None
    kb = bytes_ / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    return f"{kb/1024:.2f} MB"


def _format_date(dt):
    if dt is None:
        return ""
    return dt.strftime("%d %b %Y") if hasattr(dt, "strftime") else str(dt)


# ── PROFESSIONAL ──


def list_patient_docs(professional_id, patient_id):
    docs = documento_repository.list_profesional_docs(professional_id, patient_id)
    result = []
    for d in docs:
        result.append({
            "id": d["idDocumento"],
            "nombre": d["nombreArchivo"],
            "mime": d["tipoMime"],
            "tamano": _format_size(d["tamanoArchivo"]),
            "tamanoBytes": d["tamanoArchivo"],
            "categoria": d["categoria"],
            "visibilidad": d["visibilidad"],
            "notas": d["notasInternas"],
            "fecha": _format_date(d["fecha"]),
        })
    return {"success": True, "documentos": result}


def upload_profesional_doc(professional_id, patient_id, file, categoria, visibilidad, notas):
    safe_name, error = validate_upload(
        file,
        allowed_extensions={"jpg", "jpeg", "png", "pdf", "doc", "docx", "gif", "webp"},
        max_size_mb=20,
    )
    if error:
        return {"success": False, "message": error}, 400

    upload_path = _ensure_upload_dir()
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    file.save(os.path.join(upload_path, safe_name))

    ruta_relativa = f"{UPLOAD_SUBDIR}/{safe_name}"
    doc_id = documento_repository.create_profesional_doc(
        professional_id, patient_id,
        nombre=file.filename,
        ruta=ruta_relativa,
        mime=file.content_type or "application/octet-stream",
        tamano=file_size,
        categoria=categoria or "Otro",
        visibilidad=visibilidad or "privado",
        notas=notas or None,
    )
    return {"success": True, "idDocumento": doc_id, "message": "Documento guardado correctamente"}, 201


def toggle_doc_visibility(doc_id, professional_id):
    doc = documento_repository.get_profesional_doc_by_id(doc_id, professional_id)
    if not doc:
        return {"success": False, "message": "Documento no encontrado"}, 404

    new_vis = "compartido" if doc.get("visibilidad") != "compartido" else "privado"
    documento_repository.update_doc_visibility(doc_id, professional_id, new_vis)
    return {"success": True, "visibilidad": new_vis, "message": "Visibilidad actualizada"}


def delete_profesional_doc(doc_id, professional_id):
    ok = documento_repository.soft_delete_profesional_doc(doc_id, professional_id)
    if not ok:
        return {"success": False, "message": "Documento no encontrado"}, 404
    return {"success": True, "message": "Documento eliminado"}


# ── PATIENT ──


def list_patient_dashboard(patient_id):
    compartidos = documento_repository.list_shared_docs_for_patient(patient_id)
    propios = documento_repository.list_patient_own_docs(patient_id)

    return {
        "success": True,
        "compartidos": [
            {
                "id": d["idDocumento"],
                "nombre": d["nombreArchivo"],
                "mime": d["tipoMime"],
                "tamano": _format_size(d["tamanoArchivo"]),
                "categoria": d["categoria"],
                "fecha": _format_date(d["fecha"]),
                "profesional": d["profesionalNombre"],
            }
            for d in compartidos
        ],
        "propios": [
            {
                "id": d["idDocumento"],
                "nombre": d["nombreArchivo"],
                "mime": d["tipoMime"],
                "tamano": _format_size(d["tamanoArchivo"]),
                "descripcion": d["descripcion"],
                "fecha": _format_date(d["fecha"]),
            }
            for d in propios
        ],
    }


def upload_patient_doc(patient_id, file, descripcion):
    safe_name, error = validate_upload(
        file,
        allowed_extensions={"jpg", "jpeg", "png", "pdf", "doc", "docx", "gif", "webp"},
        max_size_mb=20,
    )
    if error:
        return {"success": False, "message": error}, 400

    upload_path = _ensure_upload_dir()
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    file.save(os.path.join(upload_path, safe_name))

    ruta_relativa = f"{UPLOAD_SUBDIR}/{safe_name}"
    doc_id = documento_repository.create_patient_doc(
        patient_id,
        nombre=file.filename,
        ruta=ruta_relativa,
        mime=file.content_type or "application/octet-stream",
        tamano=file_size,
        descripcion=descripcion or None,
    )
    return {"success": True, "idDocumento": doc_id, "message": "Documento subido correctamente"}, 201


def delete_patient_doc(doc_id, patient_id):
    ok = documento_repository.soft_delete_patient_doc(doc_id, patient_id)
    if not ok:
        return {"success": False, "message": "Documento no encontrado"}, 404
    return {"success": True, "message": "Documento eliminado"}


def toggle_autorizacion(documento_id, patient_id, professional_id):
    doc = documento_repository.get_patient_doc_by_id(documento_id, patient_id)
    if not doc:
        return {"success": False, "message": "Documento no encontrado"}, 404

    aut = documento_repository.get_autorizacion(documento_id, professional_id)
    if aut and not aut["revocado"]:
        documento_repository.set_autorizacion(documento_id, professional_id, revocado=1)
        return {"success": True, "autorizado": False, "message": "Acceso revocado"}
    else:
        documento_repository.set_autorizacion(documento_id, professional_id, revocado=0)
        return {"success": True, "autorizado": True, "message": "Acceso concedido"}
