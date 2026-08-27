import asyncio
from app.database.db_hashtag import HashtagManager
from app.database.db_helper import DatabaseHelper, DatabaseModel, DatabaseManager
from app.database.db_tariff import TariffManager

#from app.llm.models import llm_fast

class UserManager():
    @staticmethod
    def create_user(user_id, username, first_name=None, last_name=None, language_code=None):
        """
        Creates a new user in the database.

        Args:
            user_id (int): The Telegram user ID.
            username (str): The username of the user.
            first_name (str): The first name of the user.
            last_name (str): The last name of the user.
        """

        # List of supported language codes
        supported_language_codes = ["en", "zh", "es", "ar", "id", "pt", "fr", "ja", "ru", "de"]
        # Check if the user's language code is supported
        if not language_code in supported_language_codes:
            language_code = "en"

        query = """
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, language)
                VALUES (?, ?, ?, ?, ?)
            """
        DatabaseHelper.safe_execute_query(query, (user_id, username, first_name, last_name, language_code))

        # create user usage record
        TariffManager.create_user_usage(user_id)

    @staticmethod
    def get_all_users():
        query = "SELECT * FROM users"

        return DatabaseHelper.safe_execute_query(query)

    @staticmethod
    def get_chats_user(chat_id):
        query = """
            SELECT owner_user_id FROM chats
            WHERE chat_id = ?
        """
        users = DatabaseHelper.safe_execute_query(query, (chat_id,))
        return users[0] if users else None


    @staticmethod
    def get_user_language(chat_id):
        """
        Retrieves the language preference of the user.

        Args:
            chat_id (int): The chat ID associated with the user.

        Returns:
            int: The language preference of the user. Defaults to 1 if not set.
        """
        query = """
            SELECT language FROM users 
            WHERE user_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (chat_id,))
        if result and result[0] and result[0][0] is not None:
            return result[0][0]
        else:
            return 1  # Default value for language

    @staticmethod
    def get_user_style(chat_id):
        """
        Retrieves the style preference of the user.

        Args:
            chat_id (int): The chat ID associated with the user.

        Returns:
            int: The style preference of the user. Defaults to 1 if not set.
        """
        query = """
            SELECT style FROM users 
            WHERE user_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (chat_id,))
        if result and result[0] and result[0][0] is not None:
            return result[0][0]
        else:
            return 1  # Default value for style

    @staticmethod

    async def predict_user_age_and_gender(user_id):
        """
        Asynchronously predicts the user's age and gender based on the user's hashtags.

        Args:
            user_id: The ID of the user for whom the prediction is to be made.

        Returns:
            Tuple[int, int]: A tuple containing the predicted age and gender as integers.
        """
        hashtags = HashtagManager.get_chat_hashtags(user_id)
        hashtags_str = HashtagManager.get_hashtags_names_by_id(hashtags)

        #predict age
        prompt = f"Based on the following hashtags: {hashtags_str}, estimate the user's age. Please provide an approximate age as a single number. Don't write words"
        age, *_ = await llm_fast.send_request( prompt, common_args={
                "messages": [{"role": "system",
                              "content": "Based on the following hashtags estimate the user's age. Please provide an approximate age as a single number. Don't write words"}],
                "max_tokens": 10
        })
        #predict gender
        prompt = f"Based on the following hashtags: {hashtags_str}, estimate the user's gender. Please provide: 'Male' or 'Female' as a single word. Don't write words"
        gender, *_ = await llm_fast.send_request( prompt, common_args={
                "messages": [{"role": "system",
                              "content": "Based on the following hashtags estimate the user's gender. Please provide: 'Male' or 'Female' as a single word. Don't write words"}],
                "max_tokens": 10
        })
        try:
            age = int(age)
        except ValueError:
            age = 0
        except Exception as e:
            return 0, 0

        if gender == 'Male':
            gender_int = 2
        elif gender == 'Female':
            gender_int = 1
        else:
            gender_int = 0

        return age, gender_int

        #response = await llm_fast.send_request(prompt)
        print(age, gender)

    @staticmethod
    def set_user_blocked(user_id: int, is_blocked: bool = False):
        query = f"UPDATE users SET is_blocked = {int(is_blocked)} WHERE user_id = ?"
        DatabaseHelper.safe_execute_query(query, (user_id,))


if __name__ == '__main__':
    #asyncio.run(UserManager.predict_user_age_and_gender(466001259) )
    #UserManager.set_user_blocked(1252909852, False)
    pass