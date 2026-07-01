# ============================================================
# ARCHIVO: services/chat_events.py
# ============================================================

import json
from queue import Queue
from threading import Lock

# Sistema de publicación/suscripción en memoria para eventos de mensajería en tiempo real
_subscribers = {}
_subscribers_lock = Lock()


def subscribe(user_id):
    # Crea una cola de eventos para un usuario específico (para SSE de mensajes)
    queue = Queue()
    user_id = int(user_id)
    with _subscribers_lock:
        _subscribers.setdefault(user_id, []).append(queue)
    return queue


def unsubscribe(user_id, queue):
    # Elimina la cola de un usuario cuando se desconecta
    user_id = int(user_id)
    with _subscribers_lock:
        queues = _subscribers.get(user_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues and user_id in _subscribers:
            del _subscribers[user_id]


def publish_message(id_mensaje, id_emisor, id_receptor):
    # Publica un evento de nuevo mensaje a los suscriptores (emisor y receptor)
    event = json.dumps({
        "idMensaje": id_mensaje,
        "idEmisor": id_emisor,
        "idReceptor": id_receptor,
    })
    recipients = {int(id_emisor), int(id_receptor)}

    with _subscribers_lock:
        # Recolecta todas las colas del emisor y receptor
        subscribers = [
            queue
            for user_id in recipients
            for queue in _subscribers.get(user_id, [])
        ]

    # Distribuye el evento a todas las colas suscritas
    for queue in subscribers:
        queue.put(event)
