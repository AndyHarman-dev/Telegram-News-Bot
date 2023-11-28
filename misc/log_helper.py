import logging
from config import config

DEFAULT_LOG_PATH = config.CONFIG_DICT['log_path']


class LogHelper:
    def __init__(self, logger_name: str, logger_category: str) -> None:
        self.logger_name_ = logger_name
        self.logger_category_ = logger_category
        self.__logger_ = logging.getLogger(logger_name)
        self.__logger_.setLevel(logging.DEBUG)
        # Create a formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Create a file handler
        file_handler = logging.FileHandler(DEFAULT_LOG_PATH + "/" + "telegram-bot.log")

        # Add the formatter to the file handler
        file_handler.setFormatter(formatter)

        # Add the file handler to the logger
        self.__logger_.addHandler(file_handler)

    def log(self, level: int, message: str) -> None:
        formatted_msg = self.logger_category_ + ": " + message
        self.__logger_.log(level, formatted_msg)
        self.__print_console__(level, message)

    def __print_console__(self, level: int, message: str) -> None:
        formatted_msg = self.logger_category_ + " : " + logging.getLevelName(level) + " : " + message
        print(formatted_msg)
