from app.bot import config
from app.misc.registry_objects.chat_completions_registry import register_llm_chat_completion_requests
from app.llm.image_generator.image_generation_requests import ImageGenerationRequest
from app.misc.prototype_registry import PrototypeRegistry


def init_default_classes():
    register_llm_chat_completion_requests()

    image_generator_request = ImageGenerationRequest(url="https://api.openai.com/v1/images/generations",
                                                     api_key=config.openai_config["api_key"],
                                                     api_service='OpenAI (DALL-E)')
    PrototypeRegistry.register_object("openai_image_generator", image_generator_request, "image_generators")
