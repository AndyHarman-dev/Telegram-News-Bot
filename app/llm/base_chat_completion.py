import asyncio
import inspect
import json
import logging
from functools import partial
from typing import Callable, Optional

import aiohttp
import nltk

from app.interfaces.api_request_interface import IAPIRequest, IResource, IRetValue
from app.llm.resources import LLMRequestResource
from app.api.base_api_request import BaseAPIRequest
from app.llm.chat_completion_value import ChatCompletionValue
from app.misc.log_helper import LogHelper
from app.llm.exceptions import InvalidResource, UnsupportedResource, InvalidModel, Forbidden
from app.interfaces.prototype import IPrototype
from app.bot.config import llm_services_config
from app.bot.config import llm_services_config

LOG_CHAT_COMPLETION = LogHelper(__name__, "LLMChatCompletion")

nltk.download('punkt')


def count_tokens(text: str):
    tokens = nltk.word_tokenize(text)
    return len(tokens)


class BaseChatCompletionRequest(BaseAPIRequest):
    """Default base class for chat completions that adds two common variables and
    overrides __call__ method to be a callable object

    the variables are:
    model_name: the name of the model
    _URL: the url of the service
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stream_delta_callback = None  # For calling each delta out
        self._stream_callback = None  # For calling the whole message
        self.current_model_index = 0  # For iterating over models if some of them produce exceptions when requesting

    async def prepare_resource(self, *args, **kwargs) -> IResource:

        parameter = args[0].clone()  # We don't want a reference to the original parameter

        if not isinstance(parameter, LLMRequestResource):
            LOG_CHAT_COMPLETION.raise_exception_with_log(UnsupportedResource(f"{self.__class__.__name__} service does "
                                                                             f"not support"
                                                                             f"a resource of type {type(parameter)},"
                                                                             f" consider using"
                                                                             f"{type(LLMRequestResource)} instead"))

            # Check token count of user messages
            for message in parameter.messages:
                if message['role'] == 'user':
                    token_count = count_tokens(message['content'])
                    if token_count > llm_services_config['max_tokens']:
                        LOG_CHAT_COMPLETION.raise_exception_with_log(
                            ValueError(f"User message exceeds the maximum allowed tokens. "
                                       f"Message length: {token_count} tokens, "
                                       f"Maximum allowed: {llm_services_config['max_tokens']} tokens"))

        await self.add_override_parameters(parameter, *args[1:], **kwargs)  # If there were any override parameters

        LOG_CHAT_COMPLETION(logging.INFO, f"Prepared resource: {parameter}", verbose=True)

        return parameter

    @staticmethod
    async def add_override_parameters(r: IResource, *args, **kwargs):
        """
        A function to add override parameters to the given IResource object.
        The function takes in the IResource object r, along with optional positional
        and keyword arguments. The function is asynchronous and does not return anything.
        """
        if isinstance(r, LLMRequestResource):
            # Case 1: args contains only string
            if 0 in range(len(args)) and isinstance(args[0], str):
                token_count = count_tokens(args[0])
                if token_count > llm_services_config['max_tokens'] and \
                        (not hasattr(r, 'from_parser') or not r.from_parser) and \
                        (not hasattr(r, 'from_news_manager') or not r.from_news_manager):
                    LOG_CHAT_COMPLETION.raise_exception_with_log(
                        ValueError(f"User message exceeds the maximum allowed tokens. "
                                   f"Message length: {token_count} tokens, "
                                   f"Maximum allowed: {llm_services_config['max_tokens']} tokens"))

                all_content = args[0]
                if hasattr(r, 'from_news_manager') and r.from_news_manager and \
                        token_count > llm_services_config['max_tokens']:
                    all_content = BaseChatCompletionRequest.smart_text_news_truncating(all_content,
                                                                                       llm_services_config['max_tokens']
                                                                                       )

                r.messages.append({"role": "user", "content": all_content})
                LOG_CHAT_COMPLETION(logging.INFO, f"Added user message: {all_content}", verbose=True)

            # Case 3: Check kwargs for matching parameters
            for key, value in kwargs.items():
                if hasattr(r, key):
                    setattr(r, key, value)

    @staticmethod
    def smart_text_news_truncating(text_news, max_tokens):
        import re
        LOG_CHAT_COMPLETION.log(logging.INFO, f'The message that begins with {text_news[:100]} has reached too large a length.')

        def truncate_text(text, max_length):
            # Breaking text into sentences
            sentences = re.split(r'(?<=[.!?])\s+', text)

            # If the text is shorter than max_length, return it unchanged
            if len(text) <= max_length:
                return text

            # If the first sentence is longer than max_length
            if len(sentences[0]) > max_length:
                words = sentences[0].split()
                truncated_sentence = ''
                for word in words:
                    if len(truncated_sentence + word) <= max_length:
                        truncated_sentence += word + ' '
                    else:
                        break
                return truncated_sentence.strip()

            # If the text is longer than max_length, but the first sentence is shorter
            truncated_text = ''
            for sentence in sentences:
                if len(truncated_text + sentence) <= max_length:
                    truncated_text += sentence + ' '
                else:
                    break

            return truncated_text.strip()

        return truncate_text(text_news, max_tokens)

    def _prepare_payload(self, resource: IResource) -> dict:
        if isinstance(resource, LLMRequestResource):
            return {
                        "model": resource.models[self.current_model_index],
                        "messages": [
                            {
                                'role': "system",
                                "content": resource.system
                            },
                            *resource.messages
                        ],
                        "temperature": resource.temperature,
                        "max_tokens": resource.max_tokens,
                        "top_p": resource.top_p,
                        "stream": resource.stream
                    }

        LOG_CHAT_COMPLETION.raise_exception_with_log(InvalidResource(f"{self.__class__.__name__} service does not support"
                                                                     f"a resource of type {type(resource)}"))

    async def _process_response(self, response, resource: IResource) -> IRetValue:

        if not isinstance(resource, LLMRequestResource):
            LOG_CHAT_COMPLETION.raise_exception_with_log(InvalidResource(
                f"{self.__class__.__name__} service does not support"
                f"a resource of type {type(resource)}"))

        LOG_CHAT_COMPLETION(logging.INFO,
                            f"Processing response with {resource.models[self.current_model_index]} model and "
                            f"with {self.api_service_name} service.", verbose=True)
        LOG_CHAT_COMPLETION(logging.INFO, f"Response: {response}", verbose=True)

        if not response:
            LOG_CHAT_COMPLETION.raise_exception_with_log(ValueError(f"Response is empty!"))

        # Get out with incorrect status code
        if response.reason.lower() == "forbidden":
            LOG_CHAT_COMPLETION.raise_exception_with_log(
                Forbidden(f"This url is forbidden in this country."))

        if response.status != 200:
            # if code was failed, recursively make the next request with a new model
            LOG_CHAT_COMPLETION.log(logging.WARNING,
                                    f"Response code is not 200! Error {response.status} Error message {response.reason}",
                                    verbose=True)
            self.current_model_index += 1

            if self.current_model_index >= len(resource.models):
                self.current_model_index = 0
                LOG_CHAT_COMPLETION.raise_exception_with_log(
                    ValueError('The maximum number of models has been used. '
                               'An attempt to use another API service will be made. '
                               'If all services have been tried, the request will be interrupted! '
                               f'({self.api_service_name} service message)'))

            LOG_CHAT_COMPLETION(logging.INFO,
                                f"Requesting new model: {resource.models[self.current_model_index]}. "
                                f"({self.api_service_name} service message)", verbose=True)

            return await self.request(resource)

        if resource.stream:

            LOG_CHAT_COMPLETION(logging.INFO, "Streaming response... ", verbose=True)

            # Bind stream callback if present to dispatch each delta
            if resource.stream_delta_callback:
                await self.bind_to_stream_delta_callback(resource.stream_delta_callback)
            if resource.stream_callback:
                await self.bind_to_stream_callback(resource.stream_callback)

            chat_answer = await self._handle_stream_response(response)  # This will receive all the
            # chunks and append them to return the chat answer.
        else:

            LOG_CHAT_COMPLETION(logging.INFO, "Non-streaming response... ", verbose=True)
            LOG_CHAT_COMPLETION(logging.INFO, "Unpacking response content... ", verbose=True)
            response_json = await response.json()  # If it's a regular response, then we can just jsonify it
            chat_answer = response_json['choices'][0]['message']['content']

        LOG_CHAT_COMPLETION(logging.INFO, f"Response content : {chat_answer}", verbose=True)
        LOG_CHAT_COMPLETION(logging.INFO, f"Response with {resource.models[self.current_model_index]} model "
                                          f"and with {self.api_service_name} service complete.", verbose=True)

        self.current_model_index = 0  # Nullify the current model index in order to make new requests later

        return ChatCompletionValue(
            chat_answer
        )

    async def request(self, resource: IResource) -> IRetValue:
        """
                   Asynchronous function that makes a request to a given resource.
                   Takes a resource of type IResource and returns a value of type IRetValue.
                   Raises exceptions for unsupported resource types and long request content.
                   Utilizes aiohttp.ClientSession for the HTTP request.
                   """

        if not isinstance(resource, LLMRequestResource):
            LOG_CHAT_COMPLETION.raise_exception_with_log(UnsupportedResource(f"{self.__class__.__name__} service does "
                                                                             f"not support"
                                                                             f"a resource of type {type(resource)}"))

        # If current model is out of the bounds of resource models, raise an exception and stop requesting
        if self.current_model_index >= len(resource.models):
            self.current_model_index = 0
            LOG_CHAT_COMPLETION.raise_exception_with_log(
                InvalidModel("Run out of available models for a request"
                             "make sure that the models you provided "
                             "in the request are all supported!"))  # Raise exception when run out of models

        return await super().request(resource)  # Make the super call for sending the request

    async def _handle_stream_response(self, response):
        """
        Asynchronous function to handle stream responses.
        Takes the response object and returns the complete chat answer.
        It also calls the stream delta callback function for each chunk
        """
        chat_answer = ""

        LOG_CHAT_COMPLETION(logging.INFO, f"Handling streaming response by chunks...", verbose=True)

        async for chunk in response.content:

            chunk_str = chunk.decode('utf-8', 'surrogatepass')

            LOG_CHAT_COMPLETION(logging.INFO, f"Decoding chunk: {chunk_str}", verbose=True)

            if chunk_str.startswith('data:'):
                data_part = chunk_str[6:]  # Remove the 'data: ' prefix
                LOG_CHAT_COMPLETION(logging.INFO, f"'data' prefix removed, raw data: {data_part}", verbose=True)
                if data_part:
                    try:
                        data_json = json.loads(data_part)
                        delta_content = data_json['choices'][0]['delta'].get('content', '')
                        LOG_CHAT_COMPLETION(logging.INFO, f"'Extracted delta content: {delta_content}", verbose=True)
                        chat_answer += delta_content

                        callbacks = [(self._stream_callback, chat_answer), (self._stream_delta_callback, delta_content)]

                        for callback, answer in callbacks:  # Iterate over both callbacks and dispatch the data
                            if callback:
                                if inspect.iscoroutinefunction(callback.__call__) or \
                                        inspect.iscoroutinefunction(callback):
                                    # Check if the callback is a function or a callable wrapper
                                    await callback(answer)
                                else:
                                    partial_func = partial(callback, ChatCompletionValue(delta_content))
                                    loop = asyncio.get_running_loop()
                                    await loop.run_in_executor(None, partial_func)

                    except json.JSONDecodeError as e:
                        LOG_CHAT_COMPLETION(logging.WARNING, f"Could not decode json while streaming a response. Reason: {e}. Keep on...", verbose=True)
                        pass

        LOG_CHAT_COMPLETION(logging.WARNING,
                            f"Chat answer is formed. Answer: {chat_answer}", verbose=True)
        return chat_answer

    async def bind_to_stream_delta_callback(self, stream_delta_callback: Callable[[IRetValue], None]) -> None:
        self._stream_delta_callback = stream_delta_callback

    async def bind_to_stream_callback(self, stream_callback: Callable[[IRetValue], None]) -> None:
        self._stream_callback = stream_callback

    def copy(self, source: 'BaseAPIRequest'):
        copy = super().copy(source)
        if isinstance(copy, self.__class__):
            copy._stream_delta_callback = self._stream_delta_callback  # For calling each delta out
            copy._stream_callback  = self._stream_callback # For calling the whole message
            copy.current_model_index  = int(self.current_model_index)  # For iterating over models if some of them
            # produce exceptions when requesting

            return copy
