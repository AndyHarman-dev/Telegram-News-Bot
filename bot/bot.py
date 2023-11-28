import requests
from telegram import Update, ForceReply
from telegram.ext import filters, CommandHandler, MessageHandler, ContextTypes, Application
from misc.log_helper import LogHelper, logging
from config import config
from misc.pexels_library import PexelsAPI

# Create log helper and category for it
TG_LOG_BOT = LogHelper(__name__, "Bot thread")

# Text handles
START_MESSAGE_TEXT = config.CONFIG_DICT['start_message']
HELP_MESSAGE_TEXT = config.CONFIG_DICT['help_message']


# Helper function for getting telegram api url
def get_telegram_api_url(token: str) -> str:
    return f"https://api.telegram.org/bot{token}/"


# Helper function for getting telegram api url
def get_chat_id(bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    response = requests.get(url)
    data = response.json()
    if 'result' in data:
        for update in data['result']:
            chat_id = update['message']['chat']['id']
            return chat_id


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
    async def handle_response(self, text: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        response = PexelsAPI.test()

        url = f"https://api.telegram.org/bot{self.__token}/sendPhoto"
        data = {'chat_id': get_chat_id(self.__token),
                'photo': response.json()['photos'][0]['src']['original']}
        r = requests.post(url, data=data)
        return "Image"

    # TG Functions ==============================================================

    # Start
    async def start_handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        TG_LOG_BOT.log(logging.INFO, f"User {user.first_name} started the bot")
        await update.message.reply_text(START_MESSAGE_TEXT)

    # Help
    async def help_handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        TG_LOG_BOT.log(logging.INFO, f"User {user.first_name} started the bot")
        await update.message.reply_text(HELP_MESSAGE_TEXT)

    # Handles TG Message
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message_type: str = update.message.chat.type
        text: str = update.message.text

        TG_LOG_BOT.log(logging.INFO,
                       f"Message received from user {update.effective_user.first_name} in {message_type}: {text}")

        if message_type == 'group':
            if self.__bot_username in text.lower():
                new_text: str = text.replace(self.__bot_username, "").strip()
                response = await self.handle_response(new_text, update, context)
            else:
                return
        else:
            response = await self.handle_response(text, update, context)

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
