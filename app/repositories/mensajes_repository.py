from sqlalchemy import select, or_, and_
from app.database.session import db_session
from app.models.mensajes_chat import MensajesChat


class MensajesRepository:
    def enviar_mensaje(self, id_emisor, id_receptor, mensaje):
        with db_session() as session:
            msg = MensajesChat(idEmisor=id_emisor, idReceptor=id_receptor, mensaje=mensaje)
            session.add(msg)
            return msg.idMensaje

    def get_conversacion(self, id_usuario, id_otro, desde_id=0, limit=60):
        with db_session() as session:
            if desde_id <= 0:
                stmt = select(MensajesChat).where(
                    or_(
                        and_(MensajesChat.idEmisor == id_usuario, MensajesChat.idReceptor == id_otro),
                        and_(MensajesChat.idEmisor == id_otro, MensajesChat.idReceptor == id_usuario),
                    )
                ).order_by(MensajesChat.fecha.desc(), MensajesChat.idMensaje.desc()).limit(limit)
                rows = list(reversed(session.execute(stmt).scalars().all()))
            else:
                stmt = select(MensajesChat).where(
                    MensajesChat.idMensaje > desde_id,
                    or_(
                        and_(MensajesChat.idEmisor == id_usuario, MensajesChat.idReceptor == id_otro),
                        and_(MensajesChat.idEmisor == id_otro, MensajesChat.idReceptor == id_usuario),
                    )
                ).order_by(MensajesChat.fecha.asc(), MensajesChat.idMensaje.asc()).limit(limit)
                rows = session.execute(stmt).scalars().all()
            return [m.to_dict() for m in rows]

    def marcar_leidos(self, id_receptor, id_emisor):
        with db_session() as session:
            stmt = select(MensajesChat).where(
                MensajesChat.idReceptor == id_receptor,
                MensajesChat.idEmisor == id_emisor,
                MensajesChat.leido == False,
            )
            mensajes = session.execute(stmt).scalars().all()
            for m in mensajes:
                m.leido = True

    def contar_no_leidos(self, id_receptor, id_emisor):
        with db_session() as session:
            from sqlalchemy import func
            return session.execute(
                select(func.count()).select_from(MensajesChat).where(
                    MensajesChat.idReceptor == id_receptor,
                    MensajesChat.idEmisor == id_emisor,
                    MensajesChat.leido == False,
                )
            ).scalar() or 0

    def get_ultimo_mensaje(self, id_usuario, id_otro):
        with db_session() as session:
            stmt = select(MensajesChat).where(
                or_(
                    and_(MensajesChat.idEmisor == id_usuario, MensajesChat.idReceptor == id_otro),
                    and_(MensajesChat.idEmisor == id_otro, MensajesChat.idReceptor == id_usuario),
                )
            ).order_by(MensajesChat.fecha.desc()).limit(1)
            msg = session.execute(stmt).scalar_one_or_none()
            if msg:
                return {"idMensaje": msg.idMensaje, "idEmisor": msg.idEmisor, "mensaje": msg.mensaje, "fecha": msg.fecha}
            return None
