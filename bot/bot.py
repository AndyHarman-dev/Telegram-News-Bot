from telegram import Update, ForceReply
from telegram.ext import filters, CommandHandler, MessageHandler, ContextTypes, Application
from misc.log_helper import LogHelper, logging

# Create log helper and category for it
TG_LOG_BOT = LogHelper(__name__, "Bot thread")


# Interface for interacting with TG Bot
class TelegramBot:
    def __init__(self, token: str, bot_username: str) -> None:

        # Validate token
        if token == '':
            err_msg = "Token cannot be empty. Exception is raised!"
            TG_LOG_BOT.log(logging.ERROR, err_msg)
            raise ValueError(err_msg)

        self.__token = token
        self.__bot_username = bot_username

        self.__create_application()
        TG_LOG_BOT.log(logging.INFO, "Bot initialized")

    # Creates telegram application and add handlers
    def __create_application(self):
        self.__app = Application.builder().token(self.__token).build()

        self.__app.add_handlers(
            [
                CommandHandler("start", self.start_handle),
                CommandHandler("help", self.help_handle),
                MessageHandler(filters.TEXT, self.handle_message)
            ]
        )

        self.__app.add_error_handler(self.error)

    # Handles response
    async def handle_response(self, text: str) -> str:
        return "Response handled!"

    # TG Functions ==============================================================

    # Start
    async def start_handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        TG_LOG_BOT.log(logging.INFO, f"User {user.first_name} started the bot")
        await update.message.reply_text(
            "Hello! I am an AI, Social Media Manager. I am going to manage all your social media for you so that you will have free time to spend on something important")

    # Help
    async def help_handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        TG_LOG_BOT.log(logging.INFO, f"User {user.first_name} started the bot")
        await update.message.reply_text('Help Command')  # fullfll the command

    # Handles TG Message
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message_type: str = update.message.chat.type
        text: str = update.message.text

        TG_LOG_BOT.log(logging.INFO, f"Message received from user {update.message.chat.id} in {message_type}: {text}")

        if message_type == 'group':
            if self.__bot_username in text.lower():
                new_text: str = text.replace(self.__bot_username, "").strip()
                response = await self.handle_response(new_text)
            else:
                return
        else:
            response = await self.handle_response(text)

        TG_LOG_BOT.log(logging.INFO, f"Response from bot sent to user {update.message.chat.id}: {response}")
        await update.message.reply_text(response)

    # Handle error
    async def error(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log Errors caused by Updates."""
        TG_LOG_BOT.log(logging.ERROR, f"Update {update} caused error {context.error}")

    # Run the bot and starts polling
    def run(self):

        # Validate application
        if not isinstance(self.__app, Application):
            err_msg: str = "Application was not created properly! Cannot run the bot"
            TG_LOG_BOT.log(logging.ERROR, err_msg)
            raise ValueError(err_msg)

        # Start the bot
        TG_LOG_BOT.log(logging.INFO, "Run telegram bot")
        TG_LOG_BOT.log(logging.INFO, "Polling...")

        self.__app.run_polling(poll_interval=3)
