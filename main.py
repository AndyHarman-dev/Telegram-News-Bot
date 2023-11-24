from config import config
from bot.bot import TelegramBot
from misc.log_helper import LogHelper, logging

TG_LOG_M = LogHelper(__name__, "Main thread")

if __name__ == "__main__":
    TG_LOG_M.log(logging.INFO, "Starting bot")
    bot = TelegramBot(config.TOKEN)
    bot.run()

