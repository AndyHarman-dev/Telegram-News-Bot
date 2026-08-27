import inspect
from abc import abstractmethod, ABC


class IEventHandler(ABC):

    @abstractmethod
    def register(self, handler):
        pass

    @abstractmethod
    def unregister(self, handler):
        pass

    @abstractmethod
    def is_registered(self, handler):
        pass


class EventHandler(IEventHandler):
    def __init__(self):
        self.handlers = []

    def register(self, handler):
        self.handlers.append(handler)

    def unregister(self, handler):
        self.handlers.remove(handler)

    def trigger(self, *args, **kwargs):
        for handler in self.handlers:
            handler(*args, **kwargs)

    def is_registered(self, handler):
        return handler in self.handlers


class AsyncEventHandler(EventHandler):

    async def trigger(self, *args, **kwargs):
        for handler in self.handlers:
            if inspect.iscoroutinefunction(handler.__call__) or inspect.iscoroutinefunction(handler):
                await handler(*args, **kwargs)
            else:
                handler(*args, **kwargs)
