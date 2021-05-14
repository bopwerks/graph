class Listener(object):
    def __init__(self):
        self._listeners = set()
    
    def _publish(self):
        for fn in self._listeners:
            fn(self)

    def addListener(self, fn):
        self._listeners.add(fn)

    def removeListener(self, fn):
        self._listeners.remove(fn)