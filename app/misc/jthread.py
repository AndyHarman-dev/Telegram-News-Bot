import threading
from app.misc.log_helper import LogHelper

LOG_JOINABLE_THREAD = LogHelper(__name__, "Joinable Thread Thread")


class JThread:
    """Jthread is an autojoinable thread
    that is joined as soon as exists its life-scope"""

    def __init__(self, target=None, args=(), daemon=False, b_auto_start=False):
        self.running_thread = threading.Thread(target=target, args=args, daemon=daemon)

        if b_auto_start:
            self.running_thread.start()

    def start(self):
        if not self.running_thread.is_alive():
            self.running_thread.start()
        else:
            LOG_JOINABLE_THREAD.raise_exception_with_log(ValueError("Thread was not initialized and created properly"))

    def join(self):
        if self.running_thread:
            self.running_thread.join()
        else:
            LOG_JOINABLE_THREAD.raise_exception_with_log(ValueError("Thread was not initialized and created properly"))

    def __del__(self):
        if self.running_thread.is_alive():
            self.running_thread.join()
