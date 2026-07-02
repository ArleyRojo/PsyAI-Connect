# ============================================================
# ARCHIVO: services/mensajes_service.py
# ============================================================

from app.repositories import mensajes_repository


def get_contactos_con_mensajes(id_usuario, lista_contactos, id_field="idUsuario"):
    """
    Enriquece una lista de contactos con último mensaje, no leídos y estado online.
    Retorna la lista ordenada (no leídos primero, luego por fecha desc).
    """
    from app.services.telemetry_service import get_active_user_ids
    online_ids = set(get_active_user_ids())
    resultado = []
    for contacto in lista_contactos:
        uid = contacto.get(id_field)
        ultimo = mensajes_repository.get_ultimo_mensaje(id_usuario, uid)
        no_leidos = mensajes_repository.contar_no_leidos(id_usuario, uid)
        resultado.append({
            **contacto,
            "ultimoMensaje": ultimo["mensaje"][:60] if ultimo else None,
            "ultimaFecha": str(ultimo["fecha"]) if ultimo else None,
            "ultimoIdMensaje": ultimo["idMensaje"] if ultimo else 0,
            "ultimoEmisor": ultimo["idEmisor"] if ultimo else None,
            "noLeidos": no_leidos,
            "isOnline": uid in online_ids,
        })
    # Ordena: primero los no leídos, luego por fecha del último mensaje descendente
    return sorted(
        resultado,
        key=lambda c: (
            1 if c.get("noLeidos", 0) else 0,
            c.get("ultimaFecha") or "",
            c.get("ultimoIdMensaje") or 0,
        ),
        reverse=True,
    )


def get_mensajes(id_usuario, id_otro, desde_id=0):
    # Marca mensajes como leídos y obtiene la conversación
    mensajes_repository.marcar_leidos(id_usuario, id_otro)
    rows = mensajes_repository.get_conversacion(id_usuario, id_otro, desde_id)
    return [
        {**row, "esMio": row["idEmisor"] == id_usuario, "fecha": str(row["fecha"])}
        for row in rows
    ]


def enviar_mensaje(id_emisor, id_receptor, mensaje):
    return mensajes_repository.enviar_mensaje(id_emisor, id_receptor, mensaje)


def eliminar_historial_chatbot(patient_id):
    from app.repositories import chat_repository
    chat_repository.delete_history(patient_id)
