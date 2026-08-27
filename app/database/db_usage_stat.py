from datetime import datetime,timedelta
from app.database.db_helper import DatabaseHelper


class UsageStatManager():
    @staticmethod
    def update_last_activity(user_id):
        # Получаем текущее время
        current_time = datetime.now()

        # Форматируем время в формат, подходящий для SQL (например, 'YYYY-MM-DD HH:MM:SS')
        formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')

        # SQL запрос для обновления времени последней активности
        query = """
                UPDATE users_usages
                SET last_activity = ?
                WHERE user_id = ?
            """
        DatabaseHelper.safe_execute_query(query, (formatted_time, user_id))

    @staticmethod
    def count_active_users(n_days):
        # Вычисляем дату, начиная с которой будем считать активных пользователей
        date_n_days_ago = datetime.now() - timedelta(days=n_days)
        formatted_date = date_n_days_ago.strftime('%Y-%m-%d %H:%M:%S')

        # SQL запрос для подсчета активных пользователей
        query = """
                SELECT COUNT(DISTINCT user_id)
                FROM users_usages
                WHERE last_activity >= ?
            """
        result = DatabaseHelper.safe_execute_query(query, (formatted_date,))
        # return resulting count
        return result[0][0] if result else 0

    @staticmethod
    def inc_user_usage(user_id, column_name):
        # available values:
        #daily_messages_sent, monthly_messages_sent, monthly_images_generated, monthly_news_gathered

        UsageStatManager.update_last_activity(user_id)

        query = f"UPDATE users_usages SET {column_name} = {column_name} + 1 WHERE user_id = ?"
        DatabaseHelper.safe_execute_query(query, (user_id,))

    @staticmethod
    def get_stats():
        query = "SELECT * FROM users_usages"
        return DatabaseHelper.safe_execute_query(query)


    @staticmethod
    def average_user_activity(n_days):
        # Получаем дату за последние n дней
        date_n_days_ago = datetime.now() - timedelta(days=n_days)
        formatted_date = date_n_days_ago.strftime('%Y-%m-%d %H:%M:%S')

        # SQL запрос для получения суммы по каждой активности и количества активных пользователей
        query = f"""
                    SELECT SUM(daily_messages_sent), SUM(monthly_messages_sent),
                           SUM(monthly_images_generated), SUM(monthly_news_gathered), COUNT(DISTINCT user_id)
                    FROM users_usages
                    WHERE last_activity >= ?
                """
        result = DatabaseHelper.safe_execute_query(query, (formatted_date,))

        if not result or not result[0][0]:  # Проверка на пустой результат или нулевую активность
            return "No active users or no activity in the last {} days".format(n_days)

        # Расчет средних значений для каждого типа активности
        daily_msg_avg = result[0][0] / result[0][4]
        monthly_msg_avg = result[0][1] / result[0][4]
        images_avg = result[0][2] / result[0][4]
        news_avg = result[0][3] / result[0][4]

        return {
            'Total active users': result[0][4],
            'Average daily messages sent': daily_msg_avg,
            'Average monthly messages sent': monthly_msg_avg,
            'Average monthly images generated': images_avg,
            'Average monthly news gathered': news_avg
        }


if __name__ == '__main__':
    n_days = 30
    average_activity = UsageStatManager.average_user_activity(n_days)
    print(f"Average user activity over the last {n_days} days: {average_activity}")