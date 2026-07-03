import json
from queue import Queue
from threading import Lock


class ChatbotConfigEventsService:
    def __init__(self):
        self._subscribers = []
        self._subscribers_lock = Lock()

    def subscribe(self):
        queue = Queue()
        with self._subscribers_lock:
            self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue):
        with self._subscribers_lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    def publish_config_update(self, config):
        event = json.dumps(config or {})
        with self._subscribers_lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            queue.put(event)


chatbot_config_events = ChatbotConfigEventsService()
subscribe = chatbot_config_events.subscribe
unsubscribe = chatbot_config_events.unsubscribe
publish_config_update = chatbot_config_events.publish_config_update
