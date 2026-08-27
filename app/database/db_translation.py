from app.database.db_helper import DatabaseHelper
from app.database.db_post import PostManager

from app.misc import log_helper

LOG = log_helper.LogHelper(__name__, "db_translation")

#Languages
EN = 1
ZH = 2
ES = 3
AR = 4
ID = 5
PT = 6
FR = 7
JA = 8
RU = 9
DE = 10

# post_styles data
CASUAL_STYLE = 1
CONCISE_STYLE = 2
PROFESSIONAL_STYLE = 3
ENTHUSIASTIC_STYLE = 4
HUMOROUS_STYLE = 5
EMPATHETIC_STYLE = 6
SARCASTIC_STYLE = 7


class TranslationManager:

    def process_input_fields(func):
        def wrapper(self, *args, **kwargs):
            # input fields processing
            for arg_name, arg_value in kwargs.items():
                # if arg_name ends with "_id" или "_name", then replace it with "d_"
                if isinstance(arg_value, str) and (arg_name.endswith("_id") or arg_name.endswith("_name")):
                    kwargs[arg_name] = "d_" + arg_value


    @staticmethod
    def get_translation_command(chat_id):
        """
        Retrieves translation settings for a given chat and constructs a system command for ChatGPT.
        Uses default values if language or style are not set.

        Args:
            chat_id (int): The ID of the chat.

        Returns:
            str: A system command for ChatGPT based on the chat's language and style preferences.
        """
        # get language and style
        language_query = """
            SELECT COALESCE(language, 1) FROM chats WHERE chat_id = ?
        """
        style_query = """
            SELECT COALESCE(style, 1) FROM chats WHERE chat_id = ?
        """
        language_id = DatabaseHelper.safe_execute_query(language_query, (chat_id,))
        style_id = DatabaseHelper.safe_execute_query(style_query, (chat_id,))

        # construct system command
        if language_id and style_id:
            language_name_query = """
                SELECT language_code FROM languages WHERE language_id = ?
            """
            style_description_query = """
                SELECT description FROM translation_styles WHERE style_id = ?
            """
            language_name = DatabaseHelper.safe_execute_query(language_name_query, (language_id[0][0],))
            style_description = DatabaseHelper.safe_execute_query(style_description_query, (style_id[0][0],))

            if language_name and style_description:
                # construct system command
                system_command = f"Answer only in {language_name[0][0]}. Use a {style_description[0][0]} and don't put context into your message but we aware of it"
                return system_command
            else:

                LOG.raise_exception_with_log(ValueError)
                return "answer in context language"
        else:
            LOG.raise_exception_with_log(ValueError)
            return "answer in context language"

    @staticmethod
    def get_languages(orig_name=False):
        """
        Retrieves a list of language names from the database, either in original language or in English.
        :param orig_name: if True, returns original names, otherwise returns English names.
        :return: list of language names
        """
        if orig_name:
            query = "SELECT name_orig FROM languages"
        else:
            query = "SELECT name FROM languages"

        results = DatabaseHelper.safe_execute_query(query)

        languages = [result[0] for result in results]
        return languages

    @staticmethod
    def get_languages_codes():
        """
        Retrieves a list of language names from the database.
        :return: list of language names
        """

        query = "SELECT language_code FROM languages"

        results = DatabaseHelper.safe_execute_query(query)

        languages = [result[0] for result in results]
        return languages

    @staticmethod
    def get_styles():

        query = "SELECT style_name FROM translation_styles"
        results = DatabaseHelper.safe_execute_query(query)

        styles = [result[0] for result in results]
        return styles

    @staticmethod
    def get_language_id(language):
        """
        Retrieves the ID of a language by its name.

        Args:
            language (str): The name of the language.

        Returns:
            int: The ID of the language, or None if not found.
        """
        query = "SELECT language_id FROM languages WHERE language_code = ? OR name = ? OR name_orig = ?"
        result = DatabaseHelper.safe_execute_query(query, (language, language, language))
        return result[0][0] if result else 1

    @staticmethod
    def get_language_name(identifier, orig_name=False):
        """
        Retrieves the name of a language by its code or short name, in original language or English.

        Args:
            identifier (str): The code or short name of the language.
            orig_name (bool): If True, returns the original name of the language. Otherwise, returns the English name.

        Returns:
            str: The name of the language in the requested format, or None if not found.
        """
        # Определяем, какое поле выбирать в зависимости от флага orig_name
        field_to_select = "name_orig" if orig_name else "name"

        # SQL запрос на поиск языка по коду или короткому имени
        query = f"SELECT {field_to_select} FROM languages WHERE language_code = ? OR language_id = ? LIMIT 1"

        # Выполняем запрос к базе данных
        result = DatabaseHelper.safe_execute_query(query, (identifier, identifier))

        # Возвращаем результат, если он существует
        return result[0][0] if result else 1 # default value

    @staticmethod
    def get_style_id_by_name(style_name):
        """
        Retrieves the ID of a style by its name.

        Args:
            style_name (str): The name of the style.

        Returns:
            int: The ID of the style, or None if not found.
        """
        query = "SELECT style_id FROM translation_styles WHERE style_name = ?"
        result = DatabaseHelper.safe_execute_query(query, (style_name,))
        return int(result[0][0]) if result else None

    @staticmethod
    def is_translation_exists(post_id, language_id, style_id):
        # SQL query to check if a translation exists
        query = """
            SELECT 1 FROM translations 
            WHERE post_id = ? AND language_id = ? AND style_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (post_id, language_id, style_id))
        return bool(result)

    @staticmethod
    def get_language_code_by_id(language_id=1):
        # SQL query to get language by ID
        query = "SELECT language_code FROM languages WHERE language_id = ?"
        result = DatabaseHelper.safe_execute_query(query, (language_id,))
        return result[0][0] if result else 1

    @staticmethod
    def get_style_id(style_identifier):
        if isinstance(style_identifier, str):
            query = "SELECT style_id FROM translation_styles WHERE style_name = ?"
        elif isinstance(style_identifier, int):
            query = "SELECT style_id FROM translation_styles WHERE style_id = ?"
        else:
            raise ValueError("style_identifier must be either a string (style name) or an integer (style ID)")

        result = DatabaseHelper.safe_execute_query(query, (style_identifier,))
        return result[0][0] if result else 1

    @staticmethod
    def get_style_name_by_id(style_id=1):
        # SQL query to get style by ID
        query = "SELECT style_name FROM translation_styles WHERE style_id = ?"
        result = DatabaseHelper.safe_execute_query(query, (style_id,))
        return result[0][0] if result else 1
    @staticmethod
    def get_style_description_by_id(style_id=1):
        query = "SELECT description FROM translation_styles WHERE style_id = ?"
        result = DatabaseHelper.safe_execute_query(query, (style_id,))
        return result[0][0] if result else None

    @staticmethod
    async def get_existing_translation(post_id, language_id, style_id):
        # SQL query to retrieve an existing translation
        query = """
            SELECT title, content FROM translations 
            WHERE post_id = ? AND language_id = ? AND style_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (post_id, language_id, style_id))
        if result:
            # return as cortège
            return result[0][0], result[0][1]
        else:
            # NONE if don't find
            return None, None

    @staticmethod
    def create_translation(post_id, language_id, style_id, title, content):
        # SQL query to insert a new translation into the database
        query = """
            INSERT OR IGNORE INTO translations (post_id, language_id, style_id, title, content)
            VALUES (?, ?, ?, ?, ?)
        """
        DatabaseHelper.safe_execute_query(query, (post_id, language_id, style_id, title, content))

if __name__ == '__main__':
    # Example usage
    result = TranslationManager.get_language_name(ZH,True)
    print(result)