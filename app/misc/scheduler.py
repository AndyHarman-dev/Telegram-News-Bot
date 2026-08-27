import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
import pytz
import datetime
from typing import Callable
from app.misc.log_helper import LogHelper
from app.bot.config import SERVER_REGION

LOG_SCHEDULER = LogHelper(__name__, "Scheduler Thread")


class Scheduler:
    """
    This class is designed to manage and execute tasks based on a schedule. It uses the APScheduler library to handle
    the scheduling of tasks and the pytz library to handle timezone conversions. The class maintains a dictionary of
    tasks, where each task is associated with its corresponding job object from the APScheduler library.
    """

    def __init__(self):
        """This is the constructor of the Scheduler class. It initializes an empty dictionary self.tasks to store the
        tasks that will be scheduled and initializes the APScheduler."""
        self.tasks = {}
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def schedule_task(self, task: Callable, interval, unit, *args):
        """
        This function schedules a task to be executed at a regular interval. The task parameter is the function to be
        executed, interval is the length of time between executions, and unit is the unit of time for the interval (
        e.g., 'seconds', 'minutes', 'hours'). The function adds the task to the self.tasks dictionary.
        """
        trigger = IntervalTrigger(**{unit: interval})
        job = self.scheduler.add_job(task, trigger, args=args)
        self.tasks[task.__name__] = job

    def get_scheduled_tasks(self):
        """This function returns the self.tasks dictionary, which contains all the currently scheduled tasks."""
        return self.tasks

    def schedule_task_at(self, task: Callable, date_time_str, user_region, *args):
        """
        This function schedules a task to be executed at a specific point in time. The task parameter is the function
        to be executed, and date_time_str is a string representing the date and time when the task should be
        executed, in the format 'YYYY-MM-DD HH:MM:SS'. The function converts the date and time to the user's local
        timezone and adds the task to the self.tasks dictionary.

        Example of date_time_str : "2024-01-04 12:00:00"
        """

        # Parse the string into a naive datetime object
        naive_datetime_obj = datetime.datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")

        # Assume the original datetime is in UTC
        utc_timezone = pytz.timezone(user_region)
        utc_datetime_obj = utc_timezone.localize(naive_datetime_obj)

        # Convert to another timezone, e.g., US/Eastern
        server_timezone = pytz.timezone(SERVER_REGION)
        server_timezone_obj = utc_datetime_obj.astimezone(server_timezone)

        LOG_SCHEDULER.log(logging.INFO, f"Original UTC Time {utc_datetime_obj}")
        LOG_SCHEDULER.log(logging.INFO, f"Converted Time to server timezone {server_timezone_obj}")

        # Schedule the task at the specific time
        trigger = DateTrigger(run_date=server_timezone_obj)
        job = self.scheduler.add_job(task, trigger, args=args)
        self.tasks[task.__name__] = job

    def reset_schedule(self):
        """This function clears all scheduled tasks. It uses the remove_all_jobs function from the APScheduler library to remove
        all jobs from the schedule."""
        self.scheduler.remove_all_jobs()
        self.tasks.clear()

    def remove_task(self, task_name):
        """
        This function removes a specific task from the schedule. The task_name parameter is the name of the task to
        be removed. If the task is in the self.tasks dictionary, the function cancels the corresponding job and
        removes the task from the dictionary.
        """
        if task_name in self.tasks:
            job = self.tasks[task_name]
            job.remove()
            del self.tasks[task_name]

    def stop(self):
        """Stops the scheduler and all running jobs."""
        self.scheduler.shutdown()


# def print_hello_10():
#     print("Hello 10!")
#
#
# def print_hello_with_arg(arg):
#     print("Hello with ", arg)
#
#
# def main():
#     # Creating an instance of scheduler
#     scheduler = Scheduler()
#
#     # Schedule a repetitive task every 10 sec
#     scheduler.schedule_task(print_hello_10, 10, 'seconds')
#
#     # Schedule a one-shot task at a specific date
#     desired_date = input("Enter a desired date in a format (year-month-day hour:minute:second)")
#     current_user_region = input("Enter current user's region in a format 'Continent/City'")
#
#     scheduler.schedule_task_at(print_hello_with_arg, desired_date, current_user_region, "This is my argument!")
#
#     # Since this thread does not do anything else, to avoid scheduler termination we will wait until it's done
#     try:
#         while True:
#             time.sleep(2)
#     except (KeyboardInterrupt, SystemExit):
#         scheduler.stop()
#
#
# if __name__ == "__main__":
#     main()
