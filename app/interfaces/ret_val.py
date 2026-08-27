from abc import ABC, abstractmethod


class IRetValue(ABC):
    @abstractmethod
    async def is_valid(self) -> bool:
        pass

    @abstractmethod
    def __await__(self):
        pass
