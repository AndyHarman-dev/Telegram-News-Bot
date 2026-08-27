import logging

import app.database.db_hashtag as hashtags

from app.database.db_helper import DatabaseHelper

from pathlib import Path

from app.misc.log_helper import LogHelper
from app.misc.paths import Paths

db_helper = DatabaseHelper()
DB_INIT_LOGGER = LogHelper(__name__, "DB Init Thread")

post_styles = [
    {
        "style": "Casual",
        "description": "A friendly and informal style that's warm and inviting ",
        "example": "Hey there! Have you heard? The local park's got a brand new look! Why not check it out?"
    },
    {
        "style": "Concise",
        "description": "All about being brief and direct, stripping the message to its essential facts without fluff. ",
        "example": "Local park renovated and open now."
    },
    {
        "style": "Professional",
        "description": "Characterized by a serious, business-like tone, suitable for official updates or formal announcements. ",
        "example": "Update: The local park has been successfully renovated and is open for public use effective immediately."
    },
    {
        "style": "Enthusiastic",
        "description": "Energetic and optimistic, full of excitement. Uplifting, motivational, and encouraging. Great for positive engagement.",
        "example": "Exciting news! The local park is now renovated and open! It's time to have some fun outdoors!"
    },
    {
        "style": "Humorous",
        "description": "Incorporates humor and wit, often playful. Engages the audience in a fun manner, making content memorable.",
        "example": "Guess what? The local park's makeover is finally done! Now it's almost as pretty as me! Go take a look!"
    },
    {
        "style": "Empathetic",
        "description": "Demonstrates understanding and empathy, resonating with the audience's feelings.",
        "example": "I know we've all missed the park during its renovation. It's finally open, so let's enjoy the green space we've been longing for!"
    },
    {
        "style": "Sarcastic",
        "description": "Marked by irony or mocking, adding a sardonic twist to the message. ",
        "example": "So, the local park is finally open again. Make sure to visit before we all forget what trees look like!"
    }
]

languages = [
    {"language_code": "en", "encode": "UTF-8", "direction": "LTR", "name": "English", "name_orig": "English"},
    {"language_code": "zh", "encode": "UTF-8", "direction": "LTR", "name": "Chinese", "name_orig": "中文"},
    {"language_code": "es", "encode": "UTF-8", "direction": "LTR", "name": "Spanish", "name_orig": "Español"},
    {"language_code": "ar", "encode": "UTF-8", "direction": "RTL", "name": "Arabic", "name_orig": "العربية"},
    {"language_code": "id", "encode": "UTF-8", "direction": "LTR", "name": "Indonesian", "name_orig": "Bahasa Indonesia"},
    {"language_code": "pt", "encode": "UTF-8", "direction": "LTR", "name": "Portuguese", "name_orig": "Português"},
    {"language_code": "fr", "encode": "UTF-8", "direction": "LTR", "name": "French", "name_orig": "Français"},
    {"language_code": "ja", "encode": "UTF-8", "direction": "LTR", "name": "Japanese", "name_orig": "日本語"},
    {"language_code": "ru", "encode": "UTF-8", "direction": "LTR", "name": "Russian", "name_orig": "Русский"},
    {"language_code": "de", "encode": "UTF-8", "direction": "LTR", "name": "German", "name_orig": "Deutsch"}
]


tariffs = [
    {
        "daily_messages_quota": 5,
        "monthly_messages_quota": 15,
        "channels_quota": 0,
        "price": 0,
        "name": "Basic"
    },
    {
        "daily_messages_quota": 20,
        "monthly_messages_quota": 200,
        "channels_quota": 5,
        "price": 10,
        "name": "Standard"
    },
    {
        "daily_messages_quota": 50,
        "monthly_messages_quota": 500,
        "channels_quota": 20,
        "price": 19,
        "name": "Pro"
    },
    {
        "daily_messages_quota": 150,
        "monthly_messages_quota": 1500,
        "channels_quota": 50,
        "price": 50,
        "name": "Premium"
    },

]

# Creating a dictionary with major currencies and their conversion rates
currency_map = {
    'USD': 1.0,
    'EUR': 0.80,
    'GBP': 0.75,
    'JPY': 110.0,
    'CNY': 6.5,
    'AUD': 1.3,
    'CAD': 1.25,
    'CHF': 0.90,
    'HKD': 7.8,
    'NZD': 1.4,
    'RUB': 0.01
}


def init_tables():

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id INTEGER PRIMARY KEY,
            channel_name TEXT NOT NULL,
            channel_url TEXT UNIQUE NOT NULL,
            channel_resource_type INTEGER,
            channel_privacy INTEGER        
        )
    """)

    # all channels to parse - RSS, Sites, SMM etc.
    #         channel_resource_type INTEGER   1 - RSS 2 - Website 3 - Telegram 4 - ...
    #         channel_privacy 0 - private channel to parse news only for it's subscribers 1 - channel for all users

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS posts (
            post_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,   
            rating INTEGER CHECK(rating BETWEEN 1 AND 5),
            popularity INTEGER,
            date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
        )
    """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS posts_content (
            post_id INTEGER,
            content TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(post_id),
            PRIMARY KEY (post_id)
        )
    """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS languages (
            language_id INTEGER PRIMARY KEY,
            language_code TEXT UNIQUE NOT NULL,
            encode TEXT,
            direction TEXT,
            name TEXT,
            name_orig TEXT
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS translation_styles (
            style_id INTEGER PRIMARY KEY,
            style_name TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS translations (
            post_id INTEGER,
            language_id INTEGER,
            style_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            PRIMARY KEY (post_id, language_id, style_id),
            FOREIGN KEY (post_id) REFERENCES posts(post_id),
            FOREIGN KEY (language_id) REFERENCES languages(language_id),
            FOREIGN KEY (style_id) REFERENCES translation_styles(style_id)
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS tariffs (
            tariff_id INTEGER PRIMARY KEY,
            daily_messages_quota INTEGER,
            monthly_messages_quota INTEGER,
            channels_quota INTEGER,
            price INTEGER UNIQUE NOT NULL,
            name TEXT
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT,
            first_name TEXT,
            last_name TEXT,
            age INTEGER,
            gender INTEGER,
            language INTEGER,
            style INTEGER,
            is_blocked INTEGER DEFAULT 0
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            user_id INTEGER, 
            chat_link TEXT UNIQUE,
            chat_type INTEGER,
            master_chat_id INTEGER,
            language TEXT,
            style TEXT,
            date DATETIME DEFAULT '1970-01-01 00:00:00',
            timezone INTEGER DEFAULT 0,
            post_interval INTEGER DEFAULT 60,
            model TEXT,

            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS seen_chats_posts (
          chat_id INTEGER,
          post_id INTEGER,
          PRIMARY KEY (chat_id, post_id),
          FOREIGN KEY (chat_id) REFERENCES chats(chat_id),
          FOREIGN KEY (post_id) REFERENCES posts(post_id)
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS users_usages (
            user_id INTEGER PRIMARY KEY,
            tariff_id INTEGER DEFAULT 1,
            daily_messages_sent INTEGER DEFAULT 0,
            monthly_messages_sent INTEGER DEFAULT 0,
            channels_quota INTEGER DEFAULT 0,   
            balance INTEGER DEFAULT 0,
            activation_date DATE,
            monthly_news_gathered INTEGER DEFAULT 0,
            monthly_images_generated INTEGER DEFAULT 0,
            last_activity DATETIME DEFAULT '1970-01-01 00:00:00',
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (tariff_id) REFERENCES tariffs(tariff_id)  
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS users_action (
            user_id INTEGER,
            action_type TEXT,
            date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)


    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS hashtag_categories (
            category_id INTEGER PRIMARY KEY,
            category_name TEXT UNIQUE NOT NULL
            )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS hashtags (
            hashtag_id INTEGER PRIMARY KEY,
            hashtag_name TEXT UNIQUE NOT NULL,
            category_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES hashtag_categories(category_id)
            )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS users_channels (
            user_id INTEGER,
            channel_id INTEGER,
            PRIMARY KEY (user_id, channel_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS chats_hashtags (
                entity_id INTEGER,
                hashtag_id INTEGER,
                PRIMARY KEY (entity_id, hashtag_id),
                FOREIGN KEY (entity_id) REFERENCES chats(chat_id),
                FOREIGN KEY (hashtag_id) REFERENCES hashtags(hashtag_id)
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS chats_blacklist_hashtags (
                entity_id INTEGER,
                hashtag_id INTEGER,
                PRIMARY KEY (entity_id, hashtag_id),
                FOREIGN KEY (entity_id) REFERENCES chats(chat_id),
                FOREIGN KEY (hashtag_id) REFERENCES hashtags(hashtag_id)
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS posts_hashtags (
                entity_id INTEGER,
                hashtag_id INTEGER,
                PRIMARY KEY (entity_id, hashtag_id),
                FOREIGN KEY (entity_id) REFERENCES posts(post_id),
                FOREIGN KEY (hashtag_id) REFERENCES hashtags(hashtag_id)
                        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            chat_id INTEGER,
            role INTEGER,
            content TEXT,
            summary TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
        )
        """)

    db_helper.safe_execute_query("""
        CREATE TABLE IF NOT EXISTS pocket_news (
            pocket_news_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            post_id INTEGER,
            language_id INTEGER,
            style_id INTEGER,
            current_date_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id, language_id, style_id) REFERENCES translation(post_id, language_id, style_id)
        )
        """)


def init_translation_styles():
    for style in post_styles:
        query = """
            INSERT OR IGNORE INTO translation_styles (style_name, description)
            VALUES (?, ?)
        """
        db_helper.safe_execute_query(query, (style['style'], style['description']))


def init_languages():
    """
    Initializes languages in the database based on the given input data.
    """
    for language in languages:
        # Проверяем, существует ли уже язык с таким language_code
        exists_query = "SELECT 1 FROM languages WHERE language_code = ?"
        exists = db_helper.safe_execute_query(exists_query, (language['language_code'],))

        if not exists:
            # Если языка с таким language_code нет, добавляем его
            insert_query = """
                INSERT INTO languages (language_code, encode, direction, name, name_orig)
                VALUES (?, ?, ?, ?, ?)
            """
            db_helper.safe_execute_query(insert_query, (
                language['language_code'], language['encode'], language['direction'],
                language['name'], language['name_orig']
            ))



def init_tariffs():
    """
    Initializes tariffs in the database based on the given input data.
    """
    for tariff in tariffs:
        # Проверяем, существует ли уже тариф с таким price
        exists_query = "SELECT 1 FROM tariffs WHERE price = ?"
        exists = db_helper.safe_execute_query(exists_query, (tariff['price'],))

        if not exists:
            # Если тарифа с таким price нет, добавляем его
            insert_query = """
                INSERT OR IGNORE INTO tariffs (daily_messages_quota, monthly_messages_quota, channels_quota, price, name)
                VALUES (?, ?, ?, ?,?)
            """
            db_helper.safe_execute_query(insert_query, (
            tariff['daily_messages_quota'], tariff['monthly_messages_quota'], tariff['channels_quota'],
            tariff['price'], tariff['name']))

def init_default_channels():
    project_root = Paths.ROOT_DIR

    #paths to default channels
    rss_file_path = project_root + '/settings/parser/rss_channels.txt'
    websites_file_path = project_root + '/settings/parser/website_channels.txt'
    telegram_file_path = project_root + '/settings/parser/telegram_channels.txt'

    rss_channels = read_channels_from_file(rss_file_path, 1)  # 1 для RSS
    website_channels = read_channels_from_file(websites_file_path, 2)  # 2 для веб-сайтов
    telegram_channels = read_channels_from_file(telegram_file_path, 3)  # 3 для telegram

    for channel in rss_channels + website_channels + telegram_channels:
        query = """
            INSERT OR IGNORE INTO channels (channel_name, channel_url, channel_resource_type, channel_privacy) VALUES (?, ?, ?, ?)
        """
        db_helper.safe_execute_query(query, channel)


def read_channels_from_file(file_path, channel_resource_type):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    channels = []
    for i in range(0, len(lines), 2):
        channel_name = lines[i].strip().lstrip('#').strip()
        if i + 1 < len(lines):
            channel_url = lines[i + 1].strip()
            channels.append((channel_name, channel_url, channel_resource_type, 1))
        else:
            DB_INIT_LOGGER.log(logging.WARNING, f"URL missing for channel '{channel_name}'")

    return channels


def init_hashtag_categories(main_categories):
    for category_name in main_categories:
        query = """
            INSERT OR IGNORE INTO hashtag_categories (category_name)
            VALUES (?)
        """
        db_helper.safe_execute_query(query, (category_name,))


def init_hashtags(hashtag_categories):
    for category_name, hashtags in hashtag_categories.items():
        query = "SELECT category_id FROM hashtag_categories WHERE category_name = ?"
        category_id = db_helper.safe_execute_query(query, (category_name,))[0][0]

        for hashtag in hashtags:
            insert_query = """
                INSERT OR IGNORE INTO hashtags (hashtag_name, category_id)
                VALUES (?, ?)
            """
            db_helper.safe_execute_query(insert_query, (hashtag, category_id))


def add_column_if_not_exists(db_helper, table_name, column_name, column_type):
    # Check if a column already exists
    query = f"PRAGMA table_info({table_name})"
    columns_info = db_helper.safe_execute_query(query)

    # Check if the required column is in the list of columns
    if not any(column[1] == column_name for column in columns_info):
        # If the column does not exist, add it
        alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        db_helper.safe_execute_query(alter_query)
        DB_INIT_LOGGER.log(logging.INFO, f"Column {column_name} added to {table_name}.")
    else:
        DB_INIT_LOGGER.log(logging.INFO, f"Column {column_name} already exists in {table_name}.")


def create_database():
    # WAL mode for database journal reading optimization
    DatabaseHelper.safe_execute_query("PRAGMA journal_mode=WAL;")

    init_tables()
    init_languages()
    init_default_channels()
    init_translation_styles()
    init_tariffs()
    init_hashtag_categories(hashtags.main_categories)
    init_hashtags(hashtags.hashtag_categories)

    add_column_if_not_exists(DatabaseHelper, "users", "is_blocked", "INTEGER DEFAULT 0")
    add_column_if_not_exists(DatabaseHelper, "chats", "last_pocket_erasing_date",
                             "DATETIME")
    add_column_if_not_exists(DatabaseHelper, "chats", "preferences", "TEXT")

    # Actualise DB
    ensure_database_structure(DatabaseHelper)


def ensure_database_structure(db_helper):

    # Определение всех необходимых столбцов и таблиц с их типами
    required_structure = {
        'users_usages': {
            'daily_messages_sent': 'INTEGER DEFAULT 0',
            'monthly_messages_sent': 'INTEGER DEFAULT 0',
            'channels_quota': 'INTEGER DEFAULT 0',
            'balance': 'INTEGER DEFAULT 0',
            'activation_date': 'DATE',
            'monthly_news_gathered': 'INTEGER DEFAULT 0',
            'monthly_images_generated': 'INTEGER DEFAULT 0',
            'last_activity': "DATETIME DEFAULT '1970-01-01 00:00:00'",
            # Добавьте сюда новые поля с типами, если они вам нужны
        }
        # Добавьте другие таблицы и поля здесь, если требуется
    }

    # Проходим по всей структуре и добавляем недостающие столбцы
    for table_name, fields in required_structure.items():
        for field_name, field_type in fields.items():
            add_column_if_not_exists(db_helper, table_name, field_name, field_type)


if __name__ == "__main__":
    create_database()