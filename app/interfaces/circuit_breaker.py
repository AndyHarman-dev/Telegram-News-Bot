from abc import ABC, abstractmethod
from app.interfaces.ret_val import IRetValue


class ICircuitBreaker(ABC):
    @abstractmethod
    async def execute(self, *args, **kwargs) -> IRetValue:
        pass

    @abstractmethod
    async def _fallback(self):
        pass

