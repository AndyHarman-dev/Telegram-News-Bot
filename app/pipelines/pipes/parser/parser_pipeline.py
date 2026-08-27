from datetime import datetime
import csv
import feedparser

import aiohttp

from bs4 import BeautifulSoup

import asyncio

from app.bot.config import telegram_config
from app.database.db_channel import ChannelManager
from app.database.db_llm import DatabaseLlmManager
from app.database.db_helper import Channel, Post

from telethon.sync import TelegramClient

from app.database.db_helper import DatabaseHelper, DatabaseManager

from app.misc.log_helper import LogHelper
import logging

from app.misc.paths import Paths
from app.pipelines.pipeline import Pipeline

LOG_PARSER = LogHelper(__name__, "Parser")


class Parser(Pipeline):

    def __init__(self, pipeline_tag='parser_pipeline'):
        super().__init__(pipeline_tag)

    def main(self, *args, **kwargs):
        """Called when pipeline is run"""

        asyncio.run(Parser.rss_parser())
        #asyncio.run(Parser.rss_bridge_parser())

        #await Parser.rss_parser()
        #await Parser.rss_bridge_parser() # rss-bridges in localhost needed
        #add hashtags to posts
        return 0

    @staticmethod
    async def rss_parser():
        # get RSS channels list
        rss_channels = ChannelManager.get_channels_by_type(1)

        '''
        total_entries = 0
        for channel_id, rss_url in rss_channels:
            try:
                total_entries += len(feedparser.parse(rss_url).entries)
            except Exception as e:
                logging.error(f"Error parsing feed from {rss_url}: {e}")

        processed_entries = 0
        print(f"Begin parsing of {total_entries} posts...")
        '''
        await Parser.__rss_channel_parsing(rss_channels)

    @staticmethod
    async def __rss_channel_parsing(rss_channels):
        for channel_id, rss_url in rss_channels:
            try:
                LOG_PARSER.log(logging.DEBUG, f"start parsing channel: {rss_url} ")
                feed = feedparser.parse(rss_url)

                total_entries = len(feed.entries)
                processed_entries = 0
            except Exception as e:
                LOG_PARSER.log(logging.ERROR, f"Error processing feed from {rss_url}: {e}")
                continue

            for entry in feed.entries:
                try:
                    # check if news already exist
                    if not DatabaseManager.is_exists("posts", "link", entry.link):

                        # get post description from different fields
                        description = ''
                        if hasattr(entry, 'description'):
                            description = entry.description
                        elif hasattr(entry, 'summary'):
                            description = entry.summary
                        elif hasattr(entry, 'title'):
                            description = entry.title
                        else:
                            LOG_PARSER.log(logging.WARNING,
                                           f"No description found for entry with title: {entry.title} in {entry.link}")

                        # rate post with AI
                        post_text = entry.title + description
                        rating = await DatabaseLlmManager.llm_rate_post(post_text)

                        # create and save new post
                        new_post = Post(channel_id=channel_id, title=entry.title, content=description,
                                        link=entry.link, rating=rating)
                        new_post.save()

                        # if new_post.id ==0:
                        #    new_post.id = DatabaseManager.get_last_id("posts")

                        # add hashtags only for quality posts
                        if rating >= 4:
                            await DatabaseLlmManager.process_text_with_hashtags(post_text, new_post.post_id,
                                                                                'posts_hashtags')

                        processed_entries += 1
                        LOG_PARSER.log(logging.DEBUG, f"Parsed posts: {processed_entries}/{total_entries}")
                    else:
                        LOG_PARSER.log(logging.DEBUG, f"Post '{entry.title}' already processed")

                except Exception as e:
                    LOG_PARSER.log(logging.WARNING, f"Error processing post from {entry.title} in {entry.link}: {e}")
                    continue

    @staticmethod
    async def rss_bridge_parser():
        _csv_file_name = Paths.ROOT_DIR + '/app/pipelines/pipes/parser/sites_with_rss_bridges.csv'
        # get RSS-bridges list from csv-file
        rss_bridges_channels = Parser.__read_all_bridges_from_csv(_csv_file_name)
        await Parser.__rss_channel_parsing(rss_bridges_channels)

    @staticmethod
    def __read_all_bridges_from_csv(file):
        all_bridges = []
        with open(file, newline='', encoding='utf-8') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=';')
            for row in csvreader:
                all_bridges.append((row[0], row[1]))
        return all_bridges

    @staticmethod
    async def telegram_parser():
        # Авторизация в Telegram
        api_id = telegram_config['bot_api']
        api_hash = telegram_config['bot_hash']
        bot_token = telegram_config['token']
        client = TelegramClient('session_name', api_id, api_hash)

        await client.start()

        # Получение списка каналов
        tg_channels = ChannelManager.get_channels_by_type(3) # 3 for telegram channels

        total_entries = 0
        processed_entries = 0

        async with client:
            for channel_id, tg_url in tg_channels:
                channel_entity = await client.get_entity(tg_url)
                messages = await client.get_messages(channel_entity, limit=100) # Ограничение количества сообщений
                total_entries += len(messages)

                for message in messages:
                    # Проверка, существует ли уже пост
                    if not DatabaseManager.is_exists("posts", "link", message.link):
                        # Обработка сообщения
                        post_text = message.text
                        rating = await DatabaseLlmManager.llm_rate_post(post_text)

                        # Создание и сохранение нового поста
                        new_post = Post(channel_id=channel_id, title=message.title, content=message.text, link=message.link, rating=rating)
                        new_post.save()

                        processed_entries += 1
                        LOG_PARSER.log(logging.INFO, f"Parsed posts: {processed_entries}/{total_entries}")
                    else:
                        LOG_PARSER.log(logging.INFO, f"Post with ID '{message.id}' already processed")

            LOG_PARSER.log(logging.INFO, f"Completed parsing of {total_entries} posts.")

    @staticmethod
    async def fetch_full_post_content(url):
        """
        Fetches the full content of a news post from its URL using BeautifulSoup.

        Args:
            url (str): The URL of the news post.

        Returns:
            str: The full text content of the post, or None if an error occurs.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    content = await response.text()

                soup = BeautifulSoup(content, 'html.parser')

            # Remove unwanted elements like scripts, styles, headers, footers, and navigation bars
            for unwanted in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']):
                unwanted.decompose()

            # Attempt to find the main content container
            main_content = soup.find('main') or soup.find('article') or soup.find('div', {'role': 'main'})

            # Use main content if found, otherwise use the entire body
            content_to_use = main_content if main_content else soup.body

            if content_to_use:
                # Get clean text from the content
                clean_text = content_to_use.get_text(separator='\n', strip=True)

                # Further clean up the text
                lines = (line.strip() for line in clean_text.splitlines())
                # Remove lines with less than 6 words
                start_word_count = 6
                filtered_lines = []
                while not filtered_lines and start_word_count >= 2:
                    filtered_lines = [line for line in lines if len(line.split()) >= start_word_count]
                    start_word_count -= 1

                return '\n'.join(filtered_lines)
            else:
                LOG_PARSER.log(logging.WARNING, "Content not found.")
                return None

        except aiohttp.ClientError as e:
            LOG_PARSER.log(logging.ERROR, f"HTTP error while fetching from {url}: {e}")
            return None
        except Exception as e:
            LOG_PARSER.log(logging.ERROR, f"Error while processing content from {url}: {e}")
            return None


async def my_func():
    # url = "https://www.bbc.com/news/live/world-middle-east-67751758"  # Пример URL новости
    url = "https://pikabu.ru/story/15_strannyikh_i_absurdnyikh_sovetskikh_multikov_kotoryie_izmenyat_vashe_predstavlenie_o_multiplikatsii_togo_vremeni_9964496"  # Пример URL новости
    full_content = await Parser.fetch_full_post_content(url)
    if full_content:
        print(full_content)


async def new_func():
    full_content = await Parser.rss_bridge_parser()
    if full_content:
        print(full_content)


async def main():
    await Parser.rss_parser()
    #await Parser.rss_bridge_parser()


if __name__ == '__main__':
    asyncio.run(main())
    pass



    # parser = Parser('')
    # parser.run()

    #print(asyncio.run( main() ))



#    posts_id = 123  # Example posts ID
#    posts_content = "Example posts content here."
#    assign_hashtags_to_posts(posts_id, posts_content)
