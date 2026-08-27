from abc import ABC, abstractmethod
import aiohttp

from app.bot.config import util_config
from app.interfaces.api_request_interface import IAPIRequest, IResource, IRetValue
from app.misc.prototype_registry import IPrototype


class BaseAPIRequest(IAPIRequest, IPrototype, ABC):
    """
    Abstract base class for making API requests, adhering to the IAPIRequest interface.
    This class provides common functionalities for API requests while allowing
    specific implementations in child classes.
    """

    def __init__(self, url: str, api_key: str, api_service: str = 'Default Service'):
        self._URL = url
        self._API_KEY = api_key
        self.api_service_name = api_service

    async def __call__(self, *args, **kwargs) -> IRetValue:
        resource = await self.prepare_resource(*args, **kwargs)
        return await self.request(resource)

    @abstractmethod
    async def prepare_resource(self, *args, **kwargs) -> IResource:
        """
        Prepare the resource for the request. This method should be implemented
        by child classes to handle specific resource preparations.
        """
        pass

    async def request(self, resource: IResource) -> IRetValue:
        """
        Asynchronous function that makes a request to a given resource.
        This method provides a common request handling mechanism while allowing
        child classes to implement specific request and response processing.
        """

        #if util_config['debug_mode'] == True:
            #print("Requesting:",resource)
            #resource.print()

        headers = self._prepare_headers()
        async with aiohttp.ClientSession() as session:
            response = await session.post(self._URL, json=self._prepare_payload(resource),
                                          headers=headers)
            return await self._process_response(response, resource)

    def _prepare_headers(self) -> dict:
        """
        Prepare the common headers for the API request.
        """
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self._API_KEY}"
        }

    @abstractmethod
    def _prepare_payload(self, resource: IResource) -> dict:
        """
        Prepare the payload for the request. This method should be implemented
        by child classes to handle specific payload preparations.
        """
        pass

    @abstractmethod
    async def _process_response(self, response, resource :IResource) -> IRetValue:
        """
        Process the response from the API request. This method should be implemented
        by child classes to handle specific response processing.
        """
        pass

    def clone(self):
        return self.copy(self)

    def copy(self, source: 'BaseAPIRequest'):
        return self.__class__(
            url=source._URL,
            api_key=source._API_KEY
        )

