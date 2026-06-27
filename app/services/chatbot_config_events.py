# ============================================================
# ARCHIVO: services/chatbot_config_events.py
# ============================================================

import json
from queue import Queue
from threading import Lock

# Sistema de publicación/suscripción para notificar cambios en la configuración del chatbot
_subscribers = []
_subscribers_lock = Lock()


def subscribe():
    # Crea una cola para recibir eventos de actualización de configuración
    queue = Queue()
    with _subscribers_lock:
        _subscribers.append(queue)
    return queue


def unsubscribe(queue):
    # Elimina una cola de la lista de suscriptores
    with _subscribers_lock:
        if queue in _subscribers:
            _subscribers.remove(queue)


def publish_config_update(config):
    # Publica un evento con la nueva configuración a todos los suscriptores (pacientes conectados)
    event = json.dumps(config or {})
    with _subscribers_lock:
        subscribers = list(_subscribers)

    for queue in subscribers:
        queue.put(event)
