import logging
import os
import dotenv

# Get the absolute path of the current module
current_module_path = os.path.abspath(__file__)

# Get the directory of the current module
current_module_dir = os.path.dirname(current_module_path)

# Get the path of the target directory relative to the current module
target_dir_path = os.path.join(current_module_dir, '../..', 'saved/logs')

# Normalize the path (remove any '..')
target_dir_path = os.path.normpath(target_dir_path)

DEFAULT_LOG_PATH = target_dir_path

dotenv.load_dotenv()

# Enables verbose logging
VERBOSE_LOGGING = os.environ.get('VERBOSE_LOGGING', 'False') == 'True'


class LogHelper:

    def __init__(self, logger_name: str, logger_category: str) -> None:
        # Initialize the instance only once
        if not hasattr(self, 'initialized'):  # Check if the instance is already initialized
            self.initialized = True  # Set the flag to indicate it's initialized

            self.logger_name_ = logger_name
            self.logger_category_ = logger_category
            self.__logger_ = logging.getLogger(logger_name)
            self.__logger_.setLevel(logging.DEBUG)

            # Create a formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            # Ensure the directory for log file exists
            log_file_path = os.path.join(DEFAULT_LOG_PATH, "telegram-bot.log")
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

            # Create a file handler
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')

            # Add the formatter to the file handler
            file_handler.setFormatter(formatter)

            # Add the file handler to the logger
            self.__logger_.addHandler(file_handler)

    def __call__(self, level: int, message: str, verbose=False) -> None:
        self.log(level, message, verbose=verbose)

    def log(self, level: int, message: str, verbose = False) -> None:

        if not verbose:
            formatted_msg = self.logger_category_ + ": " + message
            self.__logger_.log(level, formatted_msg)

        elif VERBOSE_LOGGING:
            formatted_msg = self.logger_category_ + ": " + message
            self.__logger_.log(level, formatted_msg)

    def raise_exception_with_log(self, exception_type) -> None:
        formatted_msg = self.logger_category_ + ": " + str(exception_type)
        self.__logger_.log(logging.ERROR, formatted_msg)

        raise exception_type
