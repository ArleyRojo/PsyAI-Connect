import json
from queue import Queue
from threading import Lock


class ChatEventsService:
    def __init__(self):
        self._subscribers = {}
        self._subscribers_lock = Lock()

    def subscribe(self, user_id):
        queue = Queue()
        user_id = int(user_id)
        with self._subscribers_lock:
            self._subscribers.setdefault(user_id, []).append(queue)
        return queue

    def unsubscribe(self, user_id, queue):
        user_id = int(user_id)
        with self._subscribers_lock:
            queues = self._subscribers.get(user_id, [])
            if queue in queues:
                queues.remove(queue)
            if not queues and user_id in self._subscribers:
                del self._subscribers[user_id]

    def publish_message(self, id_mensaje, id_emisor, id_receptor):
        event = json.dumps({
            "idMensaje": id_mensaje,
            "idEmisor": id_emisor,
            "idReceptor": id_receptor,
        })
        recipients = {int(id_emisor), int(id_receptor)}

        with self._subscribers_lock:
            subscribers = [
                queue
                for user_id in recipients
                for queue in self._subscribers.get(user_id, [])
            ]

        for queue in subscribers:
            queue.put(event)


chat_events = ChatEventsService()
subscribe = chat_events.subscribe
unsubscribe = chat_events.unsubscribe
publish_message = chat_events.publish_message
