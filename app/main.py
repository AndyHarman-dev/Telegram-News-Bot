from datetime import datetime
import sys
import os
from pathlib import Path
# root folder for module search
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.bot import config
from app.bot.telegram_bot import ChatGPTTelegramBot
from app.misc.scheduler import Scheduler

from app.pipelines.pipes.chat.news_pipeline import NewsManager
from app.database.db_init import create_database
from app.pipelines.pipes.database_util_pipeline import Database_util
from app.pipelines.pipes.parser.parser_pipeline import Parser
from app.misc import log_helper
import logging
from app.init import init_default_classes


LOG = log_helper.LogHelper(__name__, "Main Thread")

LOG.log(logging.INFO, f"Verbose logging enabled: {log_helper.VERBOSE_LOGGING}")


# Define global startup variables
SCHEDULER_PARSER = None
PARSER = None
NEWS_MANAGER = None
DATABASE_UTIL = None


def startup_submodules():
    global SCHEDULER_PARSER, PARSER, NEWS_MANAGER, DATABASE_UTIL

    # Gather startup conditions
    enable_parser = config.startup_config['enable_parser']
    parsing_interval = config.startup_config['parsing_interval']
    enable_news_sending = config.startup_config['enable_news_sending']
    news_sending_interval = config.startup_config['news_sending_interval']
    enable_database_cleanup = config.startup_config['enable_database_cleanup']

    # Cleanup database if necessary
    if enable_database_cleanup:
        DATABASE_UTIL = Database_util('DatabaseUtil')
        DATABASE_UTIL.run(parallel=True)
        LOG(logging.INFO, "Database was cleaned up")

    # Initialize global scheduler
    SCHEDULER_PARSER = Scheduler()

    # Enable parsing
    if enable_parser:
        PARSER = Parser('Parser')
        if not SCHEDULER_PARSER:
            LOG.raise_exception_with_log(ValueError("Scheduler not initialized"))

        SCHEDULER_PARSER.schedule_task(PARSER.run, parsing_interval, 'minutes')
        LOG(logging.INFO, "Parser was enabled")

    # Enable news sending
    if enable_news_sending:
        NEWS_MANAGER = NewsManager('NewsManager')
        if not SCHEDULER_PARSER:
            LOG.raise_exception_with_log(ValueError("Scheduler not initialized"))

        SCHEDULER_PARSER.schedule_task(NEWS_MANAGER.run, news_sending_interval, 'minutes')
        LOG(logging.INFO, "News manager was enabled")

    LOG(logging.INFO, "App started at: " + str(datetime.now()))


def main():

    # Initialize tables with default values
    create_database()

    # Initialize default classes
    init_default_classes()

    # Startup the submodules
    startup_submodules()

    telegram_bot = ChatGPTTelegramBot(token=config.telegram_config['token'])
    telegram_bot.run()


if __name__ == '__main__':
    main()
