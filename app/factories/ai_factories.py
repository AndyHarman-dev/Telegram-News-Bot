from abc import ABC, abstractmethod

from app.interfaces.ai_service_interfaces import ILLMChatCompletion, ILLMImageGenerator, ILLMTranscriber, \
    ILLMSpeechGenerator
from app.interfaces.factories import IAIServiceFactory
from app.bot.config import LLMModels, ImageModels
from app.llm.resources import LLMRequestResource
from app.misc.prototype_registry import PrototypeRegistry
from app.misc.log_helper import LogHelper
from app.llm.fallback_requester import AIFallbackRequester
from app.init import init_default_classes
from app.llm.image_generator.image_generator_facade import ImageGeneratorFacade
from app.llm.resources import IMGRequestResource
from app.llm.image_generator.image_generation_requests import ImgPaths

AI_FACTORY_LOG = LogHelper(__name__, "AI Factory")


class AIBaseServiceFactory(IAIServiceFactory, ABC):
    """Base service factory that defines a base interface
    of creating AI services for the client-code"""

    async def create_chat_completion(self) -> ILLMChatCompletion:
        fr = AIFallbackRequester(
            functions=PrototypeRegistry.get_category_as_list("chat_completions"),
        )

        r = LLMRequestResource(
            system="Be precise and concise.",
            messages=[],
            models=await self.get_models(),
            max_tokens=500,
            temperature=0.7,
            top_p=1
        )

        await fr.set_resource(r)  # Set the resource in the fallback requester
        return fr

    async def create_image_generator(self) -> ILLMImageGenerator:

        f = ImageGeneratorFacade()
        r = IMGRequestResource(
            prompt="",
            models=await self.get_image_models(),
            n=1,
            size="1024x1024"
        )

        await f.set_resource(r)
        return f

    async def create_transcriber(self) -> ILLMTranscriber:
        pass  # TODO

    async def create_speech_generator(self) -> ILLMSpeechGenerator:
        pass  # TODO

    @staticmethod
    @abstractmethod
    async def get_models() -> list[str]:
        pass

    @staticmethod
    async def get_image_models() -> list[str]:
        return [
            ImageModels.DALL_E_3
        ]


class AIFastServiceFactory(AIBaseServiceFactory):

    @staticmethod
    async def get_models() -> list[str]:
        return [
            LLMModels.GPT_3_5_TURBO,
            LLMModels.LLAMA_3_SONAR_SMALL_CHAT,
            LLMModels.MISTRAL_7B_INSTR
        ]


class AIBalanceServiceFactory(AIBaseServiceFactory):

    @staticmethod
    async def get_models() -> list[str]:
        return [
            LLMModels.GPT_4,
            LLMModels.LLAMA_3_SONAR_LARGE_CHAT,
            LLMModels.MISTRAL_8x7B_INSTR
        ]


class AIFreeServiceFactory(AIBaseServiceFactory):

    @staticmethod
    async def get_models() -> list[str]:
        return [
            LLMModels.LLAMA_3_SONAR_SMALL_CHAT,
            LLMModels.MISTRAL_8x7B_INSTR,
            LLMModels.LLAMA_3_SONAR_LARGE_CHAT,
            LLMModels.MISTRAL_7B_INSTR
        ]


class AIQualityServiceFactory(AIBaseServiceFactory):

    @staticmethod
    async def get_models() -> list[str]:
        return [
            LLMModels.GPT_4_1106_PREVIEW,
            LLMModels.LLAMA_3_SONAR_HUGE_CHAT
        ]


class AIAllServiceFactory(AIBaseServiceFactory):

    @staticmethod
    async def get_models() -> list[str]:
        return await AIBalanceServiceFactory.get_models() + await AIQualityServiceFactory.get_models() +\
            await AIFastServiceFactory.get_models()


class AIServiceFacade:

    @staticmethod
    async def create_chat_completion(factory_type: type[AIBaseServiceFactory] = AIFastServiceFactory,
                                     **kwargs) -> ILLMChatCompletion:
        """
        A static method to create a chat completion instance.

        Args:
            factory_type: The type of service factory to use (default is AIFastServiceFactory).
            **kwargs: Additional keyword arguments.

        Returns:
            ILLMChatCompletion: The created chat completion instance.
        """
        f = factory_type()  # Create factory
        fr = await f.create_chat_completion()
        if isinstance(fr, AIFallbackRequester):
            r = await fr.get_resource()
            for k, v in kwargs.items():
                if hasattr(r, k):
                    setattr(r, k, v)
            return fr

        AI_FACTORY_LOG.raise_exception_with_log(ValueError("This facade works only with the type of "
                                                           "AIFallbackRequester!"))

    @staticmethod
    async def create_image_generator(factory_type: type[AIBaseServiceFactory] = AIFastServiceFactory, **kwargs) -> ILLMImageGenerator:

        f = factory_type()  # Create factory
        ig = await f.create_image_generator()
        if isinstance(ig, ImageGeneratorFacade):
            r = await ig.get_resource()
            for k, v in kwargs.items():
                if hasattr(r, k):
                    setattr(r, k, v)
            return ig

        AI_FACTORY_LOG.raise_exception_with_log(ValueError("This facade works only with the type of "
                                                           "ImageGeneratorFacade!"))


async def test():
    init_default_classes()

    # fr = await AIServiceFacade.create_chat_completion(factory_type=AIQualityServiceFactory,
    #                                                   system="Be precise and concise.",
    #                                                   stream=True,
    #                                                   stream_delta_callback=lambda m: print(m, end="", flush=True))
    #
    # await fr.prompt("Hello there! Tell me a story about a cowboy")

    image_gen = await AIServiceFacade.create_image_generator(factory_type=AIQualityServiceFactory)
    img_path = await image_gen.generate("A cowboy in the middle of a desert")
    if isinstance(img_path, ImgPaths):
        print(img_path)

#
# if __name__ == "__main__":
#     asyncio.run(test())
