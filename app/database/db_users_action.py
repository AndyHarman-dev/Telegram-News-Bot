from app.database.db_helper import DatabaseHelper
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
from app.misc import log_helper
from pathlib import Path


LOG = log_helper.LogHelper(__name__, "db_user_action")

#Action_type
# start
# send_message
# generate_image
# gather_news

class UserActionManager:



    @staticmethod
    def create_user_action(user_id, action_type):
        query = """
            INSERT INTO users_action (user_id, action_type)
            VALUES (?, ?)
        """
        DatabaseHelper.safe_execute_query(query, (user_id, action_type))

    @staticmethod
    def plot_stat(days_ago, save_path="last_n_days_action_stats.png"):
        end_date = datetime.now().date()  # Today's date as the end date
        start_date = end_date - timedelta(days=days_ago)  # Calculate the start date by going back 'days_ago' days
        return UserActionManager.plot_user_action_stats(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), save_path)

    @staticmethod
    def get_user_action_stats_by_date(start_date, end_date):
        """
        Gets user activity statistics for the specified period, grouped by date and action type.
        :param start_date: The start date of the period (string in 'YYYY-MM-DD' format)
        :param end_date: The end date of the period (string in 'YYYY-MM-DD' format)
        :return: Returns activity data in the form of a dictionary {action_type: {date: count}}
        """
        query = """
            SELECT action_type, date(date) as action_date, COUNT(*) as count
            FROM users_action
            WHERE date BETWEEN ? AND ?
            GROUP BY action_type, action_date
        """
        result = DatabaseHelper.safe_execute_query_dict(query, (start_date, end_date))

        # Dictionary structure: {action_type: {date: count}}
        action_data = defaultdict(lambda: defaultdict(int))

        for row in result:
            action_type = row['action_type']
            action_date = row['action_date']
            action_data[action_type][action_date] = row['count']

        return action_data

    @staticmethod
    def plot_user_action_stats(start_date, end_date, save_path="action_stats_plot.png"):

        # database static path
        full_path = Path(__file__).resolve().parent.parent.parent /'saved' / save_path

        # Retrieve user activity statistics within the specified period
        action_stats = UserActionManager.get_user_action_stats_by_date(start_date, end_date)

        # Check if there are any results to plot
        if not action_stats:
            LOG.error("No data to plot.")
            return None

        # Output the action counts by type and date to the console
        print("Action counts by type and date:")
        for action_type, dates in action_stats.items():
            print(f"Action Type: {action_type}")
            for date, count in sorted(dates.items()):
                print(f"  Date: {date}, Count: {count}")

        # Set up the plot with a specified size
        plt.figure(figsize=(10, 6))

        # Create a date range from the start date to the end date
        date_range = pd.date_range(start=start_date, end=end_date)

        # Iterate over each action type and its corresponding dates and counts
        for action_type, date_counts in action_stats.items():
            # Convert the dictionary to a DataFrame
            df = pd.DataFrame(list(date_counts.items()), columns=['Date', 'Count'])
            df['Date'] = pd.to_datetime(df['Date'])

            # Set the date as the index and reindex the DataFrame with the full date range, filling missing values with zero
            df = df.set_index('Date').reindex(date_range, fill_value=0)

            # Plot the data for each action type
            plt.plot(df.index, df['Count'], label=action_type)

        # Configure the format of the date on the x-axis
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))  # Set an interval of one day
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

        # Set the x-axis limits to match the start and end dates
        plt.xlim(pd.to_datetime(start_date), pd.to_datetime(end_date))

        # Set labels and title of the plot
        plt.xlabel('Date')
        plt.ylabel('Count')
        plt.title(f'User Actions from {start_date} to {end_date}')

        # Add a legend and rotate the date labels for better readability
        plt.legend(title="Action Types")
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save the plot to a file
        plt.savefig(full_path)
        plt.close()  # Close the plot to free up memory

        # Return the path of the saved image file
        return full_path


if __name__ == '__main__':
    #UserActionManager.create_user_action(12345, 'start')
    #UserActionManager.create_user_action(12346, 'start')
    #UserActionManager.create_user_action(12347, 'start')
    #UserActionManager.create_user_action(12348, 'start')
    #UserActionManager.create_user_action(12345, 'send_message')
    #UserActionManager.create_user_action(12346, 'send_message')
    #UserActionManager.create_user_action(12347, 'send_message')
    #UserActionManager.create_user_action(12348, 'send_message')


    #image_path = UserActionManager.plot_user_action_stats("2024-08-01", "2024-11-01")
    image_path = UserActionManager.plot_stat(14)  # Plotting the user action statistics for the last 30 days
    if image_path:
        print(f"Plot saved at {image_path}")

