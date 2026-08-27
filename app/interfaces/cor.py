from abc import ABC, abstractmethod

class IHandler(ABC):
    @abstractmethod
    async def handle(self, *args, **kwargs):
        pass

    @abstractmethod
    def set_next(self, h: "IHandler"):
        pass


class BaseHandler(IHandler):

    def __init__(self):
        self._next = None

    def set_next(self, h: "IHandler"):
        self._next = h

    async def handle(self, *args, **kwargs):
        if self._next:
            return await self._next.handle(*args, **kwargs)
