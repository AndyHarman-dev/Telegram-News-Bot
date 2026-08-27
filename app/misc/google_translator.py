import asyncio
import logging

import requests
import os
from dotenv import load_dotenv
import aiohttp
import requests_cache

from app.misc.log_helper import LogHelper
from app.misc.caching.aiohttp_request_cache import fetch_with_cache
from app.database.db_init import languages

load_dotenv()

LANG_CODES_LIST = [lang['language_code'] for lang in languages]

GOOGLE_TRANSLATION_LOG = LogHelper(__name__, "Google translation thread")

# Your API key
api_key = os.environ.get('GOOGLE_TRANSLATION_API_KEY')

# URL to the Google Cloud Translation API including the API key in the query parameters
url = f'https://translation.googleapis.com/language/translate/v2?key={api_key}'

# Set up caching for request here
requests_cache.install_cache("google_translator_cache", backend="sqlite", expire_after=3600)


class GoogleTranslator:
    @staticmethod
    def translate_text(text, target_language):
        """
        A static method to translate text to a target language.

        Args:
            text (str): The text to be translated.
            target_language (str): The language to translate the text to.

        Returns:
            str: The translated text.
        """

        # Construct the request payload
        data = {
            'q': text,
            'target': target_language,
            'format': 'text'
        }

        # Make the request
        response = requests.post(url, json=data)

        # Check for errors
        if response.status_code != 200:
            GOOGLE_TRANSLATION_LOG.raise_exception_with_log(ValueError(f"Response code is not 200 when trying Error {response.status_code}"
                                                                       f"to translate the following text {text}"))
        else:
            # Parse the response
            result = response.json()

            # return the translated text
            return result['data']['translations'][0]['translatedText']

    @staticmethod
    async def translate_text_async(text, target_language, custom_session: aiohttp.ClientSession = None):
        """
        A static method to translate text asynchronously using Google Translate API.

        Args:
            text (str): The text to be translated.
            target_language (str): The language code for the target language.
            custom_session (aiohttp.ClientSession, optional): A custom aiohttp session to use for the request. Defaults to None.

        Returns:
            The translated text.
        """
        # Construct the request payload
        data = {
            'q': text,
            'target': target_language,
            'format': 'text'
        }

        # If session already present, make the request using the session
        if custom_session:
            return await GoogleTranslator._process_async_request(custom_session, data)

        # Create an aiohttp session
        async with aiohttp.ClientSession() as session:
            return await GoogleTranslator._process_async_request(session, data)

    @staticmethod
    async def translate_batch_async(texts, taget_language, custom_session: aiohttp.ClientSession =None):
        """
        Asynchronously translates a batch of texts to the target language using Google Translator.

        Args:
            texts: The list of texts to be translated.
            taget_language: The target language to translate the texts into.
            custom_session: (Optional) A custom aiohttp ClientSession to use for the translation.

        Returns:
            A list of translated texts in the target language.
        """
        tasks = []
        for text in texts:
            task = GoogleTranslator.translate_text_async(text, target_language=taget_language,
                                                         custom_session=custom_session)
            tasks.append(task)

        return await asyncio.gather(*tasks)

    @staticmethod
    async def _process_async_request(session, data):
        """
        A static method to process an asynchronous request using the provided session and data.
        """

        if session is None:
            GOOGLE_TRANSLATION_LOG.raise_exception_with_log(ValueError("You passed a session that is None!"))

        result = await fetch_with_cache(url, method='POST', data=data, custom_session=session)
        GOOGLE_TRANSLATION_LOG.log(logging.INFO, result)
        if 'data' in result:
            # Return the translated text
            return result['data']['translations'][0]['translatedText']
        GOOGLE_TRANSLATION_LOG.raise_exception_with_log(KeyError(f'Only this key(s) available: {", ".join(str(k) for k in result.keys())}. '
                                                                 f'And "data" key is needed.'))


async def main():
    batch = [
        "Hello",
        "How are you?",
        "I am fine",
        "Thank you",
        "Goodbye",
    ]
    print(await GoogleTranslator.translate_batch_async(batch, "fr"))


if __name__ == "__main__":
    asyncio.run(main())
