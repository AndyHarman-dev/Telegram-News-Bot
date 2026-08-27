import logging

from app.bot.config import util_config
from app.database.db_helper import DatabaseHelper, DatabaseManager

import asyncio
from datetime import datetime, timedelta

from app.database.db_translation import TranslationManager
from app.database.db_user import UserManager
from app.misc.log_helper import LogHelper

from app.bot.telegram_helper import TelegramHelper

from datetime import datetime, timedelta

LOG_DATABASE_CHAT = LogHelper(__name__, "Database Chat")


class UTCShifter:
    UTC_SHIFT_DICT: dict = { # LEGACY
        "Pago Pago (American Samoa)": -11.0,
        "Honolulu (USA, Hawaii)": -10.0,
        "Anchorage (USA, Alaska)": -9.0,
        "Los Angeles (USA, California)": -8.0,
        "Denver (USA, Colorado)": -7.0,
        "Mexico City (Mexico)": -6.0,
        "New York (USA, New York)": -5.0,
        "Caracas (Venezuela)": -4.0,
        "Buenos Aires (Argentina)": -3.0,
        "Sao Paulo (Brazil)": -2.0,
        "Praia (Cape Verde)": -1.0,
        "London (United Kingdom)": 0.0,
        "Paris (France)": 1.0,
        "Cairo (Egypt)": 2.0,
        "Moscow (Russia)": 3.0,
        "Dubai (United Arab Emirates)": 4.0,
        "Islamabad (Pakistan)": 5.0,
        "Dhaka (Bangladesh)": 6.0,
        "Bangkok (Thailand)": 7.0,
        "Beijing (China)": 8.0,
        "Tokyo (Japan)": 9.0,
        "Canberra (Australia)": 10.0,
        "Honiara (Solomon Islands)": 11.0,
        "Wellington (New Zealand)": 12.0,
    }
    START_HOUR: int = int(min(UTC_SHIFT_DICT.values())) # START_HOUR = -11


class ChatManager:
    # Dict to convert string telegram chat type to int
    CHAT_TYPE_MAPPING = {
        'private': 1,
        'group': 2,
        'supergroup': 3,
        'channel': 4
    }

    @staticmethod
    def init_chat(update):

        chat_id = update.effective_chat.id
        user_id = update.message.from_user.id
        # check and create user, if not exist

        if not DatabaseManager.is_exists("users", "user_id", user_id):

            username = update.effective_user.username
            first_name = update.effective_user.first_name
            last_name = update.effective_user.last_name
            user_language = update.effective_user.language_code
            UserManager.create_user(user_id, username, first_name, last_name, user_language)

            if update.effective_user:  # Проверяем, есть ли в обновлении callback_query
                user_language = update.effective_user.language_code
                LOG_DATABASE_CHAT.log(logging.INFO, f"User language: {user_language}")

        # create if not exist chat
        ChatManager.create_chat(chat_id, user_id, update.effective_chat.type)
        # DatabaseManager.link_entities_in_relation_table('users_chats','user_id', user_id,'chat_id', chat_id)

    @staticmethod
    def convert_chat_type_to_int(chat_type):
        return ChatManager.CHAT_TYPE_MAPPING.get(chat_type, 1)  # default value - 'private'

    @staticmethod
    def chat_exists(chat_id):
        """
        Checks if a chat already exists in the database.

        Args:
            chat_id (int): The Telegram chat ID.

        Returns:
            bool: True if the chat exists, False otherwise.
        """
        query = "SELECT 1 FROM chats WHERE chat_id = ?"
        result = DatabaseHelper.safe_execute_query(query, (chat_id,))
        return bool(result)

    @staticmethod
    def create_chat(chat_id, user_id, chat_type='private'):
        """
        Creates a new chat in the database.

        Args:
            chat_id (int): The Telegram chat ID.
            user_id (int): The Telegram owner user ID.
            chat_type (str): chat type.
        """

        if not ChatManager.chat_exists(chat_id):
            try:
                chat_type_int = ChatManager.convert_chat_type_to_int(chat_type)
                query = "INSERT OR IGNORE INTO chats (chat_id, user_id, chat_type) VALUES (?, ?, ?)"
                DatabaseHelper.safe_execute_query(query, (chat_id, user_id, chat_type_int))
            except Exception as e:
                LOG_DATABASE_CHAT.log(logging.ERROR, f"Error creating chat: {e}")
        # else:
        #    print("Chat already exists in the database.")

    @staticmethod
    def delete_chat(chat_id):
        """
        Deletes a chat from the database.

        Args:
            chat_id (int): The Telegram chat ID to be deleted.
        """

        if ChatManager.chat_exists(chat_id):
            try:
                query = "DELETE FROM chats WHERE chat_id = ?"
                DatabaseHelper.safe_execute_query(query, (chat_id,))
            except Exception as e:
                LOG_DATABASE_CHAT.log(logging.ERROR, f"Error deleting chat: {e}")
        # else:
        #    print("Chat does not exist in the database.")


    @staticmethod
    def update_last_message_time(chat_id):
        """
        updates last message time

        Args:
            chat_id (int): chat ID for update
        """
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")  # format date time
        query = """
            UPDATE chats
            SET date = ?
            WHERE chat_id = ?
        """
        DatabaseHelper.safe_execute_query(query, (current_time, chat_id))


    @staticmethod
    def clear_last_message_time(chat_id):
        """
        Clears last message time.

        Args:
            chat_id (int): Chat ID for update.
        """
        query = """
            UPDATE chats
            SET date = NULL
            WHERE chat_id = ?
        """
        DatabaseHelper.safe_execute_query(query, (chat_id,))

    @staticmethod
    async def get_available_chats_by_type(selected_chat_types: int | list = (1, 2, 3, 4)):
        if isinstance(selected_chat_types, int):
            selected_chat_types = [selected_chat_types]  # Преобразуем одиночное значение в список

        # Step 1: Get all chats
        chats = await ChatManager.get_all_chats_by_type(selected_chat_types)

        #Check if chat is active
        if chats:

            # DEBUG MODE - return all chats without rules
            if util_config['debug_mode']:
                return [chat['chat_id'] for chat in chats]  # Return only chat IDs if in debug mode

            server_time = datetime.utcnow()
            available_chat_list = []
            for chat in chats:

                chat_id = chat['chat_id']
                timezone_offset = chat['timezone']  # in hours
                post_interval = chat['post_interval']  # in minutes

                # default value if we cannot read from DB
                last_message_time = ChatManager.datetime_checker(chat_id, chat['date'])
                if last_message_time is None:
                    last_message_time = server_time - timedelta(hours=2)  # Fallback to current time if parsing fails

                # Step 3: Calculate the user's local time
                user_hours = ChatManager.timezone_checking(chat_id, timezone_offset)
                user_minutes = ChatManager.post_interval_checking(chat_id, post_interval)

                user_local_time = server_time + timedelta(hours=user_hours)

                # Step 4: Check if the user's local time falls within the allowed communication window
                if not (8 <= user_local_time.hour <= 22):
                    LOG_DATABASE_CHAT.log(logging.INFO, f'Chat {chat_id} rejected cause it is late messaging')
                    continue  # Do not send a message outside the 8 AM to 10 PM

                # Step 5: Determine the elapsed time since the last message was sent
                elapsed_time_since_last_message = server_time - last_message_time

                # Step 6: Check if the elapsed time is greater than or equal to the allowed messaging frequency
                if elapsed_time_since_last_message < timedelta(minutes=user_minutes):
                    LOG_DATABASE_CHAT.log(logging.WARNING, f'Chat {chat_id} must be rejected cause high frequency of sending messages')
                    # continue  # Do not send a message if the interval since the last message is too short

                available_chat_list.append(chat_id)

            return available_chat_list
        return []

    @staticmethod
    async def get_chats_for_pocket_erasing(selected_chat_types: int | list = (1, 2, 3, 4)):
        if isinstance(selected_chat_types, int):
            selected_chat_types = [selected_chat_types]  # Преобразуем одиночное значение в список

        chats = await ChatManager.get_all_chats_by_type(selected_chat_types)

        if chats:
            server_time = datetime.utcnow()
            available_chat_list = []
            for chat in chats:

                chat_id = chat['chat_id']
                timezone_offset = chat['timezone']  # in hours

                user_hours = ChatManager.timezone_checking(chat_id, timezone_offset)

                user_local_time = server_time + timedelta(hours=user_hours)
                last_pocket_erasing_time = await DatabaseManager.get_single_field_value("chats",
                                                                                        "last_pocket_erasing_date",
                                                                                        "chat_id", chat_id)
                last_pocket_erasing_time = ChatManager.datetime_checker(chat_id, last_pocket_erasing_time)
                if last_pocket_erasing_time is None or last_pocket_erasing_time.day < user_local_time.day:
                    available_chat_list.append(chat_id)

            return available_chat_list
        return []

    @staticmethod
    def datetime_checker(chat_id, date_time) -> datetime | None:
        if date_time is None:
            return None
        current_date_time = datetime.utcnow() - timedelta(hours=2)
        try:
            current_date_time = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            LOG_DATABASE_CHAT.log(logging.ERROR,
                                  f"Error parsing date for chat {chat_id}. Using server time as fallback.")
        except Exception as e:
            LOG_DATABASE_CHAT.log(logging.ERROR, f"Error '{e}' while parsing date for chat {chat_id}. "
                                                 f"Using server time as fallback.")
        return current_date_time

    @staticmethod
    def timezone_checking(chat_id, timezone_offset) -> int:
        try:
            user_hours = int(timezone_offset)
            if not -24 <= user_hours <= 24:
                raise ValueError("Timezone offset out of range")
        except (ValueError, TypeError) as e:
            LOG_DATABASE_CHAT.log(logging.ERROR, f"Invalid value for time zone. Reason: '{e}'.")
            user_hours = 0
            DatabaseManager.update_or_insert_field("chats", "timezone", user_hours,
                                                   "chat_id", chat_id)
        return user_hours

    @staticmethod
    def post_interval_checking(chat_id, timezone_offset) -> int:
        try:
            post_interval = int(timezone_offset)
            if post_interval <= 0:
                raise ValueError("Post interval offset out of range")
        except (ValueError, TypeError) as e:
            LOG_DATABASE_CHAT.log(logging.ERROR, f"Invalid value for post interval. Reason: '{e}'.")
            post_interval = 60
            DatabaseManager.update_or_insert_field("chats", "post_interval", post_interval,
                                                   "chat_id", chat_id)
        return post_interval

    @staticmethod
    async def get_chats_and_shifts(selected_chat_types: int | list = (1, 2, 3, 4)) -> list[tuple]:
        if isinstance(selected_chat_types, int):
            selected_chat_types = [selected_chat_types]

        chats = await ChatManager.get_all_chats_by_type(selected_chat_types)
        if chats:
            return [(chat['chat_id'], chat['timezone']) for chat in chats]
        return []

    @staticmethod
    async def get_all_chats_by_type(selected_chat_types: int | list = (1, 2, 3, 4)):
        if isinstance(selected_chat_types, int):
            selected_chat_types = [selected_chat_types]  # Преобразуем одиночное значение в список

        query = "SELECT chat_id, chat_type, date, timezone, post_interval FROM chats"
        if selected_chat_types is not None:
            chat_type_str = ", ".join([str(chat_type) for chat_type in selected_chat_types])
            query += f" WHERE chat_type IN ({chat_type_str})"
        query += " ORDER BY date ASC"

        result = DatabaseHelper.safe_execute_query(query)
        chat_list = []

        if result:
            for chat in result:
                chat_data = {
                    'chat_id': chat[0],
                    'chat_type': chat[1],
                    'date': chat[2],
                    'timezone': chat[3],
                    'post_interval': chat[4]
                }
                chat_list.append(chat_data)

        return chat_list

    @staticmethod
    async def can_send_message(chat_id):
        # Step 1: Retrieve current server time
        server_time = datetime.utcnow()

        try:
            # Step 2: Get the user's timezone offset and messaging frequency from the database
            chat_info = await ChatManager.get_chat_time_data(chat_id)
            timezone_offset = chat_info['timezone']  # in hours
            post_interval = chat_info['post_interval']  # in minutes
            last_message_time = datetime.strptime(chat_info['date'], "%Y-%m-%d %H:%M:%S")

            if last_message_time is None:
                return True

            # Step 3: Calculate the user's local time
            user_local_time = server_time + timedelta(hours=timezone_offset)

            # Step 4: Check if the user's local time falls within the allowed communication window
            if not (8 <= user_local_time.hour < 22):
                return False  # Do not send a message outside of 8 AM to 10 PM

            # Step 5: Determine the elapsed time since the last message was sent
            elapsed_time_since_last_message = server_time - last_message_time

            # Step 6: Check if the elapsed time is greater than or equal to the allowed messaging frequency
            if elapsed_time_since_last_message < timedelta(minutes=post_interval):
                return False  # Do not send a message if the interval since the last message is too short
        except Exception as e:
            LOG_DATABASE_CHAT.log(logging.ERROR, f'Error in can_send_message function {e}')
            return False  # Error occurred, do not send a message
        return True  # All conditions met, message can be sent

    @staticmethod
    async def get_chat_time_data(chat_id):
        query = "SELECT date,timezone, post_interval FROM chats WHERE chat_id = ?"
        result = DatabaseHelper.safe_execute_query(query, (chat_id,))
        if result:
            # Assuming the query returns only one row
            last_message_time, timezone, post_interval = result[0]
            return {'date': last_message_time, 'timezone': timezone, 'post_interval': post_interval}
        else:
            return None

    @staticmethod
    def get_chat_language(chat_id):
        """
        Retrieves the language preference of the user.

        Args:
            chat_id (int): The chat ID associated with the user.

        Returns:
            int: The language preference of the user. Defaults to 1 if not set.
        """
        query = """
            SELECT language FROM chats
            WHERE chat_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (chat_id,))
        if result and result[0] and result[0][0] is not None:
            return result[0][0]
        else:
            return 1  # Default value for language

    @staticmethod
    def set_chat_language(chat_id, language):
        """
        Sets the language for a chat. If the language is provided as a name, converts it to the corresponding ID.

        Args:
            chat_id (int): The ID of the chat.
            language (str or int): The name or ID of the language.
        """
        # Convert language name to ID if necessary
        if isinstance(language, str):
            language_id = TranslationManager.get_language_id(language)
        else:
            language_id = language

        # Update the chat's language
        query = "UPDATE chats SET language = ? WHERE chat_id = ?"
        DatabaseHelper.safe_execute_query(query, (language_id, chat_id))

    @staticmethod
    def get_chat_style(chat_id):
        """
        Retrieves the style preference of the user.

        Args:
            chat_id (int): The chat ID associated with the user.

        Returns:
            int: The style preference of the user. Defaults to 1 if not set.
        """
        query = """
            SELECT style FROM chats
            WHERE chat_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (chat_id,))
        if result and result[0] and result[0][0] is not None:
            return int(result[0][0])
        else:
            return 1  # Default value for style

    @staticmethod
    def set_chat_style(chat_id, style):
        """
        Sets the style for a chat. If the style is provided as a name, converts it to the corresponding ID.

        Args:
            chat_id (int): The ID of the chat.
            style (str or int): The name or ID of the style.
        """
        # Convert style name to ID if necessary
        if isinstance(style, str):
            style_id = TranslationManager.get_style_id_by_name(style)
            if style_id is None:
                LOG_DATABASE_CHAT.log(logging.WARNING, f"Style '{style}' not found.")
                return
        else:
            style_id = style

        # Update the chat's style
        query = "UPDATE chats SET style = ? WHERE chat_id = ?"
        DatabaseHelper.safe_execute_query(query, (style_id, chat_id))


    @staticmethod
    def get_chat_timezone(chat_id):
        """
        Retrieves the timezone of the chat.

        Args:
            chat_id (int): The chat ID.

        Returns:
            int: The timezone of the chat. Defaults to 0 if not set.
        """
        from app.bot.states.state import State

        query = """
            SELECT timezone FROM chats
            WHERE chat_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (chat_id,))
        if result and result[0] and (result[0][0] is not None) and (result[0][0] != State.FALLBACK):
            return result[0][0]
        return None  # Default timezone

    @staticmethod
    def set_chat_timezone(chat_id, timezone):
        """
        Sets the timezone for a chat.

        Args:
            chat_id (int): The ID of the chat.
            timezone (int | str): The timezone to set for the chat.
        """
        # Update the chat's timezone
        query = "UPDATE chats SET timezone = ? WHERE chat_id = ?"
        try:
            DatabaseHelper.safe_execute_query(query, (timezone, chat_id))
        except Exception as e:
            LOG_DATABASE_CHAT.log(logging.ERROR, f"Error setting timezone for chat {chat_id}: {e}")


    @staticmethod
    def set_llm_model(chat_id, llm_model: str):

        # Ensure llm model to be a string parameter
        if not isinstance(llm_model, str):
            LOG_DATABASE_CHAT.raise_exception_with_log(ValueError("LLM Model must be of type string!"))

        query = "UPDATE chats SET model = ? WHERE chat_id = ?"
        try:
            DatabaseHelper.safe_execute_query(query, (llm_model, chat_id))
        except Exception as e:
            LOG_DATABASE_CHAT.log(logging.ERROR, f"Error setting LLM model for chat {chat_id}: {e}")

    @staticmethod
    def get_llm_model(chat_id) -> str | None:
        from app.bot.states.state import State

        query = "SELECT model FROM chats WHERE chat_id = ?"
        result = DatabaseHelper.safe_execute_query(query, (chat_id,))
        if result and result[0] and (result[0][0] is not None) and (result[0][0] != State.FALLBACK):
            return result[0][0]
        else:
            LOG_DATABASE_CHAT.raise_exception_with_log(ValueError("No model is chosen"))
        return None


if __name__ == "__main__":
    ChatManager.clear_last_message_time(466001259)
    all_chats = asyncio.run(ChatManager.get_available_chats_by_type(1))
    print(all_chats)


