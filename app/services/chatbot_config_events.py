import json
from queue import Queue
from threading import Lock


_subscribers = []
_subscribers_lock = Lock()


def subscribe():
    queue = Queue()
    with _subscribers_lock:
        _subscribers.append(queue)
    return queue


def unsubscribe(queue):
    with _subscribers_lock:
        if queue in _subscribers:
            _subscribers.remove(queue)


def publish_config_update(config):
    event = json.dumps(config or {})
    with _subscribers_lock:
        subscribers = list(_subscribers)

    for queue in subscribers:
        queue.put(event)
