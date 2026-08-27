import logging

from app.bot import config
from app.llm.base_chat_completion import BaseChatCompletionRequest
from app.misc.prototype_registry import PrototypeRegistry, LOG_REGISTRY


def register_llm_chat_completion_requests():
    # Create objects
    OPENAI_SERVICE = BaseChatCompletionRequest(url="https://api.openai.com/v1/chat/completions",
                                               api_key=config.openai_config['api_key'],
                                               api_service='OpenAI')
    PERPLEXITY_SERVICE = BaseChatCompletionRequest(url="https://api.perplexity.ai/chat/completions",
                                                   api_key=config.PERPLEXITY_API_KEY,
                                                   api_service='Perplexity')

    # Register prototype objects
    PrototypeRegistry.register_object("openai", OPENAI_SERVICE, category="chat_completions")
    PrototypeRegistry.register_object('pplx', PERPLEXITY_SERVICE, category="chat_completions")

    LOG_REGISTRY.log(logging.INFO, "Registered chat completions")


