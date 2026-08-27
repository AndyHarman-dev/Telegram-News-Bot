from app.bot.states import state
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import ContextTypes

from app.misc.admin.admin_manager import AdminManager
from app.misc.log_helper import LogHelper
from app.bot.states.bot_states import bot_functions_state as FuncState, bot_pay_state as SubscrState
from app.bot.states.bot_states.bot_settings_state import bot_settings_state as SettingsState
from app.interfaces.cor import BaseHandler
import app.bot.states.bot_states.bot_help_states as HelpState

LOG_STATES = LogHelper(__name__, "Bot States Thread")


# Define the upper tier states which are the Menu, Help and Contact us states
class BotHelpState(HelpState.BotHelpState):
    _B_HAS_FALLBACK = True

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)
        keyboard = await self.get_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_string: str = await self.get_any_display_message(update, context, "help_command", "state_display_message")
        await self._respond(update.effective_chat, reply_string, reply_markup)
        return self.get_state_id()


class BotContactUsState(state.State):
    # Base menu state. This is a start state of the bot
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await super().enter_state(update, context)

    async def on_user_messaged(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        user_surname = update.message.from_user.last_name
        message = update.message.text
        await AdminManager.send_admin_message(f"User {user_id}, {user_name} {user_surname} sent message to contact us: {message}")

        # Return to the standard state
        return self.get_state_id()


class BotMenuState(state.State, BaseHandler):
    # Base menu state. This is a start state of the bot

    # Do not make fallbacks for the initial state
    _B_HAS_FALLBACK = False

    async def handle(self, *args, **kwargs):
        return await self.transition_to_state(kwargs['update'], kwargs['context'], "menu")

    async def update_keyboard(self, update, context):
        await super().update_keyboard(update, context)

