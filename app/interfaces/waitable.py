from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Callable

T = TypeVar('T')


class IWaitable(ABC, Generic[T]):
    """
    An interface for objects that can be awaited using callbacks.
    """

    @abstractmethod
    def on_complete(self, callback: Callable[[T], None]) -> None:
        """
        Register a callback to be called when the operation completes.

        Args:
            callback (Callable[[T], None]): A function to be called with the result when the operation completes.
        """
        pass

    @abstractmethod
    def on_error(self, callback: Callable[[Exception], None]) -> None:
        """
        Register a callback to be called if an error occurs during the operation.

        Args:
            callback (Callable[[Exception], None]): A function to be called with the exception if an error occurs.
        """
        pass

    @abstractmethod
    def cancel(self) -> None:
        """
        Cancel the operation if it hasn't completed yet.
        """
        pass
