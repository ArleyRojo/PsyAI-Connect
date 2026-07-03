from app.repositories.mensajes_repository import MensajesRepository
from app.repositories.chat_repository import ChatRepository


class MensajesService:
    def __init__(self):
        self.repo = MensajesRepository()
        self.chat_repo = ChatRepository()

    def get_contactos_con_mensajes(self, id_usuario, lista_contactos, id_field="idUsuario"):
        from app.services.telemetry_service import get_active_user_ids
        online_ids = set(get_active_user_ids())
        resultado = []
        for contacto in lista_contactos:
            uid = contacto.get(id_field)
            ultimo = self.repo.get_ultimo_mensaje(id_usuario, uid)
            no_leidos = self.repo.contar_no_leidos(id_usuario, uid)
            resultado.append({
                **contacto,
                "ultimoMensaje": ultimo["mensaje"][:60] if ultimo else None,
                "ultimaFecha": str(ultimo["fecha"]) if ultimo else None,
                "ultimoIdMensaje": ultimo["idMensaje"] if ultimo else 0,
                "ultimoEmisor": ultimo["idEmisor"] if ultimo else None,
                "noLeidos": no_leidos,
                "isOnline": uid in online_ids,
            })
        return sorted(
            resultado,
            key=lambda c: (
                1 if c.get("noLeidos", 0) else 0,
                c.get("ultimaFecha") or "",
                c.get("ultimoIdMensaje") or 0,
            ),
            reverse=True,
        )

    def get_mensajes(self, id_usuario, id_otro, desde_id=0):
        self.repo.marcar_leidos(id_usuario, id_otro)
        rows = self.repo.get_conversacion(id_usuario, id_otro, desde_id)
        return [
            {**row, "esMio": row["idEmisor"] == id_usuario, "fecha": str(row["fecha"])}
            for row in rows
        ]

    def enviar_mensaje(self, id_emisor, id_receptor, mensaje):
        return self.repo.enviar_mensaje(id_emisor, id_receptor, mensaje)

    def eliminar_historial_chatbot(self, patient_id):
        self.chat_repo.delete_history(patient_id)



