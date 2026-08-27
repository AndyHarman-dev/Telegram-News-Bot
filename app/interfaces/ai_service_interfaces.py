from abc import ABC, abstractmethod


class ILLMChatCompletion(ABC):

    @abstractmethod
    async def prompt(self, p: str) -> str:
        pass


class ILLMImageGenerator(ABC):

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass


class ILLMTranscriber(ABC):

    @abstractmethod
    async def transcribe(self, file_path: str) -> str:
        pass


class ILLMSpeechGenerator(ABC):

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass
