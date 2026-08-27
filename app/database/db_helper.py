import asyncio

import aiosqlite
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor

import sqlite3


class DatabaseHelper:
    # database static path
    db_path = Path(__file__).resolve().parent.parent.parent / 'smm_data_base.db'

    # database lock for concurrent access to the database
    db_lock = asyncio.Lock()

    # Sync methods to read from database ===================
    @staticmethod
    def create_connection():
        return sqlite3.connect(DatabaseHelper.db_path, timeout=60)

    @staticmethod
    def safe_execute_query(query: object, params: object = (), second_query: object = None) -> object:
        with DatabaseHelper.create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()  # Save the result of the first query
            if second_query:
                cursor.execute(second_query)
                return cursor.fetchone()  # Return the result of the second query
            return result  # Return the result of the first query if no second query

    @staticmethod
    def safe_execute_query_dict(query: object, params: object = ()) -> object:
        """
        Execute a query and return the result as a list of dictionaries, where the keys are the column names.
        :param query: SQL query
        :param params: Parameters for SQL query (default is an empty tuple)
        :return: Result of the query as a list of dictionaries
        """
        with DatabaseHelper.create_connection() as conn:
            conn.row_factory = sqlite3.Row  # Use row_factory to return data as dictionaries
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            return [dict(row) for row in result]  # Convert each row to a dictionary

    # Async methods for write to database ==============

    @staticmethod
    async def create_async_connection():
        return await aiosqlite.connect(DatabaseHelper.db_path)

    @staticmethod
    async def safe_async_execute_query(query: object, params: object = (), second_query: object = None) -> object:
        async with DatabaseHelper.db_lock:  # Use the mutex to lock execution
            async with DatabaseHelper.create_async_connection() as conn:
                cursor = await conn.execute(query, params)
                result = await cursor.fetchall()  # Save the result of the first query
                if second_query:
                    await cursor.execute(second_query)
                    return await cursor.fetchone()  # Return the result of the second query
                return result  # Return the result of the first query if there is no second query

    @staticmethod
    async def safe_execute_query_async(query, params=()):
        async with aiosqlite.connect(DatabaseHelper.db_path) as conn:
            cursor = await conn.execute(query, params)
            data = await cursor.fetchall()
            await cursor.close()
            return data

    """
    async def run_db_query(query, *args):
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            conn = sqlite3.connect('smm_data_base.db')
            result = await loop.run_in_executor(pool, conn.execute, query, args)
            conn.commit()
            conn.close()
            return result

    @staticmethod
    async def safe_execute_query_async_write(query, params=()):
        return await DatabaseHelper.run_db_query(query, *params)
    """
    @staticmethod
    def get_last_insert_id():
        # Get the last inserted ID
        return DatabaseHelper.safe_execute_query("SELECT last_insert_rowid()")[0][0]


class DatabaseModel:
    # Virtual attributes to be defined in child classes
    table_name = "my_table"
    primary_key = "my_id"
    fields = ["my", "table", "fields"]
    hashtag_table = "my_hashtags_table"
    id = None

    def __init__(self, **kwargs):
        # set primary key and other fields
        for field in [self.primary_key] + self.fields:
            setattr(self, field, kwargs.get(field, None))


    def is_exists(self):
        """
        Checks if a record exists in the database.

        Returns:
            bool: True if a record exists, False otherwise.
        """
        primary_key_value = getattr(self, self.__class__.primary_key)
        query = f"SELECT 1 FROM {self.__class__.table_name} WHERE {self.__class__.primary_key} = ?"
        return bool(DatabaseHelper.safe_execute_query(query, (primary_key_value,)))

    def save(self):
        if self.is_exists():
            self._update()
        else:
            self.id = self._create()  # Save the returned ID
            setattr(self, self.primary_key, self.id)

    """
        def _create(self):
            # Prepare and execute INSERT query
            columns = ', '.join(self.fields)
            placeholders = ', '.join('?' for _ in self.fields)
            values = [getattr(self, field) for field in self.fields]
            query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
    
            # Execute query and get the last inserted ID
            last_id = DatabaseHelper.safe_execute_query(query, values)#, "SELECT last_insert_rowid()")[0][0]
            setattr(self, self.primary_key, last_id)
    
            return last_id  # Return the ID
    """
    def _create(self):
        # Prepare and execute INSERT query
        columns = ', '.join(self.fields)
        placeholders = ', '.join('?' for _ in self.fields)
        values = [getattr(self, field) for field in self.fields]
        insert_query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        last_id_query = "SELECT last_insert_rowid()"

        with DatabaseHelper.create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(insert_query, values)
            conn.commit()  # Commit the insert operation
            cursor.execute(last_id_query)  # Get the last inserted id
            last_id = cursor.fetchone()[0]

        return last_id  # Return the ID


    def _update(self):
        # Prepare and execute UPDATE query
        set_clause = ', '.join(f"{field} = ?" for field in self.fields)
        values = [getattr(self, field) for field in self.fields] + [getattr(self, self.primary_key)]
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE {self.primary_key} = ?"
        DatabaseHelper.safe_execute_query(query, values)


class DatabaseManager:

    @staticmethod
    def from_db_row(table_fields, row):
        """
        Maps a database row to a dictionary using the provided table fields.

        Args:
            table_fields (list): A list of fields for the table.
            row (tuple): A row from the database query.

        Returns:
            dict: A dictionary representing the row data.
        """
        if len(row) != len(table_fields):
            raise ValueError("Row length does not match number of fields")
        return dict(zip(table_fields, row))

    @staticmethod
    def update_or_insert_field(table_name, field_name, value, primary_key=None, primary_key_value=None):
        """
        Update or insert a field in a table with a given value.

        Args:
            table_name (str): The name of the table.
            field_name (str): The field name to update or insert.
            value: The value to set for the field.
            primary_key (str, optional): The primary key field name, for updating existing records.
            primary_key_value: The value of the primary key, for updating existing records.
        """
        if primary_key and primary_key_value:
            # Update existing record
            query = f"UPDATE {table_name} SET {field_name} = ? WHERE {primary_key} = ?"
            params = (value, primary_key_value)
        else:
            # Insert new record
            query = f"INSERT INTO {table_name} ({field_name}) VALUES (?)"
            params = (value,)

        with DatabaseHelper.create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

    @staticmethod
    async def get_single_field_value(table_name, target_field, filter_field, filter_value):
        """
        Retrieves a single field value from a specified table based on a filter field and its value.

        Args:
            table_name (str): The name of the table to query.
            target_field (str): The field whose value you want to retrieve.
            filter_field (str): The field to filter on.
            filter_value: The value to match in the filter field.

        Returns:
            The value of the target field for the matched record, or None if no record matches.
        """
        query = f"SELECT {target_field} FROM {table_name} WHERE {filter_field} = ? LIMIT 1"
        result = DatabaseHelper.safe_execute_query(query, (filter_value,))
        return result[0][0] if result else None

    @staticmethod
    def link_entities_in_relation_table(relation_table, first_id_name, first_id, second_id_name, second_id):
        try:
            query = f"""
                INSERT OR IGNORE INTO {relation_table} ({first_id_name}, {second_id_name})
                VALUES (?, ?)
            """
            DatabaseHelper.safe_execute_query(query, (first_id, second_id))
        except Exception as e:
            print(f"Error in link_entities_in_relation_table: {e}")

    @staticmethod
    def find_by_id(table_name, primary_key, id):
        """
        Finds a record by its ID.

        Args:
            table_name (str): The name of the table.
            primary_key (str): The primary key field name.
            id (int): The ID value to search for.

        Returns:
            dict: A dictionary representing the found record, or None if not found.
        """
        query = f"SELECT * FROM {table_name} WHERE {primary_key} = ?"
        data = DatabaseHelper.safe_execute_query(query, (id,))
        return DatabaseManager.from_db_row(table_name, data[0]) if data else None

    @staticmethod
    def is_exists(table_name, field, value):
        """
        Checks if a record exists in the database.

        Args:
            table_name (str): The name of the table.
            field (str): The field to search in.
            value: The value to search for.

        Returns:
            bool: True if a record exists, False otherwise.
        """
        query = f"SELECT 1 FROM {table_name} WHERE {field} = ?"
        return bool(DatabaseHelper.safe_execute_query(query, (value,)))

    @staticmethod
    def delete_by_id(table_name, primary_key, id):
        """
        Deletes a record by its ID.

        Args:
            table_name (str): The name of the table.
            primary_key (str): The primary key field name.
            id (int): The ID of the record to delete.
        """
        query = f"DELETE FROM {table_name} WHERE {primary_key} = ?"
        DatabaseHelper.safe_execute_query(query, (id,))

    @staticmethod
    def get_all(table_name):
        """
        Retrieves all records from a specified table.

        Args:
            table_name (str): The name of the table.

        Returns:
            list: A list of dictionaries representing each row in the table.
        """
        query = f"SELECT * FROM {table_name}"
        rows = DatabaseHelper.safe_execute_query(query)
        return [DatabaseManager.from_db_row(table_name, row) for row in rows]

    @staticmethod
    def get_all_from_table(table_name):
        """
        Retrieves all records from a specified table.

        Args:
            table_name (str): The name of the table.

        Returns:
            list: A list of tuples representing each row in the table.
        """
        query = f"SELECT * FROM {table_name}"
        return DatabaseHelper.safe_execute_query(query)

    @staticmethod
    def get_last_id(table_name):
        """
        Retrieves the ID of the last inserted record in a specified table.

        Args:
            table_name (str): The name of the table.

        Returns:
            int: The ID of the last inserted record.
        """
        query = f"SELECT last_insert_rowid()"# FROM {table_name}"
        result = DatabaseHelper.safe_execute_query(query)
        return result[0][0]


class Post(DatabaseModel):
    table_name = 'posts'
    primary_key = 'post_id'
    fields = ['channel_id', 'title', 'content', 'link', 'rating', 'popularity']
    hashtag_table = "posts_hashtags"

    def __init__(self, post_id=None, channel_id=None, title=None, content=None, link=None, rating=None, popularity=None, date=None):
        super().__init__(post_id=post_id, channel_id=channel_id, title=title, content=content, link=link, rating=rating,
                         popularity=popularity, date = date)


class User(DatabaseModel):
    table_name = 'users'
    primary_key = 'user_id'
    fields = ['login', 'email', 'password', 'name', 'age', 'gender', 'language', 'style']
    hashtag_table = "users_hashtags"

    def __init__(self, user_id=None, login=None, email=None, password=None, name=None, age=None, gender=None, language=None, style=None):
        super().__init__(user_id=user_id, login=login, email=email, password=password, name=name, age=age, gender=gender, language=language, style=style)

class Channel(DatabaseModel):
    table_name = 'channels'
    primary_key = 'channel_id'
    fields = ['channel_name', 'channel_url', 'channel_resource_type', 'channel_privacy']

    def __init__(self, channel_id=None, channel_name=None, channel_url=None, channel_resource_type=None,
                 channel_privacy=None):
        super().__init__(channel_id=channel_id, channel_name=channel_name, channel_url=channel_url,
                         channel_resource_type=channel_resource_type, channel_privacy=channel_privacy)

class Chat(DatabaseModel):
    table_name = 'chats'
    primary_key = 'chat_id'
    fields = ['chat_link', 'chat_type', 'language', 'style']

    def __init__(self, chat_id=None, chat_link=None, chat_type=None, language=None, style=None):
        super().__init__(chat_id=chat_id, chat_link=chat_link, chat_type=chat_type, language=language, style=style)



async def my_func():

    query = "SELECT hashtag_name FROM hashtags"

    # Синхронный запрос
    sync_result = DatabaseHelper.safe_execute_query(query)
    print("Синхронный результат:", sync_result)

    # Асинхронный запрос
    async_result = await DatabaseHelper.safe_execute_query_async(query)
    print("Асинхронный результат:", async_result)

if __name__ == "__main__":
    #asyncio.run( my_func() )

    print("ID последнего поста:", DatabaseManager.get_last_id('posts') )