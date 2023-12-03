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
PLATFORMS, AUTHORIZE_PLATFORM, CHOOSE_GROUPS_ACCOUNTS, ENTITY, EDIT_PREFERENCES, SCHEDULE_GENERATION, GENERATE = range(7)


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
                EDIT_PREFERENCES: [MessageHandler(filters.TEXT, self.handle_edit_preferences),
                                   CallbackQueryHandler(self.handle_edit_preferences_query)],
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

    """
    Handles an entity by retrieving its preferences and displaying them as a message. 
    The function takes an `update` object of type `Update` and a `context` object of type `ContextTypes.DEFAULT_TYPE`.

    Parameters:
        update (Update): The update object containing the information about the incoming message.
        context (ContextTypes.DEFAULT_TYPE): The context object containing the additional information for handling the update.

    Returns:
        None: This function does not return anything.
    """
    async def handle_entity(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        entity = self.__current_user.platform_entities[self.__current_platform][self.__current_entity]
        preferences = entity.preferences
        # Show the entity's preferences as a message
        await update.message.reply_text(f"Current preferences for {entity.entity_name}:\n"
                                        f"Topics: {preferences.topics}\n"
                                        f"Avoid topics: {preferences.avoid_topics}\n"
                                        f"Frequency: {preferences.frequency}")
        # Show buttons: "Edit preferences", "Schedule Generation", "Generate", "Delete"
        keyboard = [
            [
                InlineKeyboardButton("Edit preferences", callback_data='edit_preferences'),
                InlineKeyboardButton("Schedule Generation", callback_data='schedule_generation'),
                InlineKeyboardButton("Generate", callback_data='generate'),
                InlineKeyboardButton("Delete", callback_data='delete')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Please choose:', reply_markup=reply_markup)

    """
    Handle entity query.

    Parameters:
        update (Update): The update containing the callback query.
        context (ContextTypes.DEFAULT_TYPE): The context object.

    Returns:
        None

    Description:
        This function handles the entity query. It takes an update object and a context object as 
        parameters. The update object contains the callback query, while the context object provides 
        additional context for the function. The function does not return anything.

        The function starts by retrieving the callback query from the update object. It then calls the 
        "answer" method on the query object to send an empty answer to the callback query. 

        The function then checks the value of the "data" attribute of the callback query. If it is 
        "edit_preferences", the function returns the constant "EDIT_PREFERENCES". If it is 
        "schedule_generation", the function returns the constant "SCHEDULE_GENERATION". If it is 
        "generate", the function returns the constant "GENERATE". If it is "delete", the function 
        deletes the entity from the current user's platform_entities dictionary and returns the constant 
        "CHOOSE_GROUPS_ACCOUNTS".
    """
    async def handle_entity_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        if query.data == 'edit_preferences':
            return EDIT_PREFERENCES
        elif query.data == 'schedule_generation':
            return SCHEDULE_GENERATION
        elif query.data == 'generate':
            return GENERATE
        elif query.data == 'delete':
            # Delete the entity and return to the previous state
            del self.__current_user.platform_entities[self.__current_platform][self.__current_entity]
            return CHOOSE_GROUPS_ACCOUNTS

    async def handle_edit_preferences(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Ask the user for new preferences
        await update.message.reply_text("Please enter the new preferences in the following format:\n"
                                        "topics: topic1, topic2, ...\n"
                                        "avoid_topics: avoid_topic1, avoid_topic2, ...\n"
                                        "frequency: daily/weekly/monthly")

    async def handle_edit_preferences_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Parse the user's input and update the preferences
        preferences_text = update.message.text
        # Parse the preferences_text and update the preferences for the current entity
        # ...
        # Return to the ENTITY state
        return ENTITY

    async def handle_schedule_generation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Ask the user for the desired schedule time
        await update.message.reply_text("Please enter the desired schedule time in the format: HH:MM")

    async def handle_schedule_generation_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Parse the user's input and schedule the generation
        schedule_time_text = update.message.text
        # Schedule the generation based on the schedule_time_text and the current entity's preferences
        # ...
        # Return to the ENTITY state
        return ENTITY

    async def handle_generate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Generate a sample post based on the current entity's preferences
        sample_post = "Sample post content"  # Replace this with the actual generated content
        await update.message.reply_text(f"Generated sample post:\n{sample_post}")

        # Show buttons: "<< BACK" and "Post"
        keyboard = [
            [
                InlineKeyboardButton("<< BACK", callback_data='back'),
                InlineKeyboardButton("Post", callback_data='post')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Please choose:', reply_markup=reply_markup)

    async def handle_generate_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()

        if query.data == 'back':
            return ENTITY
        elif query.data == 'post':
            # Post the generated content to the selected entity
            # ...
            await update.message.reply_text("The post has been published.")
            return ENTITY

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
