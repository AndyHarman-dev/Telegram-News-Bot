import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, CommandHandler, MessageHandler, ContextTypes, Application, CallbackQueryHandler, \
    ConversationHandler

from database import entity
from misc.log_helper import LogHelper, logging
from config import config
from misc.pexels_library import PexelsAPI
from database.database import Database
from database.users import User, Preferences
from SocialMediaAPIs.telegram_api import TelegramAPI
import SocialMediaAPIs.social_media_api_defines as sm_api_defines
import database.entity

# Create log helper and category for it
TG_LOG_BOT = LogHelper(__name__, "Bot thread")

# Text handles
START_MESSAGE_TEXT = config.CONFIG_DICT['start_message']
HELP_MESSAGE_TEXT = config.CONFIG_DICT['help_message']
PLATFORMS_MESSAGE_TEXT = config.CONFIG_DICT['platforms_message']
ACCOUNTS_MESSAGE_TEXT = config.CONFIG_DICT['accounts_message']

# Define telegram bot states
PLATFORMS, AUTHORIZE_PLATFORM, CHOOSE_GROUPS_ACCOUNTS, ENTITY, SET_PREFERENCES, SCHEDULE_GENERATION, GENERATE = range(7)


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


def make_keyboard(mapped_btns):
    keyboard = [InlineKeyboardButton(key, value) for key, value in mapped_btns.items()]
    return keyboard


# Interface for interacting with TG Bot
class TelegramBot:
    # Initializers =============================================================
    def __init__(self, token: str, bot_username: str) -> None:

        # Validate token
        if token == '':
            err_msg = "Token cannot be empty. Exception is raised!"
            TG_LOG_BOT.log(logging.ERROR, err_msg)
            raise ValueError(err_msg)

        self.__token = token
        self.__bot_username = bot_username
        self.__bot_state = 0
        self.__current_user = User()
        self.__current_platform = ""
        self.__current_entity = object

        self.__create_application()
        TG_LOG_BOT.log(logging.INFO, "Bot initialized")

    # Creates telegram application and add handlers
    def __create_application(self):
        self.__app = Application.builder().token(self.__token).build()

        # Conv handler
        conv_handler = self.__create_conversation_handler()
        self.__app.add_handler(conv_handler)

        self.__app.add_error_handler(self.error)

    """
    Creates a ConversationHandler object and defines the main state of the telegram bot.
    Also binds all the necessary message handlers and query handlers

    Returns:
        ConversationHandler: The created ConversationHandler object.

    Parameters:
        self: The instance of the class.
    """
    def __create_conversation_handler(self):
        return ConversationHandler(
            entry_points=[CommandHandler('start', self.handle_start), CallbackQueryHandler(self.handle_start_query)],
            states={
                PLATFORMS: [MessageHandler(filters.TEXT, self.handle_platforms),
                            CallbackQueryHandler(self.handle_platforms_query)
                            ],
                CHOOSE_GROUPS_ACCOUNTS: [MessageHandler(filters.TEXT, self.handle_choose_groups_accounts),
                                         CallbackQueryHandler(self.handle_choose_groups_accounts_query)],
                ENTITY: [MessageHandler(filters.TEXT, self.handle_entity,),
                         CallbackQueryHandler(self.handle_entity_query)],
                SET_PREFERENCES: [MessageHandler(filters.TEXT, self.handle_set_preferences),
                                  CallbackQueryHandler(self.handle_set_preferences_query)],
                SCHEDULE_GENERATION: [MessageHandler(filters.TEXT, self.handle_schedule_generation),
                                      CallbackQueryHandler(self.handle_schedule_generation_query)],
                GENERATE: [MessageHandler(filters.TEXT, self.handle_generate),
                           CallbackQueryHandler(self.handle_generate_query)]
            },
            fallbacks=[CommandHandler('cancel', self.handle_cancel)]
        )

    # Handlers =============================================================================================

    """
    Handles the start command from the user.

    Parameters:
        update (Update): The update object containing information about the incoming message.
        context (ContextTypes.DEFAULT_TYPE): The context object providing additional functionality.

    Returns:
        None
    """

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        # Try to register user if not exists
        Database.register_user_if_not_exists(user.id, f"{user.first_name} {user.last_name}", False, {})
        # Independently of the initial existence, load the user to the class memory
        self.__current_user = Database.get_user_if_exists(user.id)

        TG_LOG_BOT.log(logging.INFO, f"User {user.first_name} started the bot")
        # Create a keyboard for start handle
        keyboard = [
            [
                InlineKeyboardButton("Help", callback_data='help'),
                InlineKeyboardButton("Platforms", callback_data=PLATFORMS)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f'{START_MESSAGE_TEXT} Please choose:', reply_markup=reply_markup)

    """
    Called whenever a button called in the start phase

    Args:
        update (Update): The update object containing the query.
        context (ContextTypes.DEFAULT_TYPE): The context object.

    Returns:
        Next state to go to
    """

    async def handle_start_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == PLATFORMS:
            return PLATFORMS
        if query.data == 'help':
            return self.handle_help(update, context)

    """
    Gives a user a list of all available platforms in our bot.

    :param update: The update object containing information about the incoming message.
    :type update: Update
    :param context: The context object containing information about the conversation.
    :type context: ContextTypes.DEFAULT_TYPE
    :return: None
    """

    async def handle_platforms(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        # Show the platforms to choose
        keyboard_markup = list(
            InlineKeyboardButton(key, value) for key, value in sm_api_defines.AVAILABLE_SOCIAL_MEDIA_APIs.items()
        )
        reply_markup = InlineKeyboardMarkup([keyboard_markup])

        await update.message.reply_text(f"{PLATFORMS_MESSAGE_TEXT}. Please choose: ", reply_markup=reply_markup)

    """
    Called whenever a button called in a PLATFORMS state

    :param update: The update object.
    :type update: Update
    :param context: The context object.
    :type context: ContextTypes.DEFAULT_TYPE
    :return: The next state.
    :rtype: int
    """

    async def handle_platforms_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        # Validate the platform
        if query.data not in sm_api_defines.AVAILABLE_SOCIAL_MEDIA_APIs.values():
            raise ValueError(f"Invalid platform value: {query.data}")

        self.__current_platform = query.data
        return CHOOSE_GROUPS_ACCOUNTS

    """
    Handles the state switching to CHOOSE_GROUPS_ACCOUNTS state and shows all available groups and
    accounts of a current user.

    Args:
        update (Update): The update object that contains information about the incoming message.
        context (ContextTypes.DEFAULT_TYPE): The context object that provides access to user data and other functionality.

    Returns:
        None
    """

    async def handle_choose_groups_accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self.__current_user
        current_platform = self.__current_platform

        # Get groups and accounts for the current platform
        groups, accounts = user.platform_entities.get(current_platform, ([], []))

        # Create buttons for each group and account
        buttons = [
                      InlineKeyboardButton(text=group.entity_name, callback_data=group) for group in groups
                  ] + [
                      InlineKeyboardButton(text=account.entity_name, callback_data=account) for account in accounts
                  ]

        # Create a keyboard markup with the buttons
        keyboard_markup = InlineKeyboardMarkup.from_column(buttons)

        # Send a message with the keyboard
        await update.message.reply_text("Choose a group or account:", reply_markup=keyboard_markup)


    """
    Handles choosing either a group or an account. Simply remembers a reference
    and validate the right entity type

    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.

    Returns:
        ENTITY: The next entity state.
    """

    async def handle_choose_groups_accounts_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        # Validate correct entity type
        if not isinstance(query.data, entity.Entity):
            TG_LOG_BOT.raise_exception_with_log(ValueError("Invalid entity type provided in callback data"))
        # Save the reference of entity
        self.__current_entity = query.data
        # Move to the next entity state
        return ENTITY

    async def handle_entity(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

    async def handle_entity_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

    async def handle_set_preferences(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

    async def handle_set_preferences_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

    async def handle_schedule_generation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

    async def handle_schedule_generation_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

    async def handle_generate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

    async def handle_generate_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

    async def handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(HELP_MESSAGE_TEXT)
        return None

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
