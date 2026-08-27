import asyncio
import threading
import logging
import copy

from telegram import Update, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.bot.states.users_states import UsersStates
from app.database.db_hashtag import HashtagManager
from app.bot.states.state import LOG_STATE_INSTANCE, State
from app.factories.ai_factories import AIServiceFacade, AIAllServiceFactory
from app.misc.keyboard import Keyboard
from app.misc.localization.lang_loc import make_localized_text
from app.interfaces.cor import BaseHandler
from app.misc.log_helper import LogHelper
from app.misc.vectorization.hashtager import Hashtager
from app.misc.google_translator import GoogleTranslator

LOG_BOT_HASHTAGS_STATE = LogHelper(__name__, "Bot Hashtags State Thread")


class BotHashtagsState(State):

    LINKING_TABLE_NAME = 'chats_hashtags'  # Define a const of the table name

    class HashtagState(State.BaseSubState):

        async def handle_enter_state(self, update, context):
            pass

        async def handle_on_user_message(self, update, context):
            pass

        async def handle_callback_query(self, update, context):
            """Called if we are in the substate of 'hashtags shown' and we chose a hashtag.
                   We either add or delete a hashtag for a user here by determining if it was added or deleted before"""

            if self.state.input_handler.is_navigational_data(update.callback_query.data):
                return self.state.get_state_id()

            if self.state.input_handler.is_fallback(update.callback_query.data):
                return self.state.get_state_id()

            # Get chosen hashtag
            chosen_hashtag = update.callback_query.data

            # Get hashtag id
            hashtag_id = HashtagManager.get_hashtag_id(chosen_hashtag)

            link = ""
            if isinstance(self.state, BotHashtagsState):
                link = self.state.LINKING_TABLE_NAME
            else:
                LOG_STATE_INSTANCE.raise_exception_with_log(ValueError('This substate must have a reference to a hashtag state!'))

            # Add or remove hashtag
            if HashtagManager.has_hashtag(update.effective_user.id, chosen_hashtag, table_name=link):
                HashtagManager.remove_hashtag_from_entity(update.effective_user.id, hashtag_id, link)
            else:
                HashtagManager.add_hashtag_to_entity(update.effective_user.id, hashtag_id, link)

            return await self.state.transition_to_state(update, context, self.state.get_state_name())

    class CategoryState(State.BaseSubState):

        async def handle_enter_state(self, update, context):
            pass

        async def handle_on_user_message(self, update, context):
            pass

        async def handle_callback_query(self, update, context):
            # Called if we are in the substate of 'categories shown'. Redefines the keyboard to show the hashtags of a
            # chosen category

            if self.state.input_handler.is_navigational_data(update.callback_query.data):
                return self.state.get_state_id()

            if self.state.input_handler.is_fallback(update.callback_query.data):
                return self.state.get_state_id()

            self.state.chosen_category = update.callback_query.data

            await self.state.update_keyboard(update, context)

            # Next state is hashtags shown
            hashtags_shown_state = BotHashtagsState.HashtagState(self.state)
            self.state.change_state(update, context, hashtags_shown_state)

            return await self.state.transition_to_state(update, context, self.state.get_state_name())

    class _HashtagsKeyboard(Keyboard):
        _LOCALE_KEYBOARD_HASHTAGS_KEY_PATH = "hashtag_categories"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.hashtag_state = None

        def __deepcopy__(self, memodict={}):
            new_copy = super().__deepcopy__(memodict)
            new_copy.hashtag_state = self.hashtag_state
            return new_copy

        async def transform_button_text(self, key, data=None):
            # Get current locale
            locale = await make_localized_text(self._lang_code)

            # Try to get custom translation for hashtags
            try:

                # Get data from the state
                current_hashtags_state = await self.hashtag_state.get_current_state()
                chosen_category = await self.hashtag_state.get_chosen_category()

                current_state_is_categories = isinstance(current_hashtags_state, BotHashtagsState.CategoryState)
                current_state_is_hashtags = isinstance(current_hashtags_state, BotHashtagsState.HashtagState)

                key_path = None

                # Conditionally form the key path to the corresponding translation in the locale
                if current_state_is_categories:
                    # Get the translation for the category
                    key_path = f"{self._LOCALE_KEYBOARD_HASHTAGS_KEY_PATH}.{key.lower()}"
                elif current_state_is_hashtags:
                    # Get the translation for the hashtags, initially we'll get a list by this key
                    key_path = f"{self._LOCALE_KEYBOARD_HASHTAGS_KEY_PATH}.{chosen_category.lower()}"
                else:
                    # Raise exception if unexpected state
                    LOG_STATE_INSTANCE.raise_exception_with_log(
                        ValueError(f"Unexpected hashtags state! Given {current_hashtags_state}"))

                locale_text = await locale.get_text(key_path)

                # Define constants for convenient indexing
                CATEGORY_INDEX = 0
                HASHTAGS_LIST_INDEX = 1

                if current_state_is_categories:
                    # Return the category localed name
                    return locale_text[CATEGORY_INDEX]

                elif current_state_is_hashtags:
                    # Return the hashtags list
                    hashtags_dict = locale_text[HASHTAGS_LIST_INDEX]

                    # Get the locale translation from the dictionary
                    translated_hashtag_text = hashtags_dict[key.lower()]
                    if await self.hashtag_state.does_hashtag_exist(key):
                        return str(translated_hashtag_text + " ✅")
                    else:
                        return translated_hashtag_text


            except ValueError as NotFoundException:
                # Excepts value error if the key is not found, which would imply that the keyboard used for default
                # locale values
                LOG_STATE_INSTANCE.log(logging.INFO, f"Handled: {NotFoundException}")
                return await locale.get_text(f"{self._LOCALE_KEYBOARD_KEY_PATH}.{key}")

    _KEYBOARD_CLASS = _HashtagsKeyboard

    def __init__(self, *args, **kwargs):
        # Initially list available hashtag categories
        super().__init__(*args, **kwargs)

        # Get hashtag categories from the database
        hashtag_categories = HashtagManager.get_hashtag_categories_list()

        # Form a keyboard layout from the hashtag categories. Note: keys match values because we pull hashtags using
        # the names
        keyboard_layout = {category: category for category in hashtag_categories}

        # Instantiate the first instance of the keyboard
        self._keyboard = self._instantiate_default_keyboard(keyboard_layout)

        # Substate of this state
        self.chosen_category = ""

        initial_state = self.CategoryState(self)
        self.change_state(None, None, initial_state)

        # Copy of the categories keyboard to be able to rewrite keyboard if needed
        self.categories_keyboard = copy.deepcopy(self._keyboard)

        self.current_hashtags_page = 0

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        # Skip if it's navigational data
        if self.input_handler.is_navigational_data(update.callback_query.data):
            return await super().callback_query(update, context)

        if update.callback_query.data == self.FALLBACK:
            return await super().callback_query(update, context)

        if self.current_sub_state:
            return await self.current_sub_state.handle_callback_query(update, context)

    async def _get_display_message(self, locale):

        # Override get display message to return a locale entry based on the current state
        query = f"states.{self.state_name}.state_display_message.{self.current_sub_state.__class__.__name__}"
        return await locale.get_text(query)

    def _instantiate_default_keyboard(self, keyboard_layout, starting_page=0):
        default_keyboard = super()._instantiate_default_keyboard(keyboard_layout, starting_page)

        # Initialize with the friendly instance of self
        if isinstance(default_keyboard, self._HashtagsKeyboard):
            default_keyboard.hashtag_state = self

        return default_keyboard

    async def _transition_to_next_state(self, context, query_data, update):
        await self._state_machine_ref.transition_to_state(update, context, self.get_state_name())
        return self.get_state_id()

    async def update_keyboard(self, update, context):
        """
        Update the keyboard based on the chosen category and hashtags.

        Parameters:
            update (telegram.Update): The update object from Telegram.
            context (telegram.ext.CallbackContext): The context object from the Telegram bot.

        Returns:
            None
        """

        chosen_category = update.callback_query.data

        hashtags = {hashtag: hashtag for hashtag in
                    HashtagManager.get_hashtags_for_categories(chosen_category)}

        self._keyboard = self._instantiate_default_keyboard(hashtags)

    async def get_keyboard(self):
        keyboard = await super().get_keyboard()
        self.current_hashtags_page = self._keyboard.current_page
        return keyboard

    async def get_current_state(self):
        return self.current_sub_state

    async def get_chosen_category(self):
        return self.chosen_category

    async def does_hashtag_exist(self, hashtag):
        "Adds a checkmark if the user has the hashtag"
        return HashtagManager.has_hashtag(self.tg_chat_id, hashtag, table_name=self.LINKING_TABLE_NAME)

    async def fallback(self, update, context):
        # Override fallback for the substates

        if isinstance(self.current_sub_state, self.HashtagState):
            initial_state = self.CategoryState(self)
            self.change_state(update, context, initial_state)
            self._keyboard = self.categories_keyboard

            return await self._state_machine_ref.transition_to_state(update, context, self.get_state_name())  #
            # Transition to this state again
        else:
            return await super().fallback(update, context)


class BotHashtagsState_Init(BotHashtagsState, BaseHandler):
    """Used only once when the bot is started"""

    class _HashtagInitKeyboard(BotHashtagsState._HashtagsKeyboard):
        async def _try_to_get_back_button(self):
            # During the init state, we don't have back button
            if self.back_button_callback_data is not None:
                locale = await make_localized_text(self._lang_code)
                self._BACK_BUTTON_TEXT = await locale.get_text(f"{self._LOCALE_KEYBOARD_KEY_PATH}.done")
                return InlineKeyboardButton(self._BACK_BUTTON_TEXT,
                                            callback_data=self.transform_keyboard_data_func(
                                                self.back_button_callback_data))
            else:
                return None

    _KEYBOARD_CLASS = _HashtagInitKeyboard

    async def fallback(self, update, context):
        if isinstance(self.current_sub_state, BotHashtagsState.HashtagState):
            return await super().fallback(update, context)
        else:
            return await super().handle(update=update, context=context)

    async def update_keyboard(self, update, context):
        await super().update_keyboard(update, context)

    async def handle(self, *args, **kwargs):
        return await self.transition_to_state(kwargs['update'], kwargs['context'], self.get_state_name())


class BotInitHashtagerState(State, BaseHandler):
    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)
        await UsersStates.del_last_menu_in_chat(update.effective_chat)
        await self._unclean_new_respond(update.effective_chat,
                                        await self.get_any_display_message(update,
                                                                           context,
                                                                           'init_hashtager',
                                                                           'state_display_message'),
                                        None)
        await self._unclean_new_respond(update.effective_chat,
                                        await self.get_any_display_message(update, context, 'init_hashtager', 'examples'),
                                        None)
        return self.get_state_id()

    async def on_user_messaged(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        async def make_hashtagization(message_id, update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_prompt = update.message.text.replace(f"@{context.bot.username}", '')
            try:
                user_promt_in_english = await GoogleTranslator.translate_text_async(user_prompt, "en")
            except Exception as e:
                try:
                    system_message = (f'Translate this text into English qualitatively and as concisely as possible. '
                                      f'If the text is in English, correct it. '
                                      f'The text is expected to contain a regular list of all possible objects. '
                                      f'The result should be capacious and concise!')
                    fr = await AIServiceFacade.create_chat_completion(factory_type=AIAllServiceFactory,
                                                                      system=system_message,
                                                                      stream=False
                                                                      )
                    user_promt_in_english = await fr.prompt(user_prompt)
                except Exception as e:
                    user_promt_in_english = 'some cool content'
            hashtager = await Hashtager.get_instance()
            hashtags = await hashtager.choosing_hashtags_for(user_promt_in_english)

            chat_id = update.effective_chat.id
            HashtagManager.remove_all_hashtag_by_chat_id(chat_id)

            for category, hashtag_name in hashtags.values():
                hashtag_id = HashtagManager.get_hashtag_id_by_category_and_name(category, hashtag_name)
                if hashtag_id is not None:
                    HashtagManager.add_hashtag_to_entity(chat_id, hashtag_id, "chats_hashtags")
            info_message = f'Hashtags for \"{user_prompt}\" (translate in English: \"{user_promt_in_english}\") ' + \
                           f'user preferences: ' + ', '.join(hashtag_name for _, hashtag_name in hashtags.values())
            LOG_BOT_HASHTAGS_STATE.log(logging.INFO, info_message)

            await self._unclean_new_respond(update.effective_chat,
                                            await self.get_current_display_message(update,
                                                                                   context,
                                                                                   "finish_hashtagization"
                                                                                   ),
                                            None,
                                            None,
                                            message_id)

        def sinc_make_hashtagization(message_id,
                                     update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
            asyncio.run(make_hashtagization(message_id, update, context))

        await UsersStates.del_last_message_in_chat(update.effective_chat)
        await self._unclean_new_respond(update.effective_chat,
                                        await self.get_any_display_message(update, context,
                                                                           'init_hashtager', "wait_message"),
                                        None)

        mess_id = update.message.message_id
        #hashtags_thread = threading.Thread(target=sinc_make_hashtagization, args=(mess_id, update, context))
        #hashtags_thread.start()
        asyncio.create_task(make_hashtagization(mess_id, update, context))

        await UsersStates.del_last_menu_in_chat(update.effective_chat)

        if self.state_name.startswith('init'):
            return await self.fallback(update, context)
        return await self.transition_to_state(update, context, 'menu')

    async def handle(self, *args, **kwargs):
        return await self.transition_to_state(kwargs['update'], kwargs['context'], self.get_state_name())

    async def fallback(self, update, context):
        return await super().handle(update=update, context=context)


class BotResetHashtagerState(BotInitHashtagerState):
    pass
