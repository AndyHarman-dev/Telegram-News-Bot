import asyncio


class AsyncObj:
    def __init__(self, *args, **kwargs) -> None:
        self.__storedargs: tuple[tuple, dict] = (args, kwargs)
        self.async_initialized: bool = False

    async def __ainit__(self, *args, **kwargs) -> None:
        """ Async constructor: should be implemented in each subclass"""
        raise NotImplementedError("Subclasses must implement __ainit__")

    async def __initobj(self) -> 'AsyncObj':
        if self.async_initialized:
            return self
        try:
            await self.__ainit__(*self.__storedargs[0], **self.__storedargs[1])
            self.async_initialized = True
            del self.__storedargs  # Clean up stored args after successful initialization
        except Exception as e:
            self.async_initialized = False
            raise RuntimeError(f"Async initialization failed: {e}") from e
        return self

    def __await__(self):
        return self.__initobj().__await__()

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if not asyncio.iscoroutinefunction(cls.__ainit__):
            raise TypeError(f"{cls.__name__}.__ainit__ must be a coroutine function")

    @property
    def async_state(self) -> str:
        return "[initialization pending]" if not self.async_initialized else "[initialization done and successful]"
