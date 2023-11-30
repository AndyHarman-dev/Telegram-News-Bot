import sqlite3
import json
from config import config
from user import User
from misc.log_helper import LogHelper, logging

TG_DB_LOG = LogHelper(__name__, "Database thread")

# Database API for interacting with SQLite database
class DatabaseAPI:
    """
    Initializes a new instance of the class with the specified database name.

    Parameters:
        db_name (str): The name of the database to connect to.

    Returns:
        None
    """

    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def __del__(self):
        self.conn.close()

    """
    Creates a table named 'users' in the database if it does not already exist.

    Parameters:
        None

    Returns:
        None
    """

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                user_name TEXT NOT NULL,
                has_pro BOOLEAN NOT NULL,
                preferences TEXT NOT NULL
            )
        """)

    """
    Inserts a new user into the database.

    Parameters:
        user_id (str): The unique identifier for the user.
        user_name (str): The name of the user.
        has_pro (bool): Indicates whether the user has a pro account.
        preferences (dict): A dictionary containing the user's preferences.

    Returns:
        None
    """

    def insert_user(self, user_id, user_name, has_pro: bool, preferences):
        preferences_json = json.dumps(preferences)
        self.cursor.execute("""
            INSERT INTO users (user_id, user_name, has_pro, preferences)
            VALUES (?, ?, ?, ?)
        """, (user_id, user_name, has_pro, preferences_json))
        self.conn.commit()

    """
    Retrieves a user from the database based on the given user ID.

    Parameters:
        user_id (int): The ID of the user to retrieve.

    Returns:
        tuple or None: A tuple containing the user's ID, name, pro status, and preferences if the user is found,
                       None otherwise.
    """

    def get_user(self, user_id) -> User:
        self.cursor.execute("""
            SELECT * FROM users WHERE user_id = ?
        """, (user_id,))
        user = self.cursor.fetchone()
        if user is not None:
            user_id, user_name, has_pro, preferences_json = user
            preferences = json.loads(preferences_json)
            return User(user_id, user_name, has_pro, preferences)
        else:
            raise ValueError(f"User with ID {user_id} not found")

    """
    Check if a user exists in the database.

    Parameters:
        user_id (int): The id of the user to check.

    Returns:
        bool: True if the user exists in the database, False otherwise.
    """

    def user_exists(self, user_id):
        self.cursor.execute("""
            SELECT COUNT(*) FROM users WHERE user_id = ?
        """, (user_id,))
        count = self.cursor.fetchone()[0]
        return count > 0

    """
    Updates user information in the database.

    Parameters:
        user_id (int): The ID of the user to update.
        user_name (str, optional): The new name for the user. Defaults to None.
        has_pro (bool, optional): Indicates whether the user has a pro account. Defaults to None.
        preferences (dict, optional): The new preferences for the user. Defaults to None.

    Returns:
        None
    """

    def update_user(self, user_id, user_name=None, has_pro=None, preferences=None):
        if user_name is not None:
            self.cursor.execute("""
                UPDATE users SET user_name = ? WHERE user_id = ?
            """, (user_name, user_id))
        if has_pro is not None:
            self.cursor.execute("""
                UPDATE users SET has_pro = ? WHERE user_id = ?
            """, (has_pro, user_id))
        if preferences is not None:
            preferences_json = json.dumps(preferences)
            self.cursor.execute("""
                UPDATE users SET preferences = ? WHERE user_id = ?
            """, (preferences_json, user_id))
        self.conn.commit()

    """
    Delete a user from the database.

    Args:
        user_id (int): The ID of the user to delete.

    Returns:
        None
    """

    def delete_user(self, user_id):
        self.cursor.execute("""
            DELETE FROM users WHERE user_id = ?
        """, (user_id,))
        self.conn.commit()


# TODO : Add database path to the config.txt file
DATABASE_API = DatabaseAPI(config.CONFIG_DICT['database_path'])


# Database class for user-friendly interaction with the database
class Database:

    """
    Registers a new user if the user does not already exist in the database.

    Args:
        user_id (int): The ID of the user.
        user_name (str): The name of the user.
        has_pro (bool): Indicates whether the user has a pro account or not.
        preferences (dict): The user's preferences.

    Returns:
        None
    """
    @staticmethod
    def register_user_if_not_exists(user_id, user_name, has_pro: bool, preferences):
        if not DATABASE_API.user_exists(user_id):
            DATABASE_API.insert_user(user_id, user_name, has_pro, preferences)

    @staticmethod
    def get_user_if_exists(user_id) -> (bool, User):
        try:
            return True, DATABASE_API.get_user(user_id)
        except ValueError as e:
            TG_DB_LOG.log(logging.ERROR, str(e))
            return (False, User())

    @staticmethod
    def update_user(user_id, user_name=None, has_pro=None, preferences=None):
        DATABASE_API.update_user(user_id, user_name, has_pro, preferences)
