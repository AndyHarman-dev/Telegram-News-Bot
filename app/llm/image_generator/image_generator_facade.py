import logging

from app.interfaces.resource import IResourceHolder, IResource
from app.interfaces.ai_service_interfaces import ILLMImageGenerator
from app.interfaces.ret_val import IRetValue
from app.misc.prototype_registry import PrototypeRegistry
from app.misc.log_helper import LogHelper
from app.llm.image_generator.image_generation_requests import ImageGenerationRequest, ImgPaths
from app.misc.timeout import with_timeout
from app.llm.resources import IMGRequestResource

LOG_IMG_GEN_FACADE = LogHelper(__name__, "ImageGeneratorFacade")


class ImageGeneratorFacade(IResourceHolder, ILLMImageGenerator):

    # TODO: протестировать таймауты и работу функции
    async def generate(self, prompt: str) -> IRetValue:

        if not self._resource:
            LOG_IMG_GEN_FACADE.raise_exception_with_log(ValueError("Resource not set!"))

        generator = PrototypeRegistry.get_object("openai_image_generator", category="image_generators")

        if not isinstance(generator, ImageGenerationRequest):
            LOG_IMG_GEN_FACADE.raise_exception_with_log(ValueError("Image generator not registered!"))

        if not isinstance(self._resource, IMGRequestResource):
            LOG_IMG_GEN_FACADE.raise_exception_with_log(ValueError("Invalid resource for image generation request."))

        self._resource.prompt = prompt

        # Call the generation function with the timeout
        try:
            return await with_timeout(generator.request,
                                      self.image_generation_timeout,
                                      callback=None,
                                      args=(self._resource,))
        except TimeoutError as e:
            return ImgPaths(["Time Out (for image generation)"])
        except Exception as e:
            LOG_IMG_GEN_FACADE(logging.WARNING, f"Some error ocurred during image generation: "
                                                f"{e}\n Returning an empty image path...")
            return ImgPaths(["Some Error"])

    def __init__(self):
        self.image_generation_timeout = 240  # Give maximum of 3 minutes for timeout
        self._resource = None

    async def set_resource(self, res: IResource):
        self._resource = res

    async def get_resource(self) -> IResource:
        return self._resource
