from app.bot.states.bot_states.bot_settings_state.bot_settings_state import BotLanguageState, BotStyleState, \
    BotUTCShiftState
from telegram.ext import ContextTypes
from telegram import Update

from app.database.db_chat import ChatManager
from app.database.db_translation import TranslationManager
from app.interfaces.cor import BaseHandler


class BotLanguageStateInit(BotLanguageState, BaseHandler):
    """Used only once when the bot is started"""

    _B_HAS_FALLBACK = False

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Exist state when any language is chosen"""
        await super().callback_query(update, context)

        # Next transition to styles
        return await super().handle(update=update, context=context)

    async def _transition_to_next_state(self, context, query_data, update):
        pass

    async def update_keyboard(self, update, context):
        await super().update_keyboard(update, context)

    async def handle(self, *args, **kwargs):
        return await self.transition_to_state(kwargs['update'], kwargs['context'], "start")

    async def fallback(self, update, context):
        pass  # Skip fallback


class BotStylesStateInit(BotStyleState, BaseHandler):
    """Used only once when the bot is started"""

    _B_HAS_FALLBACK = False

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Exist state when any style is chosen"""
        await super().callback_query(update, context)

        if not self.input_handler.is_navigational_data(update.callback_query.data):
            return await super().handle(update=update, context=context)

    async def _transition_to_next_state(self, context, query_data, update):
        pass

    async def fallback(self, update, context):
        pass

    async def update_keyboard(self, update, context):
        await super().update_keyboard(update, context)

    async def handle(self, *args, **kwargs):
        return await self.transition_to_state(kwargs['update'], kwargs['context'], self.get_state_name())


class BotUTCShiftStateInit(BotUTCShiftState, BaseHandler):
    """Used only once when the bot is started"""

    _B_HAS_FALLBACK = False

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Exist state when any UTC shift is chosen"""
        await super().callback_query(update, context)

        if not self.input_handler.is_navigational_data(update.callback_query.data):
            return await super().handle(update=update, context=context)

    async def _transition_to_next_state(self, context, query_data, update):
        pass

    async def fallback(self, update, context):
        pass  # Do not fallback in this state

    async def handle(self, *args, **kwargs):
        return await self.transition_to_state(kwargs['update'], kwargs['context'], self.get_state_name())


class BotResetStylesState(BotStylesStateInit):
    pass


class BotResetUTCShiftState(BotUTCShiftStateInit):
    pass
