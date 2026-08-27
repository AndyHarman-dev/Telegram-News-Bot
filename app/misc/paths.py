import logging
import os
from app.misc.log_helper import LogHelper

LOG_PATHS = LogHelper(__name__, "Paths Thread")


class Paths:
    """Custom project path manager"""

    # Take the dirname of an element: root/app (3)/misc (2)/path.py (1)
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    _MAIN_DIR_BASENAME = 'app'
    _SAVED_DIR_BASENAME = 'saved'

    @staticmethod
    def combine(*args):
        return os.path.join(*args)

    @staticmethod
    def exists(path):
        return os.path.exists(path)

    @staticmethod
    def ensure_path(path):
        try:
            if not Paths.exists(path):
                os.makedirs(path)
            return path
        except PermissionError:
            LOG_PATHS.log(logging.ERROR, f"Permission to create path {path} was denied")
            return None
        except Exception as e:
            LOG_PATHS.log(logging.ERROR, f"Can't create path {e}")

    @staticmethod
    def get_main_dir():
        return Paths.combine(Paths.ROOT_DIR, Paths._MAIN_DIR_BASENAME)

    @staticmethod
    def get_saved_dir():
        return Paths.combine(Paths.ROOT_DIR, Paths._SAVED_DIR_BASENAME)


def main():
    pass


if __name__ == "__main__":
    main()
