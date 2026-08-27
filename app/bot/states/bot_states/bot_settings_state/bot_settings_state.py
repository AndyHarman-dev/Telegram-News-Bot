import logging

from app.bot.states import state
from telegram import Update
from telegram.ext import ContextTypes
from app.database.db_translation import TranslationManager
from app.database.db_chat import ChatManager, UTCShifter
from app.misc.keyboard import Keyboard
from app.bot.config import AVAILABLE_MODELS, ACTIVE_MODELS
from app.misc.localization.lang_loc import make_localized_text
from app.misc.log_helper import LogHelper
from app.bot.states.state import State

LOG_SETTINGS = LogHelper(__name__, "SETTINGS")


class BotLanguageState(state.State):
    class _LanguageKeyboard(Keyboard):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.language_state = None

        # We do not want to use localization for this state
        async def transform_button_text(self, key, data=None):
            language_id = TranslationManager.get_language_id(data)
            chat_language = ChatManager.get_chat_language(self.language_state.tg_chat_id)
            if int(language_id) == int(chat_language):
                key = f"{key} ✅"

            return key

    _KEYBOARD_CLASS = _LanguageKeyboard

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get hashtag categories from the database
        languages = TranslationManager.get_languages(orig_name=True)

        # Form a keyboard layout from the hashtag categories. Note: keys match values because we pull hashtags using
        # the names
        keyboard_layout = {category: category for category in languages}

        # Make the keyboard as a list of languages
        self._keyboard = self._instantiate_default_keyboard(keyboard_layout)
        self._keyboard.language_state = self

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Sets the user langauge
        if update.callback_query.data != State.FALLBACK:
            ChatManager.set_chat_language(update.effective_chat.id, update.callback_query.data)

        return await self.fallback(update, context)

    async def _transition_to_next_state(self, context, query_data, update):
        # Don't transition to any other next state
        pass


class BotStyleState(state.State):
    # Defines BotStyleState

    class _StyleKeyboard(Keyboard):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.style_state = None

        async def transform_button_text(self, key, data=None):
            locale = await make_localized_text(self._lang_code)
            button_text = await locale.get_text(f"styles.{key.lower()}")

            style_id = TranslationManager.get_style_id_by_name(data)
            chat_style = ChatManager.get_chat_style(self.style_state.tg_chat_id)

            if style_id == chat_style:
                button_text = f"{button_text} ✅"

            return button_text

    _KEYBOARD_CLASS = _StyleKeyboard

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get hashtag categories from the database
        styles = TranslationManager.get_styles()

        # Form a keyboard layout from the hashtag categories. Note: keys match values because we pull hashtags using
        # the names
        keyboard_layout = {category: category for category in styles}

        # Make the keyboard as a list of styles
        self._keyboard = self._instantiate_default_keyboard(keyboard_layout)
        self._keyboard.style_state = self

    async def _transition_to_next_state(self, context, query_data, update):
        # Don't transition to any other next state
        pass

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        if self.input_handler.is_navigational_data(update.callback_query.data):
            return await super().callback_query(update, context)

        if self.input_handler.is_fallback(update.callback_query.data):
            return await super().callback_query(update, context)

        ChatManager.set_chat_style(update.effective_chat.id, update.callback_query.data)

        return await self.fallback(update, context)


class BotSettingsState(state.State):
    # Defines Bot Settings state which lists all the settings available
    pass


class BotUTCShiftState(state.State):
    class _UTCKeyboard(Keyboard):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.utc_state = None

        async def transform_button_text(self, key, data=None):
            preliminary_result = await super().transform_button_text(key, data)
            _sign = "+" if int(key) >= 0 else ""
            preliminary_result += f" (UTC{_sign}{key})"

            # If user has one of the UTC shifts, mark it
            user_time_zone = ChatManager.get_chat_timezone(self.utc_state.tg_chat_id)
            if user_time_zone is not None and int(key) == int(user_time_zone):
                preliminary_result = f"{preliminary_result} ✅"

            return preliminary_result

    _KEYBOARD_CLASS = _UTCKeyboard

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get list of UTC shifts
        self.utc_shifts = {str(hour): hour for hour in range(UTCShifter.START_HOUR, UTCShifter.START_HOUR + 24)}

        self._keyboard = self._instantiate_default_keyboard(self.utc_shifts)
        if isinstance(self._keyboard, self._UTCKeyboard):
            self._keyboard.utc_state = self

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Sets the user UTC shift

        if self.input_handler.is_navigational_data(update.callback_query.data):
            return await super().callback_query(update, context)

        if self.input_handler.is_fallback(update.callback_query.data):
            return await super().callback_query(update, context)

        ChatManager.set_chat_timezone(update.effective_chat.id, update.callback_query.data)

        # exit the state right away
        return await self.fallback(update, context)


class BotLLMSelectorState(state.State):
    """State for llm selection"""

    class _LLMKeyboard(Keyboard):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.llm_state = None

        async def transform_button_text(self, key, data=None):
            preliminary_result = await super().transform_button_text(key, data)
            if len(self.llm_state.selected_llm_model) > 0 and self.llm_state.selected_llm_model == data:
                preliminary_result = f"{preliminary_result} ✅"

            return preliminary_result

    _KEYBOARD_CLASS = _LLMKeyboard

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        as_dict = {model_type: model_name for model_type, model_name in ACTIVE_MODELS.items()}
        self._keyboard = self._instantiate_default_keyboard(as_dict)

        if isinstance(self._keyboard, self._LLMKeyboard):
            self._keyboard.llm_state = self

        self.selected_llm_model = None

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            self.selected_llm_model = ChatManager.get_llm_model(update.effective_chat.id)
        except ValueError as e:
            self.selected_llm_model = ""
        except Exception as e:
            LOG_SETTINGS.log(logging.ERROR, f"Can't enter state {e}")
        return await super().enter_state(update, context)

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.input_handler.is_navigational_data(update.callback_query.data):
            return await super().callback_query(update, context)

        if self.input_handler.is_fallback(update.callback_query.data):
            return await super().callback_query(update, context)

        ChatManager.set_llm_model(update.effective_chat.id, update.callback_query.data)

        # exit the state right away
        return await self.fallback(update, context)
