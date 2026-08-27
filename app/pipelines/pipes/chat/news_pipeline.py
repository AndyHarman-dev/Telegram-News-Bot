import asyncio
from collections.abc import Iterable, AsyncIterable
from datetime import datetime, timedelta

from telegram import ReplyKeyboardMarkup

from app.bot.config import openai_config, startup_config
from app.bot.states.users_states import UsersStates
from app.bot.telegram_helper import TelegramHelper
from app.database.db_chat import ChatManager
from app.database.db_hashtag import HashtagManager
from app.database.db_helper import DatabaseHelper, DatabaseManager
from app.database.db_llm import DatabaseLlmManager
from app.database.db_pocket_news import PocketNewsManager
from app.database.db_post import PostManager
from app.database.db_translation import TranslationManager
from app.init import init_default_classes
from app.llm.image_generator.image_generator_base import ImageGenerator
from app.pipelines.pipes.parser.parser_pipeline import Parser

import logging
from app.misc.log_helper import LogHelper

import re

from app.pipelines.pipeline import Pipeline
from app.misc.events.events import AsyncEventHandler

LOG_NEWSMANAGER = LogHelper(__name__, "Newsmanager")


class NewsManager(Pipeline):
    USERS = 1
    PUBLIC_CHANNELS = 2
    PRIVATE_CHANNELS = 3

    ON_NEWS_SENT = AsyncEventHandler()

    def __init__(self, pipeline_tag='newsmanager_pipeline'):
        super().__init__(pipeline_tag)

    def main(self, *args, **kwargs):
        """Called when pipeline is run"""
        # delete old posts
        # PostManager.delete_old_posts(14)
        # send news to all chats
        asyncio.run(NewsManager.async_main())
        return 0

    @staticmethod
    async def async_main():
        #await asyncio.create_task(NewsManager.erasing_pocket_in_chats(1))
        await asyncio.create_task(NewsManager.partly_erasing_pocket_in_chats(1))
        await asyncio.create_task(NewsManager.send_news_to_all_chats_by_type(1))
        
        #if NewsManager.ON_NEWS_SENT:
        #    await NewsManager.ON_NEWS_SENT.trigger()

    def on_pipeline_begin(self):
        """Override on pipeline begin"""
        super().on_pipeline_begin()
        self._pipeline_logger.log(logging.INFO, "Starting sending news to all chats...")

    def on_pipeline_end(self):
        """Override on pipeline end"""
        super().on_pipeline_end()
        self._pipeline_logger.log(logging.INFO, "Finished sending news to all chats...")

    @staticmethod
    async def partly_erasing_pocket_in_chats(selected_chat_types: int | list = (1, 2, 3, 4)):
        if isinstance(selected_chat_types, int):
            selected_chat_types = [selected_chat_types]
        all_chats = await ChatManager.get_chats_and_shifts(selected_chat_types)
        if not all_chats:
            LOG_NEWSMANAGER.log(logging.WARNING, "No chats found!")
        coroutines = [NewsManager.erase_news_from_chat(chat_id, shift) for chat_id, shift in all_chats]
        await asyncio.gather(*coroutines)
        return 0

    @staticmethod
    async def erase_news_from_chat(chat_id, shift):
        server_time = datetime.utcnow()
        user_hours = ChatManager.timezone_checking(chat_id, shift)
        user_local_time = server_time + timedelta(hours=user_hours)
        news_count = PocketNewsManager.get_unread_news_count(chat_id)
        PocketNewsManager.make_unseen_and_delete_partly(chat_id, user_local_time)
        DatabaseManager.update_or_insert_field("chats",
                                               "last_pocket_erasing_date",
                                               datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                               "chat_id", chat_id)
        if news_count != PocketNewsManager.get_unread_news_count(chat_id):
            from app.bot.states.bot_states.unread_news_state import UnreadNewsState
            await UnreadNewsState.create_update_message_for_chat(chat_id)
        return 0

    @staticmethod
    async def erasing_pocket_in_chats(selected_chat_types: int | list = (1, 2, 3, 4)):
        if isinstance(selected_chat_types, int):
            selected_chat_types = [selected_chat_types]
        all_chats = await ChatManager.get_chats_for_pocket_erasing(selected_chat_types)
        if len(all_chats) == 0:
            LOG_NEWSMANAGER.log(logging.WARNING, "No chats with full pocket found!")
        coroutines = [NewsManager.erase_all_news_from_chat(chat_id) for chat_id in all_chats]
        await asyncio.gather(*coroutines)
        return 0

    @staticmethod
    async def erase_all_news_from_chat(chat_id):
        PocketNewsManager.make_unseen_and_delete(chat_id)
        DatabaseManager.update_or_insert_field("chats",
                                               "last_pocket_erasing_date",
                                               datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                               "chat_id", chat_id)
        return 0

    @staticmethod
    async def send_news_to_all_chats_by_type(selected_chat_types: int | list = (1, 2, 3, 4)):
        """
        Sends news to all chats of the specified types.
        Args:
            selected_chat_types (list): The types of chats to send news to. # 1 - users 2-  public channels 3 - private channels
        Returns:
            int: Always returns 0.
        """
        if isinstance(selected_chat_types, int):
            selected_chat_types = [selected_chat_types]

        all_chats = await ChatManager.get_available_chats_by_type(selected_chat_types)

        if len(all_chats) == 0:
            LOG_NEWSMANAGER.log(logging.WARNING, "No chats found!")

        # Asynchronously send news to unblocked chats
        all_chats = [chat_id for chat_id in all_chats if not await TelegramHelper.is_bot_blocked(chat_id)]
        coroutines = [NewsManager.send_news_to_pocket(chat_id, number_of_posts=5, add_url=True, add_image=True,
                                                      b_set_seen=not startup_config['debug_mode'])
                      for chat_id in all_chats]
        await asyncio.gather(*coroutines)

        return 0

    @staticmethod
    async def send_news_to_pocket(chat_id, number_of_posts=5, add_url=True, add_image=True, b_set_seen=True):

        posts_ids = await NewsManager.send_news_to(chat_id, number_of_posts, add_url, add_image, b_set_seen,
                                                   True)
        PocketNewsManager.add_news_in_pocket(chat_id, posts_ids)
        await NewsManager.news_sender_message(chat_id)

    @staticmethod
    async def news_sender_message(chat_id):
        from app.bot.states.bot_states.unread_news_state import UnreadNewsState

        await UnreadNewsState.create_message_for_chat(chat_id)

    @staticmethod
    async def send_news_from_pocket_to_chat(chat_id, number_of_posts=5, add_url=True, add_image=True):
        news_from_pocket = PocketNewsManager.take_news_from_pocket(chat_id, number_of_posts)
        if not news_from_pocket:
            from app.bot.states.state import State

            message = await State.get_locale_text_by_chat_id(chat_id, 'states', "unread_news", "no_news")
            message = message.replace('/1', '/menu')
            message = message.replace('1/', '/menu')

            return await UsersStates.add_last_message_in_chat(chat_id, message)

        async def iterable_to_async_iterable(iterable: Iterable) -> AsyncIterable:
            for item in iterable:
                yield item

        async for pocket_news in iterable_to_async_iterable(news_from_pocket):
            _, post_id, chat_language, chat_style = pocket_news
            titles, full_post, image_path = await NewsManager.get_full_post(post_id, chat_language, chat_style,
                                                                            add_url, add_image, chat_id=chat_id)
            await TelegramHelper.send_message_with_photo(chat_id, full_post, image_path)
        await NewsManager.news_sender_message(chat_id)

    @staticmethod
    async def send_news_to(chat_id, number_of_posts=5, add_url=True, add_image=True, b_set_seen=True, to_pocket=False):
        """
        Sends relevant news to a chat, with the specified number of posts, and options to add URL, image, and set seen status.

        Args:
            chat_id (int): The ID of the chat to send news to.
            number_of_posts (int): The number of posts to send (default is 5).
            add_url (bool): Whether to add URL to the news (default is True).
            add_image (bool): Whether to add image to the news (default is True).
            b_set_seen (bool): Whether to set the seen status of the posts (default is True).
            to_pocket (bool): Sending to pocket marker (default is False).

        Returns:
            List of gathered news.
        """

        async def iterable_to_async_iterable(iterable: Iterable) -> AsyncIterable:
            for item in iterable:
                yield item

        reserve_for_possible_fails = 5
        timed_out_retreats = 3

        # get chat's relevant news
        unseen_posts = await NewsManager.get_relevant_post_ids(chat_id, number_of_posts + reserve_for_possible_fails)
        if len(unseen_posts) == 0:
            LOG_NEWSMANAGER.log(logging.WARNING, "No unseen posts found for chat: " + str(chat_id))
        gathered_posts = []

        chat_language = ChatManager.get_chat_language(chat_id)
        chat_style = ChatManager.get_chat_style(chat_id)

        if len(unseen_posts) <= 0:
            LOG_NEWSMANAGER.log(logging.WARNING, f"There were no unseen posts to show for {chat_id} chat. "
                                                 f"Continue to next chat...")
            return

        async for post_id in iterable_to_async_iterable(unseen_posts):

            try:
                titles, full_post, image_path = await NewsManager.get_full_post(post_id, chat_language, chat_style,
                                                                                add_url, add_image, chat_id=chat_id)
                if full_post is not None:
                    # adding content to list

                    if len(gathered_posts) >= number_of_posts:
                        return gathered_posts

                    for i in range(timed_out_retreats):
                        try:
                            if to_pocket:
                                gathered_posts.append((post_id, chat_language, chat_style))
                            else:
                                await TelegramHelper.send_message_with_photo(chat_id, full_post, image_path)
                                gathered_posts.append(full_post)
                            break
                        except Exception as e:
                            if 'timed out' not in str(e).lower():
                                LOG_NEWSMANAGER.log(logging.WARNING, f"send_news_to_chat - Post with post id "
                                                                     f"{post_id} can\'t sanding to the chat {chat_id} "
                                                                     f"because '{e}.'")
                                break
                            LOG_NEWSMANAGER.log(logging.WARNING, f"send_news_to_chat - Post with post id "
                                                                 f"{post_id} can\'t sanding to the chat {chat_id} "
                                                                 f"because timed out error occurred."
                                                                 f"Retreat n.{i+1}.")

                else:
                    LOG_NEWSMANAGER.log(logging.WARNING, f"send_news_to_chat - Can't get full post for "
                                                         f"{post_id} post_id (and for chat id {chat_id}).")

            except Exception as e:
                LOG_NEWSMANAGER.log(logging.ERROR, f"send_news_to_chat - "
                                                   f"Failed to send post {post_id} to chat {chat_id}."
                                                   f"Fail reason is '{e}' error.")
            finally:
                # Update seen status
                if b_set_seen:
                    DatabaseManager.link_entities_in_relation_table('seen_chats_posts',
                                                                    'post_id', post_id,
                                                                    'chat_id', chat_id)
                elif not b_set_seen and startup_config['debug_mode']:
                    LOG_NEWSMANAGER(logging.WARNING, "Debug mode is enabled, seen status was not updated!")

                # Update last message sent to chat (in chat), only if no debug mode enabled
                if not startup_config['debug_mode']:
                    ChatManager.update_last_message_time(chat_id)
                else:
                    LOG_NEWSMANAGER(logging.WARNING, "Debug mode is enabled, last message was not updated!")

        return gathered_posts

    @staticmethod
    async def gather_posts_for_hashtag(hashtag, number_of_posts=5, language=1, style=1, add_url=True, add_image=True):
        """
        Asynchronously gathers posts for a given hashtag.
        Args:
            hashtag (str): The hashtag to gather posts for.
            number_of_posts (int): The number of posts to gather (default is 5).
            language (int): The language of the posts (default is 1).
            style (int): The style of the posts (default is 1).
            add_url (bool): Whether to add URL to the posts (default is True).
            add_image (bool): Whether to add image to the posts (default is True).
        Returns:
            list: A list of gathered posts.
        """
        hashtag_id = HashtagManager.get_hashtag_id(hashtag)  # Call the function we wrote earlier to get the hashtag ID

        if hashtag_id is None:
            return []  # Return an empty list if the hashtag is not found

        # Get the relevant posts for the hashtag
        relevant_posts = HashtagManager.get_relevant_posts_for_hashtag(hashtag_id, number_of_posts)

        gathered_posts = await NewsManager.get_posts(relevant_posts, language, style, add_url, add_image)

        return gathered_posts

    @staticmethod
    async def add_hashtags_to_posts():
        """
        Add hashtags to posts with a rating greater than or equal to 4 and without existing hashtags.
        This function retrieves posts meeting the specified criteria, processes the text content
        to add hashtags, and then launches the tasks in batches based on the OpenAI configuration
        for threads limit.
        """
        # get all news with rating >4 and still without hashtags
        query = """
            SELECT p.post_id, p.content 
            FROM posts p
            WHERE p.rating >= 4 AND NOT EXISTS (
                SELECT 1 FROM posts_hashtags ph WHERE p.post_id = ph.entity_id
            )
        """
        posts = DatabaseHelper.safe_execute_query(query)

        total_posts = len(posts)  # Get the total number of posts
        print('posts to process with hashtags: ', total_posts)
        '''
        for index, (post_id, content) in enumerate(posts):
            # for each post, add hashtags
            await DatabaseLlmManager.process_text_with_hashtags(content, post_id, 'posts_hashtags')

            # Print the progress: current index out of total posts
            print(f"Progress: {index + 1}/{total_posts}")
        '''

        # Создание задач для каждого поста
        tasks = [DatabaseLlmManager.process_text_with_hashtags(post_content, post_id, 'posts_hashtags') for
                 post_id, post_content in posts]

        # launch tasks in batches
        await DatabaseLlmManager.run_tasks_in_batches(tasks, openai_config['llm_threads_limit'] )

    @staticmethod
    async def get_relevant_post_ids(chat_id, num_posts=5):
        """
        Retrieves the IDs of the latest 'num_posts' posts relevant to the chat's hashtags but not in the chat's blacklist
        and not already shown to the chat. If no relevant posts are found, retrieves the latest 'num_posts' posts regardless
        of relevance.

        Args:
            chat_id (int): The ID of the chat.
            num_posts (int): Number of post IDs to retrieve.

        Returns:
            list: A list of relevant post IDs.
        """
        # Retrieve the hashtags related to the chat and those that are blacklisted.
        # chat_hashtags = HashtagManager.get_hashtag_ids_for_entity(chat_id, 'chats_hashtags')
        # blacklist_hashtags = HashtagManager.get_hashtag_ids_for_entity(chat_id, 'chats_blacklist_hashtags')

        # Query to get the relevant post IDs based on the chat's hashtags and not blacklisted.
        relevant_posts_query = f"""
            SELECT DISTINCT p.post_id FROM posts p
            JOIN posts_hashtags ph ON p.post_id = ph.entity_id
            WHERE ph.hashtag_id IN (SELECT hashtag_id FROM chats_hashtags WHERE entity_id = ?)
            AND p.post_id NOT IN (
                SELECT post_id FROM posts_hashtags WHERE hashtag_id IN (SELECT hashtag_id FROM chats_blacklist_hashtags WHERE entity_id = ?)
            )
            AND p.post_id NOT IN (
                SELECT post_id FROM seen_chats_posts WHERE chat_id = ?
            )
            ORDER BY p.date DESC
            LIMIT ?
        """

        # Attempt to get relevant posts
        relevant_params = [chat_id, chat_id, chat_id, num_posts]
        relevant_result = DatabaseHelper.safe_execute_query(relevant_posts_query, relevant_params)

        # If no relevant posts are found, get the latest posts regardless of hashtags.
        if not relevant_result:
            fallback_query = f"""
                SELECT post_id FROM posts
                WHERE post_id NOT IN (
                    SELECT post_id FROM seen_chats_posts WHERE chat_id = ?
                )
                ORDER BY date DESC
                LIMIT ?
            """
            fallback_params = [chat_id, num_posts]
            fallback_result = DatabaseHelper.safe_execute_query(fallback_query, fallback_params)
            return [row[0] for row in fallback_result]

        return [row[0] for row in relevant_result]

    @staticmethod
    async def get_post_content(post_id, **kwargs):
        """
        Retrieves the content for a given post. If the content does not exist in the database,
        it fetches the content using the URL, stores it, and then returns it.

        Args:
            post_id (int): The ID of the post.

        Returns:
            str: The content of the post.
        """
        # check if content already exists
        if PostManager.is_content_exists_for_post(post_id):

            #get full post if already parsed
            query = "SELECT content FROM posts_content WHERE post_id = ?"
            result = DatabaseHelper.safe_execute_query(query, (post_id,))
            if result:
                return result[0][0]
        else:
            # get post URL
            query = "SELECT link FROM posts WHERE post_id = ?"
            result = DatabaseHelper.safe_execute_query(query, (post_id,))
            url = result[0][0] if result else None

            # fetching content
            if url is not None:
                content = await Parser.fetch_full_post_content(url)

                if content:
                    # saving to database
                    insert_query = "INSERT INTO posts_content (post_id, content) VALUES (?, ?)"
                    DatabaseHelper.safe_execute_query(insert_query, (post_id, content))

                    return content
                else:
                    LOG_NEWSMANAGER.log(logging.WARNING, f"get_post_content - Can't get full post for "
                                                         f"post ID {post_id} and "
                                                         f"url {url} "
                                                         f"(and chat ID {kwargs.get('chat_id', None)}).")
            else:
                LOG_NEWSMANAGER.log(logging.WARNING, f"get_post_content - Empty URL for {post_id} post_id.")

            # get short description and content as fallback
            query = "SELECT title,content FROM posts WHERE post_id = ?"
            result = DatabaseHelper.safe_execute_query(query, (post_id,))
            if result:
                field1 = result[0][0] if result[0][0] is not None else ""
                field2 = result[0][1] if result[0][1] is not None else ""
                return field1 + field2

        return None

    @staticmethod
    async def get_post_title(post_id):
        """
        Retrieves the content for a given post. If the content does not exist in the database,
        it fetches the content using the URL, stores it, and then returns it.

        Args:
            post_id (int): The ID of the post.

        Returns:
            str: The content of the post.
        """
        query = "SELECT title FROM posts WHERE post_id = ?"
        result = DatabaseHelper.safe_execute_query(query, (post_id,))
        return result[0][0] if result else None

    @staticmethod
    async def get_translation(post_id, language_id, style_id, **kwargs):
        # Check if the translation already exists
        if TranslationManager.is_translation_exists(post_id, language_id, style_id):
            # If exists, retrieve the existing translation from the database
            existing_title, existing_content = await TranslationManager.get_existing_translation(post_id,
                                                                                                 language_id,
                                                                                                 style_id)
            return existing_title, existing_content
        # If not exists, generate a new translation
        original_content = await NewsManager.get_post_content(post_id, chat_id=kwargs.get('chat_id', None))
        original_title = await NewsManager.get_post_title(post_id)
        translated_content = await DatabaseLlmManager.llm_translate_text(original_content,
                                                                         language_id,
                                                                         style_id,
                                                                         False,
                                                                         True)
        translated_title = await DatabaseLlmManager.llm_translate_text(original_title,
                                                                       language_id,
                                                                       style_id,
                                                                       True,
                                                                       True)

        if translated_content is not None:
            # Save the new translation to the database
            TranslationManager.create_translation(post_id, language_id, style_id, translated_title, translated_content)
            return translated_title, translated_content
        LOG_NEWSMANAGER.log(logging.ERROR,
                            "Failed to generate a new translation.")
        return None, None

    @staticmethod
    async def get_posts(post_ids, language=1, style=1, add_url=False, add_image=False):
        gathered_posts = []
        for post_id in post_ids:
            title, full_post, image_path = await NewsManager.get_full_post(post_id, language, style, add_url, add_image)
            if full_post is not None:
                # adding content to list
                gathered_posts.append((post_id, title, full_post, image_path))  # Используйте кортеж вместо списка

        return tuple(gathered_posts)  # Преобразуйте список в кортеж

    @staticmethod
    async def get_full_post(post_id, language=1, style=1, add_url=False, add_image=False,
                            add_hashtags=False, add_markdown=True, upper_title=True, **kwargs):
        title, content = await NewsManager.get_translation(post_id, language, style,
                                                           chat_id=kwargs.get('chat_id', None))

        def remove_html_tags(text):
            import re
            clean = re.compile('<.*?>')
            return re.sub(clean, '', text)

        content = remove_html_tags(content)

        """
        Get the full post content including title, content, hashtags, and optional URL and image.

        Parameters:
            post_id (int): The ID of the post to retrieve.
            language (int): The language of the post content. Defaults to 1.
            style (int): The style of the post content. Defaults to 1.
            add_url (bool): Whether to include the URL in the post content. Defaults to False.
            add_image (bool): Whether to include an image in the post content. Defaults to False.
            add_hashtags (bool): Whether to include hashtags in the post content. Defaults to True.
            add_markdown (bool): Whether to format the post content using markdown. Defaults to True.

        Returns:
            tuple: A tuple containing the title (str), full post text (str), and image path (str).
        """
        # Decode text, if needed
        title = re.sub(r'\\u[0-9a-fA-F]{4}', lambda x: x.group(0).encode().decode('unicode_escape'),
                       title) if title else None
        content = re.sub(r'\\u[0-9a-fA-F]{4}', lambda x: x.group(0).encode().decode('unicode_escape'),
                         content) if content else None

        if title is None or content is None:
            post = PostManager.get_post_by_id(post_id)
            LOG_NEWSMANAGER.log(logging.WARNING, f"get_full_post - Can't get full title or content for post_id: {post_id} ")
            return None, None, None

        # get all hashtags and convert to string
        hashtags = await HashtagManager.get_post_hashtags(post_id)
        hashtags_str = ', '.join([f'{hashtag}' for hashtag in hashtags])

        if upper_title:
            title = title.upper()

        url = ''
        if add_url:
            url = await DatabaseManager.get_single_field_value('posts', 'link', 'post_id', post_id)

        # Formatting: bold title with hyperlink to main article, regular content, italic hashtags (if hashtags enabled)
        if add_markdown:
            full_post_text = f"<a href='{url}'><b>{title}</b></a>\n \n{content}"
            if add_hashtags:
                full_post_text += f"\n <i>{hashtags_str}</i> "
        else:
            full_post_text = f"{content}\n {url}"
            if add_hashtags:
                full_post_text += f"\n{hashtags_str}"

        # for add image
        image_path = None
        if add_image:
            image_path = await ImageGenerator.get_image(str(post_id), title)

        return title, full_post_text, image_path

    @staticmethod
    def delete_post(post_id):
        """
        Delete post and it's content from database, if exist

        Args:
            post_id (int): ID поста, который нужно удалить.
        """
        # check if post exists
        check_post_exists_query = "SELECT COUNT(*) FROM posts WHERE post_id = ?"
        result = DatabaseHelper.safe_execute_query(check_post_exists_query, (post_id,))
        if result[0][0] == 0:
            print(f"No post found with ID {post_id}. Nothing to delete.")
            return

        # post content
        delete_content_query = "DELETE FROM posts_content WHERE post_id = ?"
        DatabaseHelper.safe_execute_query(delete_content_query, (post_id,))

        # post
        delete_post_query = "DELETE FROM posts WHERE post_id = ?"
        DatabaseHelper.safe_execute_query(delete_post_query, (post_id,))

        # image
        ImageGenerator.delete_image(post_id)

        print(f"Post and its content with ID {post_id} have been deleted.")


async def my_func():
    init_default_classes()

    #await NewsManager.get_full_post(10,9,3)

    #news = await NewsManager.gather_posts_for_hashtag('#Politics',10)
    #print(news)

    news = await NewsManager.gather_posts_for_hashtag('#Politics')
    print(news)

    #relevant_posts = NewsManager.get_relevant_post_ids(chat_id=466001259, num_posts=10)
    #print (relevant_posts)

    # Пример использования функции
    #post_content = NewsManager.get_translation(1,1,7)
    #await show_news_to_chat(some_chat_id)

if __name__ == "__main__":
    asyncio.run(my_func())

    #news_manager = NewsManager()
    #news_manager.main()


    #newsmanager = NewsManager()
    #asyncio.run( newsmanager.main() )
