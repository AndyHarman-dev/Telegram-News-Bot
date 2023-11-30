import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, CommandHandler, MessageHandler, ContextTypes, Application, CallbackQueryHandler
from misc.log_helper import LogHelper, logging
from config import config
from misc.pexels_library import PexelsAPI

# Create log helper and category for it
TG_LOG_BOT = LogHelper(__name__, "Bot thread")

# Text handles
START_MESSAGE_TEXT = config.CONFIG_DICT['start_message']
HELP_MESSAGE_TEXT = config.CONFIG_DICT['help_message']

# Define bot states
BOT_STATES = {
    0: "start",
    1: "help",
    2: "generate",
    3: "accounts"
}


def get_bot_state_name(state: int) -> str:
    if state not in BOT_STATES.keys():
        err_msg = f"State {state} is not valid. Exception is raised!"
        TG_LOG_BOT.log(logging.ERROR, err_msg)
        raise ValueError(err_msg)

    return BOT_STATES[state]


def get_bot_state_index(state_name: str) -> int:
    # Validate state name
    if state_name not in BOT_STATES.values():
        err_msg = f"State {state_name} is not valid. Exception is raised!"
        TG_LOG_BOT.log(logging.ERROR, err_msg)
        raise ValueError(err_msg)

    for (i, state) in BOT_STATES.items():
        if state == state_name:
            return i


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
        self.__bot_state = 0

        self.__create_application()
        TG_LOG_BOT.log(logging.INFO, "Bot initialized")

    # Creates telegram application and add handlers
    def __create_application(self):
        self.__app = Application.builder().token(self.__token).build()

        self.__app.add_handlers(
            [
                CommandHandler("start", self.start_handle),
                CommandHandler("create", self.create_account_handle),
                CommandHandler("accounts", self.accounts_handle),
                CommandHandler("generate", self.generate_handle),
                CommandHandler("help", self.help_handle),
                MessageHandler(filters.TEXT, self.handle_message)
            ]
        )
        self.__app.add_handler(CallbackQueryHandler(self.button_handle))

        self.__app.add_error_handler(self.error)

    # Handles response
    async def handle_response(self, text: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        response = PexelsAPI.test()

        url = f"https://api.telegram.org/bot{self.__token}/sendPhoto"
        data = {'chat_id': get_chat_id(self.__token),
                'photo': response.json()['photos'][0]['src']['original']}
        r = requests.post(url, data=data)

        return "Image"

    def __update_bot_state(self, state: int):
        # Validate state
        if state not in BOT_STATES:
            err_msg = f"State {state} is not valid. Exception is raised!"
            TG_LOG_BOT.log(logging.ERROR, err_msg)
            raise ValueError(err_msg)

        TG_LOG_BOT.log(logging.INFO, f"Bot state updated to {BOT_STATES[state]}")
        self.__bot_state = state

    # TG Functions ==============================================================

    # Handle for buttons
    async def button_handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        # CallbackQueries need to be answered, even if no notification to the user is needed
        query.answer()

        if query.data == 'start':
            self.__update_bot_state(get_bot_state_index("start"))
            await query.edit_message_text(text="Executed start")
        elif query.data == 'help':
            self.__update_bot_state(get_bot_state_index("help"))
            await query.edit_message_text(text="Executed help")
        elif query.data == 'generate':
            self.__update_bot_state(get_bot_state_index("generate"))
            await query.edit_message_text(text="Executed generate")
        elif query.data == 'accounts':
            self.__update_bot_state(get_bot_state_index("accounts"))
            await query.edit_message_text(text="Executed accounts")

    # Start
    async def start_handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        TG_LOG_BOT.log(logging.INFO, f"User {user.first_name} started the bot")
        # Create a keyboard for start handle
        keyboard = [
            [
                InlineKeyboardButton("Start", callback_data='start'),
                InlineKeyboardButton("Help", callback_data='help'),
                InlineKeyboardButton("Generate", callback_data='generate'),
                InlineKeyboardButton("Accounts", callback_data='accounts')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(f'{START_MESSAGE_TEXT} Please choose:', reply_markup=reply_markup)

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

    # TODO : Realize a function for account creation for a social media platform
    async def create_account_handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

    # TODO : Relize a function for listing accounts
    async def accounts_handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

    # TODO : Realize a function for generating a post
    async def generate_handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

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
