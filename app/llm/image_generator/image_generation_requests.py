import asyncio
import logging
from abc import ABC

from app.api.base_api_request import BaseAPIRequest
from app.bot import config
from app.bot.config import util_config
from app.interfaces.resource import IResource
from app.interfaces.ret_val import IRetValue
from app.llm.resources import IMGRequestResource
from app.misc.log_helper import LogHelper
from app.llm.exceptions import InvalidResource
from app.misc.utilities import contains_url

LOG_IMG_GENERATOR = LogHelper(__name__, "ImageGenerator")


class ImgPaths(IRetValue):
    def __init__(self, paths: list[str]):
        self.paths = paths

    def __await__(self):
        pass

    async def is_valid(self) -> bool:
        if self.paths and contains_url(self.paths):
            return True
        else:
            return False


class ImageGenerationRequest(BaseAPIRequest):

    async def prepare_resource(self, *args, **kwargs) -> IResource:

        parameter = args[0].clone()  # We don't want a reference to the original parameter

        if not isinstance(parameter, IMGRequestResource):
            LOG_IMG_GENERATOR.raise_exception_with_log(InvalidResource(
                "Invalid resource for image generation request."
            ))

        # If the next instance of arguments is a string, that might be the prompt for our image generation
        # so supply it if the prompt in the resource is empty
        if isinstance(args[1], str):
            parameter.prompt = args[1]
        else:
            LOG_IMG_GENERATOR.log(logging.WARNING,
                                  f"Expected to get second argument of type string got {type(args[1])} instead."
                                  f"If it wan intentional, please review the usage of {type(ImageGenerationRequest)}")

        return parameter

    def _prepare_payload(self, resource: IResource) -> dict:

        if not isinstance(resource, IMGRequestResource):
            LOG_IMG_GENERATOR.raise_exception_with_log(InvalidResource(
                "Invalid resource for image generation request."
            ))

        return {
            "model": resource.models[0],
            "prompt": resource.prompt,
            "n": resource.n,
            "size": resource.size
        }

    async def _process_response(self, response, resource: IResource) -> IRetValue:

        if util_config['debug_mode']:
            response_text = await response.text()
            LOG_IMG_GENERATOR.log(logging.INFO, "Response Text:" + response_text)

        if not isinstance(resource, IMGRequestResource):
            LOG_IMG_GENERATOR.raise_exception_with_log(InvalidResource(
                "Invalid resource for image generation request."
            ))

        if not response:
            LOG_IMG_GENERATOR.raise_exception_with_log(ValueError(f"Response is empty!"))

        if response.status != 200:
            LOG_IMG_GENERATOR.raise_exception_with_log(
                ValueError(f"Response code is not 200! Error message {response.reason}"))




        response_json = await response.json()

        if resource.multiple:
            paths = [url_obj['url'] for url_obj in response_json["data"]]
            return ImgPaths(paths)
        else:
            return ImgPaths([response_json["data"][0]["url"]])


async def my_func():
    base_request = ImageGenerationRequest(url="https://api.openai.com/v1/images/generations", api_key=config.openai_config["api_key"])
    resource = IMGRequestResource(
        models=["dall-e-3"],
        prompt="an image of a cat-dog",
        n=1,
        size="1024x1024"
    )

    # Try with no type
    img_path = await base_request.request(resource)
    print(img_path)

    # Try with multiple types
    #resource.multiple = True
    #imgs = await base_request.request(resource)

    #print(imgs)


if __name__ == "__main__":
     asyncio.run(my_func())