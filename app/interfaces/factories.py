from abc import ABC, abstractmethod
from app.interfaces.ai_service_interfaces import ILLMChatCompletion, ILLMTranscriber, ILLMImageGenerator, \
    ILLMSpeechGenerator


class IAIServiceFactory(ABC):
    @abstractmethod
    async def create_chat_completion(self) -> ILLMChatCompletion:
        pass

    @abstractmethod
    async def create_image_generator(self) -> ILLMImageGenerator:
        pass

    @abstractmethod
    async def create_transcriber(self) -> ILLMTranscriber:
        pass

    @abstractmethod
    async def create_speech_generator(self) -> ILLMSpeechGenerator:
        pass
