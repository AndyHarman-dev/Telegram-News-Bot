import asyncio
import logging
from typing import Callable, Any

from app.interfaces.ret_val import IRetValue
from app.misc.base_circuit_breaker import BaseCircuitBreaker
from app.llm.exceptions import InvalidResource
from app.interfaces.resource import IResourceHolder, IResource
from app.llm.chat_completion_value import ChatCompletionValue
from app.misc.log_helper import LogHelper
from app.interfaces.ai_service_interfaces import ILLMChatCompletion
from app.llm.resources import LLMRequestResource

LOG_REQUESTER = LogHelper(__name__, "AIFallbackRequester")


class AIFallbackRequester(BaseCircuitBreaker, IResourceHolder, ILLMChatCompletion):
    """
        A class designed to handle requests with a fallback mechanism, integrating circuit breaker pattern for
        resilience and resource management for executing requests.

        This class inherits from `BaseCircuitBreaker` to utilize the circuit breaker pattern, which helps in
        preventing a cascade of failures when a part of the system is struggling. It also implements `IResourceHolder`
        interface to manage resources necessary for request execution.

        Attributes:
            _request_resource (IResource): A private attribute that holds the resource instance required for
            executing the requests. Initially set to None and expected to be set externally before request execution.

        The class is designed to be used in scenarios where requests need to be executed with resilience and
        resource management, providing a structured way to handle potential failures and ensuring that resources
        are properly managed and utilized.
        """

    def __init__(self, functions: list[Callable[[Any], IRetValue]]):
        """Initializes the AIFallbackRequester instance
            with a list of functions that define the operations to be executed as part of the request processing.
            These functions are passed to the superclass initializer."""
        self._request_resource = None
        super().__init__(functions)

    async def set_resource(self, res: IResource):
        """set_resource(res: IResource): An asynchronous method to set the resource required for request execution.
            This method updates the `_request_resource` attribute with the provided `res` resource instance."""
        self._request_resource = res

    async def get_resource(self) -> LLMRequestResource:
        """get_resource() -> IResource: An asynchronous method that returns the current resource instance set for
            request execution. This allows for retrieval of the resource instance at any point after it has been set."""
        return self._request_resource

    async def execute(self, *args, **kwargs) -> ChatCompletionValue:
        """execute(*args, **kwargs) -> ChatCompletionValue: An asynchronous method that executes the request using
            the set resource. It first checks if the resource is valid and logs an error and exits with a fallback
            if not. If the resource is valid, it proceeds with the execution by calling the superclass's execute method,
            passing the resource as an argument."""
        if not self._request_resource or not await self._request_resource.is_valid():
            LOG_REQUESTER.raise_exception_with_log(InvalidResource("You provided an invalid resource! Please, make "
                                                                   "sure the resource is set"
                                                                   "with set_resource method before executing"))

        return await super().execute(self._request_resource, *args, **kwargs)  # Pass on the set resource

    async def prompt(self, p: str) -> str:
        return str(await self.execute(p))


async def main():
    pass
#
#
# asyncio.run(main())
