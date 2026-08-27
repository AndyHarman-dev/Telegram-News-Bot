import asyncio

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.bot.states import state
from app.misc.admin.admin_manager import AdminManager
from app.misc.keyboard import HelpKeyboard


class GeneralHelpState(state.State):
    MAIN_MENU = "help_command"
    _KEYBOARD_CLASS = HelpKeyboard


# Define the substates of the Help state
class BotHelpState(GeneralHelpState):
    _B_HAS_FALLBACK = False

    async def handle(self, *args, **kwargs):
        return await self.transition_to_state(kwargs['update'], kwargs['context'], "help_command")


class BotSkillsState(GeneralHelpState):

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)
        keyboard = await self.get_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_string: str = await self.get_display_message(update, context)
        reply_string = reply_string.replace('/1', '/menu').replace('/2', '/help').replace('/3', '/reset')
        # for arabic language:
        reply_string = reply_string.replace('1/', '/menu').replace('2/', '/help').replace('3/', '/reset')
        await self._respond(update.effective_chat, reply_string, reply_markup)
        return self.get_state_id()


class BotSettingResetState(GeneralHelpState):
    pass


class BotAreYouSureState(GeneralHelpState):

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)
        await self._respond(update.effective_chat, await self.get_display_message(update, context), None)
        return await self.transition_to_state(update, context, 'reset_styles')


class BotFAQState(GeneralHelpState):

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)
        keyboard = await self.get_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._unclean_edit_respond(update.effective_chat,
                                         await self.get_display_message(update, context),
                                         reply_markup=reply_markup,
                                         parse_mode='HTML')
        return self.get_state_id()

    async def on_user_messaged(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        user_surname = f'{update.message.from_user.last_name} ' if update.message.from_user.last_name is not None else ''
        question = update.message.text
        await AdminManager.send_admin_message(f"User {user_id}, {user_name} {user_surname}sent us a question:\n{question}")
        await self._respond(update.effective_chat,
                            await self.get_current_display_message(update, context, "state_update_display_message"),
                            reply_markup=InlineKeyboardMarkup(await self.get_keyboard()))
        return self.get_state_id()


class BotContactUsState(GeneralHelpState):
    pass


class BotWriteProblemState(GeneralHelpState):

    async def on_user_messaged(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        user_surname = f'{update.message.from_user.last_name} ' if update.message.from_user.last_name is not None else ''
        question = update.message.text
        await AdminManager.send_admin_message(f"User {user_id}, {user_name} {user_surname}sent us a description of the discovered bug:\n{question}")
        await self._respond(update.effective_chat,
                            await self.get_current_display_message(update, context, "state_update_display_message"),
                            reply_markup=InlineKeyboardMarkup(await self.get_keyboard()))
        return self.get_state_id()


class BotSuggestIdeaState(GeneralHelpState):

    async def on_user_messaged(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        user_surname = f'{update.message.from_user.last_name} ' if update.message.from_user.last_name is not None else ''
        question = update.message.text
        await AdminManager.send_admin_message(f"User {user_id}, {user_name} {user_surname}sent us a description of his great idea:\n{question}")
        await self._respond(update.effective_chat,
                            await self.get_current_display_message(update, context, "state_update_display_message"),
                            reply_markup=InlineKeyboardMarkup(await self.get_keyboard()))
        return self.get_state_id()
