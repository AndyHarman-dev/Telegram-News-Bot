import datetime
import logging

from app.database.db_chat import ChatManager
from app.database.db_helper import DatabaseHelper, DatabaseManager

from app.database.db_translation import TranslationManager
from app.misc.log_helper import LogHelper

LOG_DATABASE_POCKET_NEWS = LogHelper(__name__, "Database Pocket News")


class PocketNewsManager:

    @staticmethod
    def add_news_in_pocket(chat_id, posts_ids: list[tuple[int, int, int]]):
        for post_id, language_id, style_id in posts_ids:
            query = """
                INSERT INTO pocket_news (chat_id, post_id, language_id, style_id)
                VALUES (?, ?, ?, ?);
            """
            DatabaseHelper.safe_execute_query(query, (chat_id, post_id, language_id, style_id))
        return 1

    @staticmethod
    def delete_all_pocket_news_for_chat(chat_id):
        query = """
            DELETE FROM pocket_news
            WHERE chat_id = ?;
        """
        DatabaseHelper.safe_execute_query(query, (chat_id, ))
        return 1

    @staticmethod
    def news_from_pocket(chat_id, news_count: int):
        query = """
            SELECT pocket_news_id, post_id, language_id, style_id
            FROM pocket_news
            WHERE chat_id = ?
            ORDER BY current_date_time ASC
            LIMIT ?;
        """
        result = DatabaseHelper.safe_execute_query(query, (chat_id, news_count))
        if result is None or not result or result[0] is None:
            LOG_DATABASE_POCKET_NEWS.log(logging.WARNING, f'News pocket for chat {chat_id} is empty.')
            return None
        return result

    @staticmethod
    def get_content_news_from_pocket(chat_id, news_count: int):
        result = PocketNewsManager.news_from_pocket(chat_id, news_count)
        if result:
            news_from_pocket = []
            for _, post_id, language_id, style_id in result:
                title, content = TranslationManager.get_existing_translation(post_id, language_id, style_id)
                news_from_pocket.append([title, content])
            return news_from_pocket
        return None

    @staticmethod
    def take_news_from_pocket(chat_id, news_count: int):
        result = PocketNewsManager.news_from_pocket(chat_id, news_count)
        if result:
            for pocket_news_id, _, _, _ in result:
                query = """
                    DELETE FROM pocket_news
                    WHERE pocket_news_id = ?;
                """
                DatabaseHelper.safe_execute_query(query, (pocket_news_id, ))

        return result

    @staticmethod
    def make_unseen_and_delete_partly(chat_id, finding_date_time: datetime.datetime):
        query = """
            DELETE FROM seen_chats_posts
            WHERE post_id IN (
                SELECT post_id
                FROM pocket_news
                WHERE date(current_date_time) != date(?)
                    AND chat_id = ?
            )
        """
        DatabaseHelper.safe_execute_query(query, (finding_date_time, chat_id))
        query = """
            DELETE FROM pocket_news
            WHERE pocket_news_id IN (
                SELECT pocket_news_id
                FROM pocket_news
                WHERE date(current_date_time) != date(?)
                    AND chat_id = ?
            )
        """
        DatabaseHelper.safe_execute_query(query, (finding_date_time, chat_id))
        return 1

    @staticmethod
    def make_unseen_and_delete(chat_id):
        query = """
            DELETE FROM seen_chats_posts
            WHERE post_id IN (
                SELECT post_id
                FROM pocket_news
                WHERE chat_id = ?
            )
        """
        DatabaseHelper.safe_execute_query(query, (chat_id, ))

        PocketNewsManager.delete_all_pocket_news_for_chat(chat_id)
        return 1

    @staticmethod
    def upgrade_pocket_by_news(chat_id, posts_ids: list[tuple[int, int, int]]):
        query = """
            DELETE FROM pocket_news
            WHERE pocket_news_id IN (
                SELECT pocket_news_id
                FROM pocket_news
                ORDER BY current_date_time ASC
                LIMIT ?
            );
        """
        DatabaseHelper.safe_execute_query(query, (len(posts_ids), ))
        return PocketNewsManager.add_news_in_pocket(chat_id, *posts_ids)

    @staticmethod
    def get_unread_news_count(chat_id):
        query = """
                SELECT COUNT(pocket_news_id)
                FROM pocket_news
                WHERE chat_id = ?
            """
        result = DatabaseHelper.safe_execute_query(query, (chat_id, ))
        if result and result[0]:
            return result[0][0]
        return 0
