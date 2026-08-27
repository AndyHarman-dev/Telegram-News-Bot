import asyncio
import os
import requests

from app.init import init_default_classes
from app.llm.image_generator.image_generator_base import ImageGenerator
from app.misc.paths import Paths


class ImageGeneratorPexels(ImageGenerator):
    save_path = Paths.ROOT_DIR + '/saved/images/'
    api_key = os.getenv('PEXELS_API_KEY')

    @staticmethod
    async def get_image(image_name, prompt, max_attempts=2):
        """
        Fetches an image from Pexels API based on the specified query.

        Args:
            query (str): The search query to fetch the image.

        Returns:
            str: The file path of the saved image if successful, None otherwise.
        """
        url = "https://api.pexels.com/v1/search"
        headers = {
            'Authorization': ImageGeneratorPexels.api_key
        }
        params = {
            'query': prompt,
            'per_page': 1  # You can adjust the number of images per request
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['photos']:
                image_url = data['photos'][0]['src']['original']
                return await ImageGenerator.save_image_from_url(image_url, image_name)
            else:
                print("No images found for query:", prompt)
        else:
            print("Failed to fetch images:", response.status_code)

        return None


async def my_func():
    init_default_classes()
    img_gen = ImageGenerator()

    test_prompt = """
    «Никогда не делалось прежде»: Истинное расследование провальной американской войныКомиссия по расследованию войны в Афганистане начинает развивать серьезную деятельность.
    Headline: "Американцы пытаются понять, почему они опять проиграли" (Americans are trying to figure out why they lost again)
    """

    await img_gen.get_image("pexels2",test_prompt)  # test request

if __name__ == "__main__":
    asyncio.run(my_func())
