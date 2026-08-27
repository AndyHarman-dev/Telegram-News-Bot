from abc import ABC, abstractmethod
from app.interfaces.resource import IResource
from app.interfaces.ret_val import IRetValue

from typing import Callable


class IAPIRequest(ABC):
    """
    A base interface for any LLM chat completion service
    """

    @abstractmethod
    async def __call__(self, *args, **kwargs) -> IRetValue:
        pass

    @abstractmethod
    async def request(self, resource: IResource) -> IRetValue:
        pass
