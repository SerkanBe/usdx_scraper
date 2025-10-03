class EventManager:
    def __init__(self):
        self._listeners = {}

    def register(self, event_name, callback):
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)

    def trigger(self, event_name, *args, **kwargs):
        for callback in self._listeners.get(event_name, []):
            callback(*args, **kwargs)

# Create a global event manager
event_manager = EventManager()