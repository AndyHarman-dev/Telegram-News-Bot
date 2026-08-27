import asyncio
import logging
import time
from datetime import datetime

from app.misc.log_helper import LogHelper
from app.misc.scheduler import Scheduler
from app.misc.jthread import JThread


class Pipeline:
    start_time = datetime.now()  # .strftime("%Y-%m-%d %H:%M:%S")
    """Pipeline is a structural class that executes tasks
    within the class synchronously one by one or asynchronously

    Tasks are defined in a child class of a pipeline and are executed in the
    main function of a pipeline.

    The class itself is necessary for handling routine stuff that happens at the beginning of a pipeline
    and at the end of it such as logging of information or initializing some data
    """

    def __init__(self, pipeline_tag="pipeline_0"):
        self._on_finished_callable = None
        self._pipeline_tag = pipeline_tag
        self._pipeline_logger = LogHelper(pipeline_tag, "Pipeline Thread")
        self._pipeline_scheduler = Scheduler()
        self._b_done = False
        self._result = None  # User's return value from a pipeline
        self._pipeline_thread = None
        self._b_run_async = False

    def on_pipeline_begin(self):
        """Called when pipeline has begun"""
        self.start_time = datetime.now()
        start_time_str = self.start_time.strftime("%Y-%m-%d %H:%M:%S")
        self._pipeline_logger.log(logging.INFO, f"Enter pipeline {start_time_str}, tag: {self._pipeline_tag}")

    def on_pipeline_end(self):
        """Called when pipeline has ended"""

        end_time = datetime.now()
        elapsed_time = end_time - self.start_time

        # format time to string
        end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        elapsed_time_str = str(elapsed_time)

        self._pipeline_logger.log(logging.INFO,
                                  f"Finished pipeline {end_time_str}, duration: {elapsed_time_str}, tag: {self._pipeline_tag}")

        if self._on_finished_callable:
            self._on_finished_callable()
            self._b_done = True

    def main(self, *args, **kwargs):
        """Called when pipeline is run"""
        self._pipeline_logger.raise_exception_with_log(NotImplementedError("This pipeline does not implement main "
                                                                           "method and thus invalid!"))
        return 0

    async def main_async(self, *args, **kwargs):
        self._pipeline_logger.raise_exception_with_log(NotImplementedError("This pipeline does not implement main "
                                                                           "method and thus invalid!"))
        return 0

    def bind_on_pipeline_finished(self, on_finished):
        """Binds a callable object that is executed when the pipeline is finished"""
        self._on_finished_callable = on_finished

    def run(self, parallel=False, *args, **kwargs):
        """Runs the pipeline and returns the result of the pipeline"""
        try:
            # If not parallel, run synchronously
            if not parallel:
                return self._execute_run(*args, **kwargs)
            else:
                self._pipeline_thread = JThread(target=self._execute_run, args=(*args, *kwargs), daemon=True)
                self._pipeline_thread.start()
                self._pipeline_logger.log(logging.INFO, "Pipeline started in a parallel mode. The result of the work"
                                                        "can be got from get_result())")
        finally:
            self._b_done = True

    async def run_async(self, *args, **kwargs):
        """Runs the pipeline and returns the result of the pipeline"""
        return await self._execute_run_async(*args, **kwargs)

    def _execute_run(self, *args, **kwargs):
        self.on_pipeline_begin()
        self._result = self.main(*args, **kwargs)
        self.on_pipeline_end()
        return self._result

    async def _execute_run_async(self, *args, **kwargs):
        self.on_pipeline_begin()
        self._result = await self.main_async(*args, **kwargs)
        self.on_pipeline_end()
        return self._result

    def wait_for(self):
        """Joins this pipeline if it was run in a parallel mode"""
        if self._b_run_async:
            self._pipeline_logger.raise_exception_with_log(ValueError("Cannot wait for an async pipeline!"))

        if self._pipeline_thread:
            self._pipeline_logger.log(logging.INFO, "Waiting for this pipeline to finish...")
            self._pipeline_thread.join()

    def get_result(self):
        """Returns the result of the pipeline execution. Has no effect
        if the pipeline was run synchronously and already worked. If it was, this function
        will ensure the result by waiting for the completion and then providing the result"""

        if self._b_run_async:
            self._pipeline_logger.raise_exception_with_log(ValueError("Cannot get the result of an async pipeline!"))

        if self._pipeline_thread and self._pipeline_thread.is_alive():
            self.wait_for()

        return self._result

    def is_finished(self):
        return self._b_done


class DynamicPipeline(Pipeline):
    """Dynamic pipeline is a pipeline
    that is meant to be a local task solver within a certain
    scope."""

    _allow_instansiation = False
    _SYNC_TASK_TYPE = 'sync'
    _PARALLEL_TASK_TYPE = 'parallel'

    def __init__(self, pipeline_tag='dynamic_pipeline_0'):
        """This constructor is not supposed to be used by a user"""
        super().__init__(pipeline_tag)

        if DynamicPipeline._allow_instansiation:
            self.tasks = {}
            self._threads_pool = []
        else:
            self._pipeline_logger.raise_exception_with_log(
                ValueError("This class can't be instantiated directly!. If you want to have"
                           "this ability, then set "
                           "DynamicPipeline._allow_instansiation = true "
                           "before"
                           "constructing the instance"))

    @classmethod
    def create_pipeline(cls, pipeline_tag, setup_function):
        DynamicPipeline._allow_instansiation = True
        instance = cls(pipeline_tag)
        DynamicPipeline._allow_instansiation = False

        setup_function(instance)

        return instance

    def main(self, *args, **kwargs):
        """Main function in DynamicPipeline is not supposed to be overriden as
        it handles the tasks execution"""
        for task_tuple in self.tasks.values():
            task_type, task_callable = task_tuple
            if task_type == DynamicPipeline._SYNC_TASK_TYPE:
                task_callable(*args, **kwargs)
            elif task_type == DynamicPipeline._PARALLEL_TASK_TYPE:
                thread = JThread(target=task_callable, args=(args, kwargs), daemon=True)
                thread.start()
                self._threads_pool.append(thread)
            else:
                self._pipeline_logger.raise_exception_with_log(ValueError("Undefined task type! Tasks can be only"
                                                                          "'sync' or 'parallel'"))
        if self._threads_pool:
            del self._threads_pool

    def task(self, tag: str, callable_task):
        """Adds a task to the tasks dictionary of execution. If
        the tag's empty, then the task name will match the callable funciton
        name"""
        self._add_task_internal(tag, callable_task, DynamicPipeline._SYNC_TASK_TYPE)

    def parallel_task(self, tag: str, callable_task):
        """Adds a task to the tasks dictionary of execution but however
        it will be run on a separate thread and will not stop the pipeline
        main execution untill it reaches its end. All parallel tasks are safe to
        use but however it's on the user to make sure the data between the tasks is thread-safe
        all the tasks are autojoinable as soon as the pipeline hits the end"""
        self._add_task_internal(tag, callable_task, DynamicPipeline._PARALLEL_TASK_TYPE)

    def wait(self, delay):
        """Simply stops execution on a 'delay' amount of secodns"""

        def wait_task():
            time.sleep(delay)

        self.task('internal_wait_task', wait_task)

    def wait_all_parallels(self):
        """Wait for all parallels to finish"""

        def execute():
            for thread in self._threads_pool:
                thread.join()

        self.task('internal_wait_all_parallels', execute)

    def _add_task_internal(self, tag, callable_task, execution_type):
        task_key = tag if len(tag) != 0 else callable_task.__name__
        self.tasks[task_key] = (execution_type, callable_task)


if __name__ == "__main__":
    def heavy_test_func():
        # Tasks for heavy workload simulation
        time.sleep(5)
        print('Heavy test func is done!')


    def setup_dynamic_pipeline(pipeline_ref):
        pipeline_ref.task("Init", lambda: print("First task is executed!"))

        pipeline_ref.wait(2)

        pipeline_ref.parallel_task("Heavy task 1", heavy_test_func)
        pipeline_ref.parallel_task("Heavy task 2", heavy_test_func)

        pipeline_ref.wait(2)

        pipeline_ref.wait_all_parallels()

        pipeline_ref.task('End', lambda: print("All done!"))


    dynamic_pipeline = DynamicPipeline.create_pipeline('test_dynamic', setup_dynamic_pipeline)
    dynamic_pipeline.run()

    dynamic_pipeline.wait_for()
