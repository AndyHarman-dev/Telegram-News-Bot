import piexif
import requests
import os

from dotenv import load_dotenv
from app.bot.config import telegram_config
from app.init import init_default_classes
from app.misc.utilities import ImageProcessor, download_image
from PIL import Image, ImageDraw, ImageFont
from app.factories.ai_factories import AIServiceFacade, AIQualityServiceFactory

import logging
from app.misc.log_helper import LogHelper
import json

from app.misc.paths import Paths


import asyncio


LOG_IMAGEGENERATOR = LogHelper(__name__, "ImageGenerator")


class ImageGenerator:
    save_path = Paths.ROOT_DIR + '/saved/images/'

    load_dotenv()
    api_key = ('STABILITY_API_KEY')
    image_size = os.getenv('IMAGE_SIZE', '1024x1024')



    @staticmethod
    async def get_image(image_name, prompt, max_attempts=2):
        """
        Asynchronously gets an image based on the specified image name and prompt, with a maximum number of attempts.

        Args:
            image_name (str): The name of the image.
            prompt (str): The prompt used for generating the image.
            max_attempts (int): The maximum number of attempts to get the image (default is 2).

        Returns:
            str or None: The file path of the saved image if successful, or None if the image couldn't be obtained.
        """


        attempt = 0
        while attempt < max_attempts:
            if image_name is not None and ImageGenerator.is_image_exists(image_name):
                LOG_IMAGEGENERATOR.log(logging.INFO, f"get_image - get image from cache: {image_name} ")
                file_path = os.path.join(ImageGenerator.save_path, f"{image_name}.jpeg")
                return str(file_path)
            else:
                if prompt is None:
                    LOG_IMAGEGENERATOR.log(logging.WARNING, f"get_image - Can't get image for empty prompt: {image_name} ")
                    return None
                try:

                    # try generate
                    image_url, completed_prompt = await ImageGenerator.generate_image(prompt)

                    if image_url is not None:
                        saved_file_path = await ImageGenerator.save_image_from_url(image_url, image_name, completed_prompt, save_png=False, add_watermark=True)
                        return str(saved_file_path)
                except ValueError as e:
                    LOG_IMAGEGENERATOR(logging.ERROR, f"get_image - Can't get image: {image_name} - {str(e)}")
                    return None

            # Change prompt to be appropriate
            attempt += 1

            fr = await AIServiceFacade.create_chat_completion(factory_type=AIQualityServiceFactory)
            response = await fr.prompt(f"Rewrite this prompt to make it not"
                                       f"to violate the OpenAI's content policy, remove all real names, and shocking detailes, make it safe, or make new suitable prompt: {prompt}")

            # Ensure 'prompt' is a string after modification
            if isinstance(response, tuple):
               prompt = response[0]  # Assuming the first element of the tuple is the modified prompt
            else:
               prompt = response  # If response is already a string

        # Если изображение так и не было сгенерировано
        return None

    @staticmethod
    def is_image_exists(image_name: str) -> bool:
        """
        Check if the specified image exists and return a boolean value.

        Args:
            image_name (str): The name of the image file.

        Returns:
            bool: True if the image exists, False otherwise.
        """
        if not image_name.endswith('.jpeg'):
            image_name += '.jpeg'

        file_path = os.path.join(ImageGenerator.save_path, image_name)
        return os.path.exists(file_path)

    @staticmethod
    async def generate_image(prompt: str) -> (str, str):
        """
        An asynchronous static method to generate an image using the OpenAI API.
        Takes a prompt string and returns a tuple of response and completed prompt.
        """
        image_gen = await AIServiceFacade.create_image_generator(factory_type=AIQualityServiceFactory,
                                                                 size="1024x1024",  # ImageGenerator.image_size,
                                                                 quality="standard",
                                                                 n=1,
                                                                 response_format="url",
                                                                 )
        img_path = await image_gen.generate(prompt)

        completed_prompt = "CompletedPrompt example"  # response.data[0].revised_prompt

        if not await img_path.is_valid():
            LOG_IMAGEGENERATOR.raise_exception_with_log(ValueError("Invalid image path!"))

        return img_path.paths[0], completed_prompt

    @staticmethod
    async def save_image_from_url(image_url, image_name, prompt='', save_png=False, add_watermark=True):
        os.makedirs(ImageGenerator.save_path, exist_ok=True)

        image_data = await download_image(image_url)

        image_processor = ImageProcessor(image_data, image_name, ImageGenerator.save_path)
        jpeg_file_path = await image_processor.process(save_png, add_watermark, prompt)

        return str(jpeg_file_path)

    @staticmethod
    async def add_exif_data(image_path, prompt= telegram_config['bot_name']):
        exif_dict = {"0th": {piexif.ImageIFD.Make: telegram_config['bot_name'],
                             piexif.ImageIFD.Software: telegram_config['bot_name'],
                             piexif.ImageIFD.ImageDescription: prompt.encode()},
                     "Exif": {}}
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(image_path))  # path to string
        return

    @staticmethod
    def add_watermark(image_path, watermark_text = telegram_config['bot_name']):
        with Image.open(image_path) as original:
            original = original.convert("RGBA")
            width, height = original.size

            # Create a new transparent image for watermark
            watermark_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            d = ImageDraw.Draw(watermark_img)

            # Font settings
            font_size = 34

            try:
                font_path = Paths.ROOT_DIR + '/content/assets/fonts/blanka.otf'
                fnt = ImageFont.truetype(font_path, font_size)
            except IOError:
                print("Font not found, using default font.")
                fnt = ImageFont.load_default()

            # Calculate text size (don't work) hardcoded manually
            #text_width, text_height = d.textsize(watermark_text, font=fnt)
            text_width = round(len(watermark_text) * font_size * 0.55)
            text_height = font_size

            # Calculate positions
            x = width - text_width - 20  # Offset from the right
            y = height - text_height - 20  # Offset from the bottom

            # Draw a rectangle with semi-transparent fill behind the text
            rectangle_background = (0, 0, 0, 128)  # Black with 50% opacity
            d.rectangle([x - 10, y - 10, x + text_width + 10, y + text_height + 10], fill=rectangle_background)

            # Draw text with a white fill
            text_color = (255, 255, 255, 255)  # White
            d.text((x, y), watermark_text, font=fnt, fill=text_color)

            # Composite watermark with the original image
            watermarked = Image.alpha_composite(original, watermark_img)
            watermarked = watermarked.convert("RGB")
            watermarked.save(image_path, "JPEG")

    @staticmethod
    def delete_image(post_id):
        """
        Delete image associated with a post, if it exists.

        Args:
            post_id (int): ID post, which image should delete
        """
        jpeg_image_path = ImageGenerator.save_path + f'{post_id}.jpeg'
        png_image_path = ImageGenerator.save_path + f'{post_id}.png'

        if not jpeg_image_path.exists() and not png_image_path.exists():
            print(f"No image found for post ID {post_id}.")

        # check and delete .jpeg
        if jpeg_image_path.exists():
            os.remove(jpeg_image_path)
            print(f"Image {jpeg_image_path} has been deleted.")

        # check and delete .png
        if png_image_path.exists():
            os.remove(png_image_path)
            print(f"Image {png_image_path} has been deleted.")




class ImageGeneratorSD:
    save_path = Paths.ROOT_DIR + '/saved/images/'

    @staticmethod
    def generate_image(prompt, n=1):
        load_dotenv()
        api_key = os.getenv('STABILITY_API_KEY')

        url = "https://api.stability.ai/v2beta/stable-image/generate/core"
        payload = json.dumps({
            "key": api_key,  # Убедитесь, что ваш ключ API указан правильно
            "prompt": prompt,
            "width": "512",
            "height": "512",
            "samples": str(n),
            "num_inference_steps": "10",
            "guidance_scale": 7.5,
            "safety_checker": "yes",
            # Добавьте дополнительные параметры, если необходимо
            "negative_prompt": None,
            "seed": None,
            "multi_lingual": "no",
            "panorama": "no",
            "self_attention": "no",
            "upscale": "no",
            "embeddings_model": None,
            "webhook": None,
            "track_id": None
        })
        headers = {
            "authorization": api_key,
            "accept": "image/*"
        },

        response = requests.request("POST", url, headers=headers, data=payload)

        if response.status_code == 200:
            with open("./lighthouse.webp", 'wb') as file:
                file.write(response.content)
        else:
            raise Exception(str(response.status_code) + str(response.json()))

        if response.status_code == 200:
            data = response.json()
            # Handle successful response case
            if data["status"] == "success":
                for image_url in data["output"]:
                    ImageGeneratorSD.save_image_from_url(image_url, prompt)
            else:
                # Print error message with the name of the current file (__file__) or function
                print(f"Error in {__name__} at {__file__}: ", data.get("message"))
        else:
            # Print error message with the status code of the response, including the file name or function
            print(f"Error generating image in {__name__} at {__file__}: Status code {response.status_code}")

    @staticmethod
    def save_image_from_url(image_url, image_name):
        os.makedirs(ImageGeneratorSD.save_path, exist_ok=True)
        response = requests.get(image_url)
        if response.status_code == 200:
            img_path = ImageGeneratorSD.save_path + f"{image_name}.jpeg"
            with open(img_path, 'wb') as img_file:
                img_file.write(response.content)
            print(f"Изображение сохранено как {img_path}")
        else:
            # Print error message with the name of the current file (__file__) or function
            print(f"Error in {__name__} at {__file__}: ", response.status_code)

if __name__ == "__main__":
   init_default_classes()
   #app.misc.registry_objects.chat_completions_registry.register_llm_chat_completion_requests()

   asyncio.run(ImageGenerator.get_image("test102","ultra realistic close up portrait of a beautiful pale cyberpunk female with heavy black eyeliner"))
    #asyncio.run(ImageGenerator.get_image("test2","donald trump fucks putin hardcore"))

    #'Discuss the diplomatic relations between the United States and Russia.'

    #ImageGeneratorSD.generate_image("donald trump fucks putin hardcore")
