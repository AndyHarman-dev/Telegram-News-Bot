import json
import asyncio
import aiofiles

from app.misc.paths import Paths
from pathlib import Path

from abc import ABC, abstractmethod
from app.misc.log_helper import LogHelper

PATH_TO_LOCALE_FILES = Paths.ROOT_DIR+'/settings/localization/'  # Relative to the main function
LOCALIZATION_LOGGER = LogHelper(__name__, "Localization Thread")


class LocaleNotFound(Exception):

    def what(self):
        return "Locale not found"


class LocalizedText(ABC):
    def __init__(self, translations):
        self.translations = translations

    @abstractmethod
    async def get_text(self, key):
        pass

    @staticmethod
    async def create(locale):
        """
        Create a localized text object based on the given locale.

        :param locale: The locale for which the localized text object will be created.
        :type locale: str
        :return: A localized text object based on the given locale.
        :rtype: LeftToRightLocalizedText or RightToLeftLocalizedText
        :raises ValueError: If the specified locale is not supported.
        """
        try:
            path = PATH_TO_LOCALE_FILES + locale
            async with aiofiles.open(f"{path}.json", "r", encoding="utf-8") as file:
                translations = await file.read()
                translations = json.loads(translations)  # JSON parsing is still synchronous
                if translations.get("metadata", {}).get("text_direction") == "rtl":
                    return RightToLeftLocalizedText(translations)
                else:
                    return LeftToRightLocalizedText(translations)
        except FileNotFoundError as e:
            raise LocaleNotFound(f"Locale '{locale}' not found.")


class LeftToRightLocalizedText(LocalizedText):
    async def get_text(self, key) -> str:
        from app.bot.telegram_bot import ChatGPTTelegramBot
        key = ChatGPTTelegramBot.menu_generalization(key)
        keys = key.split('.')
        value = self.translations
        for k in keys:
            value = value.get(k)
            if value is None:
                LOCALIZATION_LOGGER.raise_exception_with_log(
                    ValueError(f"Key '{key}' not found."))  # Return empty string if the key is not found
        return value


class RightToLeftLocalizedText(LocalizedText):
    async def get_text(self, key):
        from app.bot.telegram_bot import ChatGPTTelegramBot
        key = ChatGPTTelegramBot.menu_generalization(key)
        keys = key.split('.')
        value = self.translations
        for k in keys:
            value = value.get(k)
            if value is None:
                return ""  # Return empty string if the key is not found

        return value[::-1]  # Reverting the string


async def make_localized_text(locale):
    return await LocalizedText.create(locale)


async def test():
    # Example of Usage
    try:
        localized_text = await make_localized_text("en")  # Replace "en" with user's locale
        print(await localized_text.get_text("states.menu.state_display_message"))
    except ValueError as e:
        print(e)
