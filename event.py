class Emitter(object):
    def __init__(self):
        self._listeners = {}
    
    def emit(self, event_name, *args):
        for fn in self._listeners.get(event_name, set()):
            #print("{0} {1} {2} {3}".format(self, event_name, fn, args))
            fn(*args)

    def add_listener(self, event_name, fn):
        if event_name not in self._listeners:
            self._listeners[event_name] = set()
        self._listeners[event_name].add(fn)

    def remove_listener(self, event_name, fn):
        listeners = self._listeners.get(event_name, set())
        listeners.remove(fn)
        if not listeners:
            del self._listeners[event_name]