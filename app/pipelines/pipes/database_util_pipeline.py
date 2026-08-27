import asyncio
from datetime import datetime

from app.pipelines.pipeline import Pipeline
from app.database.db_helper import DatabaseHelper

class Database_util(Pipeline):

    def __init__(self, pipeline_tag='database_util_pipeline'):
        super().__init__(pipeline_tag)

    def main(self, *args, **kwargs):
        """Called when pipeline is run"""

        asyncio.run(Database_util.clean_quotas())
        #Database_util.clean_quotas()

        return 0

    @staticmethod
    async def clean_quotas():
        Database_util.clean_daily_quota()
        Database_util.clean_monthly_quota()

        return
    @staticmethod
    def clean_daily_quota():
        """
        Asynchronously resets the daily quota for all users in the database.
        """
        query = "UPDATE users_usages SET daily_messages_sent = 0"
        DatabaseHelper.safe_execute_query(query)
        return

    @staticmethod
    def clean_monthly_quota():
        """
        Resets the monthly quota for all users in the database if today is the first day of the month.
        """
        today = datetime.now()
        if today.day == 1:  # reset quota if today is the first day of the month
            query = "UPDATE users_usages SET monthly_messages_sent = 0"
            DatabaseHelper.safe_execute_query(query)

        #TODO control separately each user

if __name__ == "__main__":
    asyncio.run(Database_util.clean_quotas())