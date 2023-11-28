from config import config
from bot.bot import TelegramBot
from misc.log_helper import LogHelper, logging
from misc.pexels_library import PexelsAPI
from AI import post_generator
import asyncio

TG_LOG_M = LogHelper(__name__, "Main thread")

TG_TOKEN = config.CONFIG_DICT['token']
BOT_USERNAME = config.CONFIG_DICT['bot_name']


def main():
    TG_LOG_M.log(logging.INFO, "Starting bot")
    bot_username: str = config.CONFIG_DICT['bot_name']

    #re = UnsplashAPI.test()

    bot = TelegramBot(TG_TOKEN, BOT_USERNAME)
    bot.run()


if __name__ == "__main__":
    main()
