import asyncio
import os
import logging

import telegram
from telegram import Bot, Update
from telegram.ext import CallbackContext

from app.bot.config import telegram_config
from app.misc.log_helper import LogHelper
from app.misc.paths import Paths

LOG_TELEGRAMHELPER = LogHelper(__name__, "Telegram_Helper")


class TelegramHelper:
    MAX_CHAR_COUNT_WITH_IMAGE = 1024
    MAX_CHAR_COUNT_WITHOUT_IMAGE = 4096

    @staticmethod
    async def send_message_with_photo(chat_id, text_message, photo_path):
        """
        Send a message with photo. If the message exceeds Telegram's text length limits, it is sent in multiple parts.

        Args:
            chat_id : chat ID.
            text_message (str): Message text.
            photo_path (str): Path to photo file.
        """
        async with Bot(token=telegram_config['token']) as bot:

            # Check photo
            if photo_path is not None and os.path.exists(photo_path) and os.path.isfile(photo_path):
                with open(photo_path, 'rb') as photo:
                    # Check text length for the caption and split if necessary
                    if len(text_message) > TelegramHelper.MAX_CHAR_COUNT_WITH_IMAGE:
                        parts = TelegramHelper.split_text(text_message, TelegramHelper.MAX_CHAR_COUNT_WITH_IMAGE)
                        await bot.send_photo(chat_id=chat_id, photo=photo, caption=parts[0], parse_mode="HTML")
                        for part in parts[1:]:
                            await bot.send_message(chat_id=chat_id, text=part, parse_mode="HTML")
                    else:
                        text_message = TelegramHelper.remove_after_last_dot(text_message)
                        await bot.send_photo(chat_id=chat_id, photo=photo, caption=text_message, parse_mode="HTML")

            else:
                LOG_TELEGRAMHELPER.log(logging.ERROR, f"Can't find file '{photo_path}'")

                # If the photo is not available, send the text in parts if necessary
                if len(text_message) > TelegramHelper.MAX_CHAR_COUNT_WITHOUT_IMAGE:
                    parts = TelegramHelper.split_text(text_message, TelegramHelper.MAX_CHAR_COUNT_WITHOUT_IMAGE)
                    for part in parts:
                        await bot.send_message(chat_id=chat_id, text=part, parse_mode="HTML")
                    LOG_TELEGRAMHELPER.log(logging.INFO, "Long message was sent in parts to chat: " + str(chat_id))
                else:
                    text_message = TelegramHelper.remove_after_last_dot(text_message)
                    await bot.send_message(chat_id=chat_id, text=text_message, parse_mode="HTML")
                    LOG_TELEGRAMHELPER.log(logging.INFO, "Message was sent to chat: " + str(chat_id))

    @staticmethod
    def split_text(full_text, max_length) -> list:
        import re
        # Step 1: Replacing a sequence of points with a single point
        full_text = re.sub(r'\.{2,}', '.', full_text)

        # Step 2: Deleting words that are too long
        # The likelihood of that happening is extremely low.
        # When using this approach, something adequate will have to be done with spaces and line breaks
        # that were before and after the deleted words.

        # words = re.findall(r'\S+', full_text)
        # filtered_words = [word for word in words if len(word) <= max_length]
        # full_text = ' '.join(filtered_words)

        # Step 3: Break the text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', full_text)

        result = []
        current_block = ""

        for sentence in sentences:
            if len(current_block) + len(sentence) <= max_length:
                current_block += sentence + " "
            else:
                if current_block:
                    result.append(current_block.strip())
                    current_block = ""

                if len(sentence) <= max_length:
                    current_block = sentence + " "
                else:
                    # Breaking up a long sentence word by word
                    words = sentence.split()
                    temp_block = ""
                    for word in words:
                        if len(temp_block) + len(word) + 1 <= max_length:
                            temp_block += word + " "
                        else:
                            if temp_block:
                                result.append(temp_block.strip())
                            temp_block = word + " "
                    if temp_block:
                        current_block = temp_block

        if current_block:
            result.append(current_block.strip())

        # Step 4: Remove all characters after the last dot (or line break) in the last block
        result[-1] = TelegramHelper.remove_after_last_dot(result[-1])

        return result

    @staticmethod
    def remove_after_last_dot(text_message: str) -> str:
        last_dot = text_message.rfind('.')
        last_newline = text_message.rfind('\n')
        split_index = max(last_dot, last_newline)
        if split_index != -1:
            text_message = text_message[:split_index if last_newline > last_dot else split_index + 1]
        return text_message

    @staticmethod
    def escape_markdown_v2(text, ignore_chars=None):
        """
        Escape special characters in a given text using Markdown syntax.

        Args:
            text (str): The text to be escaped.
            ignore_chars (list[str], optional): A list of character sequences to ignore when escaping. Defaults to ['__', '**'].

        Returns:
            str: The escaped text.

        Note:
            - The function checks for the following special characters to be escaped: `_*[]()~`>#+-=|{}.!`.
            - If a character sequence in `ignore_chars` is found at the end of the previous characters, it will not be escaped.
            - The function uses a stack-based approach to check if a character should be escaped or not.
        """
        if ignore_chars is None:
            ignore_chars = ['__', '**']

        # Symbols to escape by Markdown
        escape_chars = '_*[]()~`>#+-=|{}.!'

        # Function to check if a character should be escaped
        def should_escape(char, prev_chars):
            for ignore in ignore_chars:
                if char in ignore and ''.join(prev_chars[-len(ignore):]) == ignore[:-1]:
                    return False
            return True

        # Symbols to escape
        result = []
        for char in text:
            if char in escape_chars and should_escape(char, result):
                result.append('\\')
            result.append(char)

        return ''.join(result)

    @staticmethod
    async def send_loading_animation(update: Update, context: CallbackContext, time=10):
        """
        Send a loading animation to the chat.

        Args:
            update (Update): The update object containing information about the incoming message.
            context (CallbackContext): The context object for the current callback.
            time (int, optional): The duration of the loading animation in seconds. Defaults to 10.

        Returns:
            int: The message ID of the sent loading animation.
        """
        chat_id = update.message.chat_id

        # URL loading animation
        loading_animation_url = "https://upload.wikimedia.org/wikipedia/commons/b/b1/Loading_icon.gif"

        # send loading animation
        message = await context.bot.send_animation(chat_id=chat_id, animation=loading_animation_url, duration=time)

        # Сохранить идентификатор отправленного сообщения для последующего удаления
        message_id = message.message_id

        return message_id

    @staticmethod
    async def is_bot_blocked(chat_id, try_number: int = 1) -> bool:

        async def time_out_repeating(repeat_number: int = 1, max_repeating: int = 3) -> bool:
            if repeat_number < max_repeating:
                LOG_TELEGRAMHELPER.log(logging.ERROR, f"Timeout problem with chat {chat_id}")
                # await asyncio.sleep(int(1.5**(max_repeating+1)))
                return await TelegramHelper.is_bot_blocked(chat_id, repeat_number + 1)
            LOG_TELEGRAMHELPER.log(logging.ERROR, f"Repeating timeout problem with chat {chat_id}")
            return True
        """
        Checks if a user has not blocked the bot in a given chat.

        Parameters:
            chat_id (int): The ID of the chat to check.
            repeating (bool): A flag that indicates whether this function is being called a second time.

        Returns:
            bool: True if the user has not blocked the bot, False otherwise.
        """
        async with Bot(token=telegram_config['token']) as bot:

            try:
                # Attempt to send message
                await bot.send_chat_action(chat_id=chat_id, action='typing')
                return False  # User not blocked our bot
            except ValueError as e:
                LOG_TELEGRAMHELPER.log(logging.WARNING, f'Bot blocked in chat {chat_id}')
                return True  # User blocked our bot
            except (TimeoutError, asyncio.TimeoutError, telegram.error.TimedOut) as e:
                return await time_out_repeating(try_number)
            except Exception as e:
                if "timed out" in str(e).lower():
                    return await time_out_repeating(try_number)
                LOG_TELEGRAMHELPER.log(logging.ERROR, f"Exception occurred: {e} (for instance with id {chat_id})")
                return True


if __name__ == "__main__":
    saved_dir = Paths.get_saved_dir()
    text = "<b> Тестовое сообщение </b>"
    #asyncio.run( TelegramHelper.send_message_with_photo(466001259, text,  Paths.combine(saved_dir, "images", "107.jpeg")))
