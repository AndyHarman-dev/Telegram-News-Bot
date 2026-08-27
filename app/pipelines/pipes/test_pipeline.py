import asyncio
import logging
import time
from app.misc.jthread import JThread

from app.pipelines.pipeline import Pipeline


def external_task_to_process():
    time.sleep(4)
    print("External task processed")


class PipelineExample(Pipeline):
    """This test pipeline simulates work
    and executes different types of tasks"""

    def __init__(self, pipeline_tag, user_data: str):
        """Default pipeline init but also takes a custom user data"""
        super().__init__(pipeline_tag)
        self._custom_user_data = user_data

    def on_pipeline_begin(self):
        """Override on pipeline begin"""
        super().on_pipeline_begin()
        # Modify user data
        self._custom_user_data += str(" " + "P")

    def on_pipeline_end(self):
        super().on_pipeline_end()

    def main(self, *args, **kwargs):
        """Overriding main argument to define our pipeline."""
        # IMPORTANT ! We don't call the super as it is not supposed to be called

        time.sleep(0.7)  # Processing....
        self._custom_user_data = self.custom_task("I")

        time.sleep(0.5)  # More processing
        self._custom_user_data = self.custom_task("P")

        workers = []

        workers.append(JThread(target=self.heavy_processing, daemon=True, b_auto_start=True))
        workers.append(JThread(target=external_task_to_process, daemon=True, b_auto_start=True))

        WORKERS = 3
        for i in range(WORKERS):
            workers.append(JThread(target=self.async_custom_task, daemon=True, b_auto_start=True))

        self._custom_user_data = self.custom_task("L")

        self._custom_user_data = self.custom_task("I")

        self._custom_user_data = self.custom_task("N")

        self._custom_user_data = self.custom_task("E")

        # Gather all async tasks
        return self._custom_user_data

    def custom_task(self, appendix):
        new_str = self._custom_user_data + str("-" + appendix)
        return new_str

    def async_custom_task(self):
        time.sleep(0.3)  # Processing
        self._pipeline_logger.log(logging.INFO, "Async custom task has been processed!")

    def heavy_processing(self):
        time.sleep(5)
        self._pipeline_logger.log(logging.INFO, "Heavy processing is done!")


if __name__ == "__main__":
    pipeline_example = PipelineExample("pipeline_example", "Custom user data is: ")
    processed_data = pipeline_example.run()

    print(processed_data)
