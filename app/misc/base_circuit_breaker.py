import asyncio
import inspect
import logging
from typing import Callable, Any
from functools import partial

import telegram

from app.interfaces.circuit_breaker import ICircuitBreaker
from app.interfaces.ret_val import IRetValue
from app.misc.exceptions import FallbackException
from app.misc.log_helper import LogHelper

BASE_CIRCUIT_BREAKER = LogHelper(__name__, "Base Circuit Breaker")


class BaseCircuitBreaker(ICircuitBreaker):

    def __init__(self, functions: list[Callable[[Any], IRetValue]]):
        self._functions_stack = functions
        self._current_index = 0

    async def execute(self, *args, **kwargs) -> IRetValue:
        """
        Executes the next function in stack returning the
        interface value and passing the arbitrary parameters to it
        """
        self._current_index = 0  # Reset index each execution

        timeout_checker = False
        while True:
            try:
                if self._current_index >= len(self._functions_stack):
                    BASE_CIRCUIT_BREAKER.log(logging.WARNING, f'Out of the bounds of callables objects!'
                                                              f' Fallback process starting')
                    await self._fallback()

                func = self._functions_stack[self._current_index]

                if not func:
                    #raise Exception()  # Continue if callable is None
                    BASE_CIRCUIT_BREAKER.raise_exception_with_log(Exception('Callable object is None'))

                if inspect.iscoroutinefunction(func.__call__) or inspect.iscoroutinefunction(func):
                    BASE_CIRCUIT_BREAKER.log(logging.INFO, f'Trying to use the coroutine {func}')
                    return await func(*args, **kwargs)
                else:
                    partial_func = partial(func, *args, **kwargs)  # Wrap the function into a partial to keep the kwargs
                    loop = asyncio.get_running_loop()
                    BASE_CIRCUIT_BREAKER.log(logging.INFO, f'Trying to use the not coroutine {partial_func}')
                    return await loop.run_in_executor(None, partial_func)
            except FallbackException as fe:
                #raise fe  # Reraise fallback exception outward
                BASE_CIRCUIT_BREAKER.raise_exception_with_log(FallbackException(
                                                              f'Fallback Exception were given in '
                                                              f'{self._current_index}-th function execute. '
                                                              f'Description of exception: {fe}.')
                                                              )
            except (TimeoutError, asyncio.TimeoutError, telegram.error.TimedOut) as e:
                if timeout_checker:
                    BASE_CIRCUIT_BREAKER.log(logging.ERROR, f'There are repeating a timeout problem while using the model {func}')
                    self._current_index += 1
                    timeout_checker = False
                else:
                    BASE_CIRCUIT_BREAKER.log(logging.ERROR, f'There are a timeout problem while using the model {func}')
                    timeout_checker = True

            except Exception as e:  # Broad exception for catching unpredictable errors
                BASE_CIRCUIT_BREAKER.log(logging.ERROR, f'The {self._current_index} callable failed to execute because {e}. Trying the next one...')
                self._current_index += 1
                timeout_checker = False

    async def _fallback(self):
        raise FallbackException("fallback")


