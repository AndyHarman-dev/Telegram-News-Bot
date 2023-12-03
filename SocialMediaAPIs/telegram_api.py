import telebot
from config import config

# Obtain telegram token from the config
TOKEN = config.CONFIG_DICT['token']

# Create bot instance
BOT = telebot.TeleBot(TOKEN)

# Define const things
TELEGRAM_SEND_PHOTO_URL = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"


class TelegramAPI:
    """
    Sends a message to a chat identified by `chat_id`.

    Args:
        @chat_id (int): The ID of the chat to send the message to.
        @message (str): The content of the message to send.
    """

    @staticmethod
    def send_message(chat_id: int, message: str):
        BOT.send_message(chat_id, message)

    """
    Send multiple images to a chat.

    Parameters:
        chat_id (int): The ID of the chat where the images will be sent.
        image_urls (list): A list of URLs of the images to be sent.

    Returns:
        None
    """
    @staticmethod
    def send_images(chat_id: int, image_urls: list):
        media = [telebot.types.InputMediaPhoto(image_url) for image_url in image_urls]
        BOT.send_media_group(chat_id=chat_id, media=media)
