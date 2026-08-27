from abc import ABC, abstractmethod
from typing import Callable


class IResource(ABC):
    @abstractmethod
    async def is_valid(self) -> bool:
        pass

    def print(self):
        """
        Prints all the attributes and their values of this resource instance to the console.
        """
        print("Resource Contents:")
        for attr in dir(self):
            # Filter out private, magic attributes, and methods
            if not attr.startswith("_") and not callable(getattr(self, attr)):
                value = getattr(self, attr)
                print(f"{attr}: {value}")


class IResourceHolder(ABC):
    @abstractmethod
    async def set_resource(self, res: IResource):
        pass

    @abstractmethod
    async def get_resource(self) -> IResource:
        pass

