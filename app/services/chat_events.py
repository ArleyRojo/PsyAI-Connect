import json
from queue import Queue
from threading import Lock


_subscribers = {}
_subscribers_lock = Lock()


def subscribe(user_id):
    queue = Queue()
    user_id = int(user_id)
    with _subscribers_lock:
        _subscribers.setdefault(user_id, []).append(queue)
    return queue


def unsubscribe(user_id, queue):
    user_id = int(user_id)
    with _subscribers_lock:
        queues = _subscribers.get(user_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues and user_id in _subscribers:
            del _subscribers[user_id]


def publish_message(id_mensaje, id_emisor, id_receptor):
    event = json.dumps({
        "idMensaje": id_mensaje,
        "idEmisor": id_emisor,
        "idReceptor": id_receptor,
    })
    recipients = {int(id_emisor), int(id_receptor)}

    with _subscribers_lock:
        subscribers = [
            queue
            for user_id in recipients
            for queue in _subscribers.get(user_id, [])
        ]

    for queue in subscribers:
        queue.put(event)
