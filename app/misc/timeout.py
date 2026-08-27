import asyncio
import threading
from app.misc.log_helper import LogHelper

TIMEOUT_LOG = LogHelper(__name__, "Timeout Thread")


class Timeout:
    """
    A utility class for executing functions with a timeout.

    The Timeout class wraps a function call and ensures that it completes
    within a specified timeout period. If the function does not complete in
    time, a specified callback is called. This class supports both synchronous
    and asynchronous functions.
    """

    def __init__(self, func, timeout, callback):
        """
         Initialize a new instance of the Timeout class.
        Args:
            func (callable): The function to be executed.
            timeout (float): The maximum amount of time in seconds to wait for the function to complete.
            callback (callable): The function to be called if the timeout is reached.

        """
        self.func = func
        self.timeout = timeout
        self.callback = callback
        self.is_async = asyncio.iscoroutinefunction(func)  # Determine whether the function is an async function

    def __call__(self, *args, **kwargs):
        if self.is_async:
            return self._call_async(*args, **kwargs)
        else:
            return self._call_sync(*args, **kwargs)

    def _call_sync(self, *args, **kwargs):
        result = None
        exception = None

        def wrapper():  # Wrap the function with a timeout
            nonlocal result, exception
            try:
                result = self.func(*args, **kwargs)
            except Exception as e:
                exception = e

        thread = threading.Thread(target=wrapper)
        thread.start()
        thread.join(timeout=self.timeout)

        if thread.is_alive():
            self._execute_callback()
            TIMEOUT_LOG.raise_exception_with_log(
                TimeoutError(f"Function '{self.func.__name__}' timed out after {self.timeout} seconds"))

        if exception:  # Reraise any uncaught exception
            TIMEOUT_LOG.raise_exception_with_log(exception)

        return result

    async def _call_async(self, *args, **kwargs):
        try:
            return await asyncio.wait_for(self.func(*args, **kwargs), timeout=self.timeout)
        except asyncio.TimeoutError:
            self._execute_callback()
            TIMEOUT_LOG.raise_exception_with_log(
                TimeoutError(f"Async function '{self.func.__name__}' timed out after {self.timeout} seconds"))

    def _execute_callback(self):
        if self.callback:
            self.callback()


def with_timeout(func, timeout, callback, args=()):
    """
    Executes the given function with a specified timeout.

    Args:
        func (callable): The function to be executed.
        timeout (float): The maximum amount of time in seconds to wait for the function to complete.
        callback (callable): The function to be called if the timeout is reached.
        args (tuple, optional): The arguments to be passed to the function. Defaults to ().

    Returns:
        Any: The result of the function, or None if the timeout is reached.
    """
    return Timeout(func=func, timeout=timeout, callback=callback)(*args)  # Wrap the functions to the decorator and execute


# async def test1(argument1, argument2):
#     print("Start async func with", argument1, argument2)
#     await asyncio.sleep(10)
#
#
# def test2():
#     time.sleep(4)


if __name__ == "__main__":
    pass
    # try:
    #     asyncio.run(with_timeout(func=test1, timeout=5, callback=lambda: print("Timeout!"), args=(5, 100)))
    # except TimeoutError as e:
    #     print(e)
    # finally:
    #     print("Finally print!")
