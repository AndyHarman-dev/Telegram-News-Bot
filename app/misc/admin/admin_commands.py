import json
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import CallbackContext, ContextTypes

from app.bot.telegram_helper import TelegramHelper
from app.database.db_users_action import UserActionManager
from app.misc.log_helper import LogHelper
from app.misc.paths import Paths
from app.database.db_user import UserManager
from app.database.db_chat import ChatManager
# for commands visibility scope
from app.pipelines.pipes.database_util_pipeline import Database_util
from app.database.db_tariff import TariffManager

from app.database.db_chat import ChatManager

from app.database.db_usage_stat import UsageStatManager

ADMIN_COMMANDS_LOG = LogHelper(__name__, "Admin Commands Thread")


class AdminCommands:
    def __init__(self):
        pass


    @staticmethod
    async def execute_dynamic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if not AdminCommands.is_admin(user_id):
            await update.effective_message.reply_text("Вы не имеете права использовать эту команду.")
            return

        command_text = update.effective_message.text.lstrip('/execute ')

        # Проверяем, что пользователь пытается выполнить команду в консоли
        if "os." in command_text or "exec(" in command_text:
            await update.effective_message.reply_text("Вы не можете выполнять данную команду.")
            return

        # Execute custom command with inputs
        if command_text.startswith("get_logs"):
            await AdminCommands.get_logs(update, context)
            return


        # Execute the command
        try:
            exec(command_text)
            await update.effective_message.reply_text("Команда выполнена.")
        except Exception as e:
            await update.effective_message.reply_text(f"Ошибка выполнения команды: {e}")


    @staticmethod
    async def execute_dynamic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if not AdminCommands.is_admin(user_id):
            await update.effective_message.reply_text("You do not have permission to use this command.")
            return

        command_text = update.effective_message.text.lstrip('/execute ')

        # Check if the user is trying to execute a command in the console
        if "os." in command_text or "exec(" in command_text:
            await update.effective_message.reply_text("You cannot execute this command.")
            return

        # Execute custom command with inputs
        if command_text.startswith("get_logs"):
            await AdminCommands.get_logs(update, context)
            return
        elif command_text.startswith("get_stat"):
            await AdminCommands.get_stat(update, context)
            return
        elif command_text.startswith("block_user"):
            await AdminCommands.tg_block_user(update, context)
            return

        # Execute the command
        try:
            output = eval(command_text)
            if output:
                await update.effective_message.reply_text(f"Command executed. Output: {output}")
            else:
                await update.effective_message.reply_text("Command executed.")
        except Exception as e:
            await update.effective_message.reply_text(f"Error executing command: {e}")

    @staticmethod
    def is_admin(user_id) -> bool:
        """
        Check if the user is an admin based on the provided user ID.

        Args:
            user_id (str): The user ID to be checked.

        Returns:
            bool: True if the user is an admin, False otherwise.
        """
        load_dotenv()
        admin_user_ids = os.getenv('ADMIN_USER_IDS')
        if admin_user_ids:
            admins = admin_user_ids.split(',')
            return str(user_id) in admins
        else:
            return False

    @staticmethod
    async def get_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Asynchronously sends the log document to the user identified by the given update.
        Parameters:
            - update: The update object containing information about the user.
            - context: The context object for handling the update.
        Return:
            None
        """
        try:
            log_path = Paths.ROOT_DIR + "/saved/logs/telegram-bot.log"
            user_id = update.effective_user.id
            await context.bot.send_document(chat_id=user_id, document=log_path)
        except Exception as error:
            ADMIN_COMMANDS_LOG.log(logging.ERROR, "Error sending logs: " + error)
        return
    @staticmethod
    async def get_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Asynchronously sends the log document to the user identified by the given update.
        Parameters:
            - update: The update object containing information about the user.
            - context: The context object for handling the update.
        Return:
            None
        """
        try:
            file_path = Paths.ROOT_DIR + "/smm_data_base.db"
            user_id = update.effective_user.id
            await context.bot.send_document(chat_id=user_id, document= file_path)
        except Exception as error:
            print("Error sending db" + error)
        return


    async def get_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Asynchronously sends the log document to the user identified by the given update.
        Parameters:
            - update: The update object containing information about the user.
            - context: The context object for handling the update.
        Return:
            None
        """
        args = context.args[1:]

        try:
            days = int(args[0])
            plot_image_path = UserActionManager.plot_stat(days)
            user_id = update.effective_user.id
            await context.bot.send_document(chat_id=user_id, document=plot_image_path)
        except Exception as error:
            ADMIN_COMMANDS_LOG.log(logging.ERROR, "Error sending stat: " + error)
        return


    @staticmethod
    async def tg_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):

        args = context.args[1:] # Remove the first argument, which is the command name

        if len(args) > 2:
            await update.effective_message.reply_text("You should specify only one argument.")
            return

        user_id = args[0]
        user_id = int(user_id) if user_id.isdigit() else user_id  # Convert user id to integer if it's a string of digits
        block_condition = eval(args[1])

        assert isinstance(user_id, int) or isinstance(user_id, str), "Invalid user id!"
        await AdminCommands.set_user_blocked(user_id, block_condition)
        await update.effective_message.reply_text(f"User was successfully {'blocked' if block_condition else 'unblocked'}!")

    @staticmethod
    async def set_user_blocked(user_identifier: int | str, is_blocked: int | bool) -> None:
        users = UserManager.get_all_users()
        if len(users) > 0:
            for user in users:
                # Either check by id or check by the username
                if user[0] == user_identifier or user[1] == user_identifier:
                    UserManager.set_user_blocked(user[0], bool(is_blocked))




if __name__ == "__main__":
    update = Update(1252909852)
    context = CallbackContext()
    update.message.text = "/execute  print(AdminCommands.is_admin(466001259)) "
    AdminCommands.execute_dynamic_command(update, context)