import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Bot

from app.misc.log_helper import LogHelper

LOG_ADMIN_MANAGER = LogHelper(__name__, "Admin Manager Thread")


class AdminManager:
    def __init__(self):
        self.admins = []

    def add_admin(self, admin):
        self.admins.append(admin)

    def remove_admin(self, admin):
        self.admins.remove(admin)

    @staticmethod
    def get_admins():
        load_dotenv()
        admin_user_ids = os.getenv('ADMIN_USER_IDS')
        if admin_user_ids:
            admins = admin_user_ids.split(',')
            return admins
        else:
            return []

    @staticmethod
    async def send_admin_message(message):
        load_dotenv()
        admin_id = 0
        try:
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            async with Bot(token=bot_token) as bot:
                admins = AdminManager.get_admins()
                for admin_id in admins:
                    await bot.send_message(chat_id=admin_id, text=message)
        except Exception as e:
            if admin_id:
                LOG_ADMIN_MANAGER.log(logging.ERROR, f"Error when sending a message to admin {admin_id}: {e}")
            else:
                LOG_ADMIN_MANAGER.log(logging.ERROR, f"Error during getting admin list: {e}")


if __name__ == "__main__":
    #asyncio.run(AdminManager.send_admin_message("they want to kill me"))
    pass
