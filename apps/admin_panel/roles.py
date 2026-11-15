"""Catálogo de roles (HU-11): el admin crea y elimina roles personalizados.

Cada rol personalizado se basa en paciente, profesional o administrador y hereda sus
permisos (el sistema sigue decidiendo los permisos con el rol base). Los 3 roles base
no se pueden eliminar, y tampoco un rol que tenga usuarios asignados.
"""
from apps.admin_panel.repositories import AdminRepository
from apps.authentication.models import RolPersonalizado
from apps.authentication.repositories import AuthRepository

NOMBRE_MIN = 3
NOMBRE_MAX = 40
DESCRIPCIONES_BASE = {
    "paciente": "Usa el chatbot, agenda citas y consulta sus documentos y facturas.",
    "profesional": "Atiende pacientes, agenda, historia clínica, mensajes y facturación.",
    "admin": "Gestiona usuarios, configuración, supervisión y auditoría.",
}
NOMBRES_RESERVADOS = {"paciente", "profesional", "admin", "administrador"}


def _log(accion, detalle, administrador):
    AdminRepository().registrar_log(modulo="roles", accion=accion, detalle=detalle, administrador=administrador)


def catalogo():
    repo = AuthRepository()
    conteo_base, roles_personalizados = repo.get_custom_role_catalog()
    base = [
        {
            "rolBase": clave, "nombre": nombre, "descripcion": DESCRIPCIONES_BASE[clave],
            "usuarios": conteo_base.get(clave, 0), "base": True,
        }
        for clave, nombre in RolPersonalizado.ROLES_BASE
    ]
    personalizados = [
        r.to_dict(usuarios=r.n)
        for r in roles_personalizados
    ]
    return {"success": True, "base": base, "personalizados": personalizados}, 200


def crear(data, administrador="Admin"):
    data = data or {}
    nombre = " ".join(str(data.get("nombre") or "").split())
    descripcion = str(data.get("descripcion") or "").strip()
    rol_base = str(data.get("rolBase") or "").strip().lower()

    if not NOMBRE_MIN <= len(nombre) <= NOMBRE_MAX:
        return {"success": False, "message": f"El nombre debe tener entre {NOMBRE_MIN} y {NOMBRE_MAX} caracteres"}, 400
    if nombre.lower() in NOMBRES_RESERVADOS:
        return {"success": False, "message": "Ese nombre es de un rol base del sistema"}, 400
    repo = AuthRepository()
    if repo.custom_role_exists(nombre):
        return {"success": False, "message": f"Ya existe un rol llamado \"{nombre}\""}, 400
    if rol_base not in dict(RolPersonalizado.ROLES_BASE):
        return {"success": False, "message": "Elige en qué rol base se apoya (paciente, profesional o administrador)"}, 400
    if len(descripcion) > 200:
        return {"success": False, "message": "La descripción no puede superar 200 caracteres"}, 400

    rol = repo.create_custom_role(nombre=nombre, descripcion=descripcion, rolBase=rol_base,
                                  creadoPor=administrador)
    _log("Crear rol", f"Rol \"{nombre}\" creado sobre la base {rol.to_dict()['rolBaseNombre']}", administrador)
    return {"success": True, "message": f"Rol \"{nombre}\" creado", "rol": rol.to_dict(usuarios=0)}, 201


def eliminar(id_rol, administrador="Admin"):
    repo = AuthRepository()
    rol = repo.get_custom_role_for_deletion(id_rol)
    if not rol:
        return {"success": False, "message": "Rol no encontrado"}, 404
    if rol.n:
        return {
            "success": False,
            "message": f"\"{rol.nombre}\" tiene {rol.n} usuario(s). Asígnales otro rol antes de eliminarlo.",
        }, 400
    nombre = rol.nombre
    repo.delete_custom_role(rol)
    _log("Eliminar rol", f"Rol \"{nombre}\" eliminado", administrador)
    return {"success": True, "message": f"Rol \"{nombre}\" eliminado"}, 200
