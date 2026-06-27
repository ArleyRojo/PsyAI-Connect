# ============================================================
# ARCHIVO: repositories/documento_repository.py
# ============================================================

from app.utils.db import db_cursor


def list_profesional_docs(professional_id, patient_id):
    # Lista los documentos clínicos que un profesional ha subido para un paciente específico
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """SELECT idDocumento, nombreArchivo, tipoMime, tamanoArchivo,
                      categoria, visibilidad, notasInternas, fecha, eliminado
               FROM documentosclinicos
               WHERE idProfesional = %s AND idPaciente = %s AND COALESCE(eliminado, 0) = 0
               ORDER BY fecha DESC""",
            (professional_id, patient_id),
        )
        return cursor.fetchall()


def create_profesional_doc(professional_id, patient_id, nombre, ruta, mime, tamano, categoria, visibilidad, notas):
    # Crea un registro de documento clínico subido por un profesional
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """INSERT INTO documentosclinicos
               (idProfesional, idPaciente, nombreArchivo, rutaArchivo, tipoMime, tamanoArchivo, categoria, visibilidad, notasInternas)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (professional_id, patient_id, nombre, ruta, mime, tamano, categoria, visibilidad, notas),
        )
        conn.commit()
        return cursor.lastrowid


def update_doc_visibility(doc_id, professional_id, visibilidad):
    # Cambia la visibilidad de un documento (privado <-> compartido) para que el paciente pueda verlo
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE documentosclinicos SET visibilidad = %s WHERE idDocumento = %s AND idProfesional = %s AND COALESCE(eliminado, 0) = 0",
            (visibilidad, doc_id, professional_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def soft_delete_profesional_doc(doc_id, professional_id):
    # Eliminación lógica de un documento clínico (no se borra físicamente)
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE documentosclinicos SET eliminado = 1 WHERE idDocumento = %s AND idProfesional = %s",
            (doc_id, professional_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def list_shared_docs_for_patient(patient_id):
    # Lista los documentos compartidos con un paciente por sus profesionales
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """SELECT d.idDocumento, d.nombreArchivo, d.tipoMime, d.tamanoArchivo,
                      d.categoria, d.fecha, r.nombre as profesionalNombre
               FROM documentosclinicos d
               JOIN Register r ON d.idProfesional = r.idUsuario
               WHERE d.idPaciente = %s AND d.visibilidad = 'compartido' AND COALESCE(d.eliminado, 0) = 0
               ORDER BY d.fecha DESC""",
            (patient_id,),
        )
        return cursor.fetchall()


def list_patient_own_docs(patient_id):
    # Lista los documentos que el paciente ha subido por sí mismo
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """SELECT idDocumento, nombreArchivo, tipoMime, tamanoArchivo, descripcion, fecha
               FROM documentospaciente
               WHERE idPaciente = %s AND COALESCE(eliminado, 0) = 0
               ORDER BY fecha DESC""",
            (patient_id,),
        )
        return cursor.fetchall()


def create_patient_doc(patient_id, nombre, ruta, mime, tamano, descripcion):
    # Crea un registro de documento subido por el paciente
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """INSERT INTO documentospaciente
               (idPaciente, nombreArchivo, rutaArchivo, tipoMime, tamanoArchivo, descripcion)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (patient_id, nombre, ruta, mime, tamano, descripcion),
        )
        conn.commit()
        return cursor.lastrowid


def soft_delete_patient_doc(doc_id, patient_id):
    # Eliminación lógica de un documento del paciente
    with db_cursor() as (conn, cursor):
        cursor.execute(
            "UPDATE documentospaciente SET eliminado = 1 WHERE idDocumento = %s AND idPaciente = %s",
            (doc_id, patient_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_autorizacion(documento_id, professional_id):
    # Obtiene la autorización de un profesional para acceder a un documento del paciente
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """SELECT idAutorizacion, revocado FROM autorizacionesdocumento
               WHERE idDocumento = %s AND idProfesional = %s""",
            (documento_id, professional_id),
        )
        return cursor.fetchone()


def set_autorizacion(documento_id, professional_id, revocado=0):
    # Concede o revoca autorización a un profesional para ver un documento del paciente
    with db_cursor() as (conn, cursor):
        cursor.execute(
            """INSERT INTO autorizacionesdocumento (idDocumento, idProfesional, revocado)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE revocado = VALUES(revocado), fechaRevocacion = IF(VALUES(revocado)=1, NOW(), NULL)""",
            (documento_id, professional_id, revocado),
        )
        conn.commit()


def get_patient_doc_by_id(doc_id, patient_id):
    # Obtiene un documento del paciente validando que le pertenezca
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT idDocumento, nombreArchivo, rutaArchivo FROM documentospaciente WHERE idDocumento = %s AND idPaciente = %s AND COALESCE(eliminado, 0) = 0",
            (doc_id, patient_id),
        )
        return cursor.fetchone()


def get_patient_doc_by_id_any(doc_id):
    # Obtiene un documento del paciente sin validar propietario (para admins/profesionales autorizados)
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT idDocumento, nombreArchivo, rutaArchivo, idPaciente FROM documentospaciente WHERE idDocumento = %s AND COALESCE(eliminado, 0) = 0",
            (doc_id,),
        )
        return cursor.fetchone()


def get_profesional_doc_by_id(doc_id, professional_id):
    # Obtiene un documento clínico validando que pertenezca al profesional
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT idDocumento, nombreArchivo, rutaArchivo, visibilidad FROM documentosclinicos WHERE idDocumento = %s AND idProfesional = %s AND COALESCE(eliminado, 0) = 0",
            (doc_id, professional_id),
        )
        return cursor.fetchone()
