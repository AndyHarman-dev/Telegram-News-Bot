import asyncio
import os
from dotenv import load_dotenv
import datetime

from app.database.db_init import tariffs, currency_map

from app.database.db_helper import DatabaseHelper
from app.misc.log_helper import LogHelper

LOG_USER_USAGE = LogHelper(__name__, "User Usage Thread")

class TariffManager():


    @staticmethod
    def get_tariffs_dict():
        """
        Retrieve all tariffs from the database and return a dictionary where keys are tariff IDs and values are tariff names.
        """
        query = """
            SELECT tariff_id, name FROM tariffs
        """
        result = DatabaseHelper.safe_execute_query(query)

        # Создаем словарь, используя идентификаторы тарифов в качестве ключей и имена тарифов в качестве значений
        tariff_names = {row[1]: str(row[0]) for row in result}

        return tariff_names

    @staticmethod
    def get_tariffs_info():
        """
        Retrieve all tariffs from the database and return a dictionary where keys are tariff IDs and values are tariff names.
        """
        query = """
            SELECT * FROM tariffs
        """
        result = DatabaseHelper.safe_execute_query(query)

        return result

    @staticmethod
    def get_tariff(user_id):
        """
        Retrieves the tariff ID for the given user ID.

        :param user_id: The ID of the user
        :return: The tariff ID associated with the user ID
        """
        query = """
            SELECT tariff_id FROM users_usages
            WHERE user_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (user_id,))
        return result[0][0]

    @staticmethod
    def get_tariff_descriptions():
        """
        Generate tariff descriptions for each tariff, including daily and monthly message quotas, and available channels.
        Return a list of description strings for each tariff.
        """
        descriptions = []
        for index, tariff in enumerate(tariffs, start=1):
            description = f"**{tariff['name']}**: Begin your journey with our {tariff['name'].lower()} plan, providing a daily message quota of {tariff['daily_messages_quota']} messages and a monthly allowance of {tariff['monthly_messages_quota']} messages. Ideal for those taking their first steps into messaging automation.\n\n"
            description += f"Elevate your messaging experience with our {tariff['name']} plan. Enjoy {tariff['daily_messages_quota']} messages per day and a generous monthly quota of {tariff['monthly_messages_quota']} messages. Plus, gain access to {tariff['channels_quota']} channels for wider outreach.\n\n"
            description += f"Take your messaging strategy to new heights with our {tariff['name']} plan. Benefit from {tariff['daily_messages_quota']} messages daily and a substantial monthly limit of {tariff['monthly_messages_quota']} messages. Additionally, unlock exclusive access to {tariff['channels_quota']} channels for expanded reach and engagement.\n\n"
            description += f"Unleash the power of messaging automation with our {tariff['name']} plan. Enjoy an impressive daily message quota of {tariff['daily_messages_quota']} messages, complemented by a significant monthly limit of {tariff['monthly_messages_quota']} messages. Access up to {tariff['channels_quota']} channels to maximize your impact and connect with your audience like never before.\n\n"
            descriptions.append(description)
        return descriptions


    @staticmethod
    def get_exchange_rate(currency):
        """
        Get the exchange rate for the given currency using an internal dictionary.
        If the currency is not found, return 1000.

        Args:
            currency (str): The currency to get the exchange rate for.

        Returns:
            float: The exchange rate for the given currency if found, otherwise 1000.
        """
        # Accessing the currency map to find the exchange rate
        return currency_map.get(currency, 1000)



    @staticmethod
    def get_tariff_price(tariff_id):
        """
        Get the price of the tariff with the given ID.

        Args:
            tariff_id (int): The ID of the tariff.

        Returns:
            float: The price of the tariff.
        """
        query = "SELECT price FROM tariffs WHERE tariff_id = ?"
        result = DatabaseHelper.safe_execute_query(query, (tariff_id,))
        if result:
            return float(result[0][0])
        else:
            return None  # Return None if no tariff with the given ID is found

    @staticmethod
    def get_payment_methods():
        """
        Get payment methods and their tokens from environment variables.

        Returns:
            dict: A dictionary containing payment methods as keys and their tokens as values.
        """
        load_dotenv()

        # get environment variables for PAYMENT_METHODS
        payment_methods_str = os.getenv('PAYMENT_METHODS')

        payment_methods = payment_methods_str.split(',')

        payment_tokens = {}

        # get environment variables for each payment method
        for method in payment_methods:
            token_var_name = f"{method}_TOKEN"
            token = os.getenv(token_var_name)
            if token:
                payment_tokens[method] = token

        return payment_tokens

    @staticmethod
    def get_provider_currencies(provider_name):
        """
        Get a list of available currencies for the given provider from environment variables.

        Args:
            provider_name (str): The name of the provider.

        Returns:
            list: A list containing the available currencies for the provider.
        """
        load_dotenv()

        # Construct the environment variable name
        env_var_name = f"{provider_name.upper()}_CURR"

        # Get the environment variable value
        currencies_str = os.getenv(env_var_name)

        if currencies_str:
            # Parse the currencies, assuming they are separated by commas and enclosed in quotes
            currencies = [currency.strip().strip('"') for currency in currencies_str.split(',')]

            if len(currencies) == 0:
                LOG_USER_USAGE.raise_exception_with_log(ValueError(f"Couldn't form a list of currencies for {provider_name}."
                                                                   f"Might be a typo?"))

            return currencies
        else:
            LOG_USER_USAGE.raise_exception_with_log(ValueError(f"No currencies found for {provider_name}"))


    @staticmethod
    def create_user_usage(user_id):
        """
        Creates a user usage record in the database.

        Args:
            user_id (int): The ID of the user.

        Returns:
            None
        """
        query = """
            INSERT OR IGNORE INTO users_usages (user_id, tariff_id, daily_messages_sent, monthly_messages_sent)
            VALUES (?, ?, ?, ?)
        """
        DatabaseHelper.safe_execute_query(query, (user_id, 1, 0, 0))


    @staticmethod
    def set_tariff(user_id, tariff):
        """
        Update the tariff for a specific user.

        Args:
            user_id (int): The ID of the user.
            tariff (int): The ID of the new tariff.

        Returns:
            None
        """
        query = """
            UPDATE users_usages
            SET tariff_id = ?,
                activation_date = ?
            WHERE user_id = ?
        """
        current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        DatabaseHelper.safe_execute_query(query, (tariff, current_date, user_id))

    @staticmethod
    def add_usage_to_user(user_id, usage=1):
        """
        Updates the usage for a specific user in the database.

        :param user_id: int, the id of the user
        :param usage: int, the amount to increase the user's usage (default 1)
        :return: None
        """
        query = """
            UPDATE users_usages
            SET daily_messages_sent = daily_messages_sent + ?, monthly_messages_sent = monthly_messages_sent + ?
            WHERE user_id = ?      
        """
        DatabaseHelper.safe_execute_query(query, (usage, usage, user_id))
        return

    @staticmethod
    def has_user_exceeded_quota(user_id):
        """
        Check if the user has exceeded the daily or monthly message quota.
        :param user_id: The ID of the user to check the quota for.
        :return: A boolean indicating if the user has exceeded the quota.
        """
        from app.misc.admin.admin_manager import AdminManager
        if str(user_id) in AdminManager.get_admins():
            return False

        query = """
        SELECT
            uu.daily_messages_sent >= t.daily_messages_quota AS daily_exceeded,
            uu.monthly_messages_sent >= t.monthly_messages_quota AS monthly_exceeded
        FROM users_usages uu
        INNER JOIN tariffs t ON uu.tariff_id = t.tariff_id
        WHERE uu.user_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (user_id,))

        if result:
            daily_exceeded, monthly_exceeded = result[0]
            return daily_exceeded or monthly_exceeded
        else:
            # Handle the case where the user does not exist or another error occurs
            print("Error or no data found for user")
            return False  # Assuming no quota exceeded if user or tariff data is missing

    @staticmethod
    def has_user_exceeded_monthly_quota(user_id):
        """
        Check if the user has exceeded the monthly message quota.
        :param user_id: The ID of the user to check the quota for.
        :return: A boolean indicating if the user has exceeded the monthly quota.
        """
        from app.misc.admin.admin_manager import AdminManager
        if str(user_id) in AdminManager.get_admins():
            return False

        query = """
        SELECT
            uu.monthly_messages_sent >= t.monthly_messages_quota AS monthly_exceeded
        FROM users_usages uu
        INNER JOIN tariffs t ON uu.tariff_id = t.tariff_id
        WHERE uu.user_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (user_id,))

        if result:
            monthly_exceeded = result[0][0]
            return monthly_exceeded
        else:
            # Handle the case where the user does not exist or another error occurs
            print("Error or no data found for user")
            return False  # Assuming no quota exceeded if user or tariff data is missing

    @staticmethod
    def clear_all_daily_messages_sent():
        """
        Asynchronously clears all daily messages sent by updating the users_usages table.
        """
        query = """
        UPDATE users_usages
        SET daily_messages_sent = 0
        """
        DatabaseHelper.safe_execute_query(query)

    #TODO pipeline to update usage and balance in payment and


async def myFunc():
    # result = TariffManager.has_user_exceeded_quota(466001259)
    # TariffManager.add_usage_to_user(466001259)
    # print(result)

    currs = TariffManager.get_provider_currencies("TEST_KASSA")
    print(currs)


if __name__ == '__main__':
    asyncio.run(myFunc())

    # tariff_descriptions = TariffManager.generate_tariff_descriptions()
    # print("Tariff Descriptions: ",tariff_descriptions)

    # Пример использования функции
    # payment_tokens = TariffManager.get_payment_methods()
    # print(payment_tokens)

    #price = TariffManager.get_tariff_price(3)
    #print(price)

    #provider_token = TariffManager.get_payment_methods()

    #provider_list = list(provider_token.keys())
    #print(provider_list)


    #print(TariffManager.get_tariffs_dict() )