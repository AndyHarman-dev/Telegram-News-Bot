from telegram import Update
from telegram.ext import ContextTypes

from app.bot.states import state
from app.misc.keyboard import Keyboard


class BotChatState(state.State):
    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Since we enter this state from a message, we already need to process it
        return await super().on_user_messaged(update, context)
