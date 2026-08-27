from app.interfaces.resource import IResource
from app.interfaces.prototype import IPrototype
from app.bot.config import llm_services_config


class LLMRequestResource(IResource, IPrototype):

    def clone(self):
        return LLMRequestResource(
            system=str(self.system),
            messages=list(self.messages),
            temperature=float(self.temperature),
            max_tokens=int(self.max_tokens),
            top_p=float(self.top_p),
            models=list(self.models),
            stream=bool(self.stream),
            from_parser=bool(self.from_parser),
            from_news_manager=bool(self.from_news_manager),
            stream_callback=self.stream_callback,
            stream_delta_callback=self.stream_delta_callback
        )

    def __init__(self, **kwargs):
        """Initializes the LLMRequestResource in order:"""
        self.system = kwargs.get("system", "Be precise and conscise.")
        self.messages = kwargs.get("messages", [])
        self.temperature = kwargs.get("temperature", 0.0)
        self.max_tokens = kwargs.get("max_tokens", int(llm_services_config['max_tokens']))
        self.top_p = kwargs.get("top_p", 1.0)
        self.models = kwargs.get("models", [])
        self.stream = kwargs.get("stream", False)
        self.from_parser = kwargs.get("from_parser", False)
        self.from_news_manager = kwargs.get("from_news_manager", False)
        self.stream_callback = kwargs.get("stream_callback", None)
        self.stream_delta_callback = kwargs.get("stream_delta_callback", None)
        if isinstance(self.models, str):
            # If a single model name is provided, convert it to a list
            self.models = [self.models]

    async def is_valid(self) -> bool:
        return len(self.messages) > 0 or len(self.models) > 0


class IMGRequestResource(IResource, IPrototype):

    def __init__(self, **kwargs):
        """Initializes the LLMRequestResource in order:"""
        self.prompt = kwargs.get("prompt", "")
        self.models = kwargs.get("models", ["dall-e-3"])
        self.size = kwargs.get("size", "1024x1024")
        self.n = kwargs.get('n', 1)
        self.multiple = False

        if self.n > 1:
            self.multiple = True

        if isinstance(self.models, str):
            # If a single model name is provided, convert it to a list
            self.models = [self.models]

    def clone(self):
        return IMGRequestResource(
            prompt=list(self.prompt),
            models=list(self.models),
            size=str(self.size),
            n=int(self.n)
        )

    async def is_valid(self) -> bool:
        return len(self.prompt) > 0 or len(self.models) > 0
