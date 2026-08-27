import sys
import time
import subprocess
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.misc.log_helper import LogHelper
from app.misc.paths import Paths

LOG_WATCHDOG = LogHelper(__name__, "Watchdog Thread")


class ScriptRestartHandler(FileSystemEventHandler):
    def __init__(self, script_path):
        self.script_path = script_path
        self.process = None
        self.start_script()

    def start_script(self):
        if self.process:
            self.process.terminate()
        self.process = subprocess.Popen([sys.executable, self.script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        LOG_WATCHDOG(logging.INFO, "Started script: {self.script_path}")

    def on_modified(self, event):
        if event.src_path.endswith(self.script_path):
            LOG_WATCHDOG(logging.INFO, f"Detected modification in {self.script_path}. Restarting script.")
            self.start_script()

    def check_script(self):
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            LOG_WATCHDOG(logging.ERROR, f"Script {self.script_path} terminated with exit code {self.process.returncode}.")
            LOG_WATCHDOG(logging.ERROR, f"Standard Output: {stdout.decode()}")
            LOG_WATCHDOG(logging.ERROR, f"Standard Error: {stderr.decode()}")
            time.sleep(5)  # Delay before restarting to avoid rapid restarts
            LOG_WATCHDOG(logging.INFO, "Restarting script.")
            self.start_script()


def main():
    script_path = Paths.ROOT_DIR + "/app/main.py"  # Path to the script you want to monitor and restart
    event_handler = ScriptRestartHandler(script_path)
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    LOG_WATCHDOG(logging.INFO, f"Watching for changes in {script_path}...")

    try:
        while True:
            event_handler.check_script()
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
