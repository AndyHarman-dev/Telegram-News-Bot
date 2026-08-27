# String utilities
import re

import piexif

from app.bot.config import telegram_config

URL_PATTERN = re.compile(r'https?://(?:www\.)?[a-zA-Z0-9./]+')


def contains_url(obj: str | list[str]):
    if isinstance(obj, str):  # If it's a single string, then just search it
        return bool(URL_PATTERN.search(obj))

    if isinstance(obj, list):  # if it's a list, iterate over each string, and search for match
        for string in obj:
            if URL_PATTERN.search(string):
                return True

    return False  # If nothing matched, return False

# ===========================================================================
#Other

def number_to_emoji(number):
    emoji_numbers = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
    if 0 <= number <= 9:
        return emoji_numbers[number]
    return str(number)

# ===========================================================================

# Image utilities
import io
from PIL import Image, ImageDraw, ImageFont
from app.misc.paths import Paths
import aiohttp


class ImageUtils:
    @staticmethod
    def add_watermark(image_path, watermark_text):
        """
        Adds a watermark to an image.

        Args:
            image_path (str): The path to the image file.
            watermark_text (str): The text to be added as a watermark.

        Returns:
            None

        Raises:
            IOError: If the specified font file is not found.

        Description:
            This function opens an image file, converts it to RGBA format, and creates a new transparent image for the watermark. It then sets the font settings, calculates the text size, and calculates the positions of the watermark text. It draws a rectangle with semi-transparent fill behind the text, draws the text with a white fill, composites the watermark with the original image, and saves the modified image.
        """
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
            # text_width, text_height = d.textsize(watermark_text, font=fnt)
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
    async def add_exif_data(image_path, prompt):
        """
        Adds EXIF data to an image file.

        Args:
            image_path (str): The path to the image file.
            prompt (str): The prompt to be added as EXIF data.

        Returns:
            None

        Description:
            This function adds EXIF data to an image file. It creates a dictionary with the EXIF data, including the Make, Software, and ImageDescription fields. The Make and Software fields are set to the value of `telegram_config['bot_name']`, and the ImageDescription field is set to the encoded version of the `prompt` string. The dictionary is then converted to bytes using `piexif.dump()`. Finally, the EXIF data is inserted into the image file using `piexif.insert()`.

        Note:
            This function requires the `piexif` library to be installed.
        """
        exif_dict = {"0th": {piexif.ImageIFD.Make: telegram_config['bot_name'],
                             piexif.ImageIFD.Software: telegram_config['bot_name'],
                             piexif.ImageIFD.ImageDescription: prompt.encode()},
                     "Exif": {}}
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(image_path))  # path to string


async def download_image(image_url):
    """
    Downloads an image from the specified URL asynchronously.

    Returns:
        The downloaded image content as bytes.

    Raises:
        Exception: If the image download fails with a non-200 status code.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if response.status == 200:
                return await response.read()
            else:
                raise Exception(f"ERROR LOADING IMAGE: {response.status}")


class ImageProcessor:
    def __init__(self, image_data, image_name, save_path):
        self.image_data = image_data
        self.image_name = image_name
        self.save_path = save_path

    async def process(self, save_png, add_watermark, prompt):
        """
        Asynchronously processes an image by saving it in PNG and JPEG formats, adding a watermark, and adding EXIF data.

        Args:
            save_png (bool): Flag indicating whether to save the image in PNG format.
            add_watermark (bool): Flag indicating whether to add a watermark to the image.
            prompt (str): The prompt for adding EXIF data to the image.

        Returns:
            str: The file path of the saved JPEG image.
        """
        if save_png:
            png_file_path = self.save_path + f"{self.image_name}.png"
            with open(png_file_path, 'wb') as file:
                file.write(self.image_data)

        jpeg_file_path = self.save_path + f"{self.image_name}.jpeg"
        with Image.open(io.BytesIO(self.image_data)) as img:
            img = img.convert("RGB")
            img.save(jpeg_file_path, "JPEG")

        if add_watermark:
            ImageUtils.add_watermark(jpeg_file_path, telegram_config['bot_name'])

        await ImageUtils.add_exif_data(jpeg_file_path, prompt)

        return str(jpeg_file_path)


if __name__ == "__main__":
    pass
