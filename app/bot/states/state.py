# Standard libs
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Final
import random

from telegram import Update, InlineKeyboardMarkup, Bot, Message, Chat
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from app.bot.config import telegram_config
# Local modules
from app.database.db_chat import ChatManager
from app.database.db_message import MessageManager
from app.database.db_translation import TranslationManager
from app.database.db_tariff import TariffManager
from app.misc.admin.admin_manager import AdminManager
from app.misc.localization.lang_loc import make_localized_text
from app.factories.ai_factories import AIQualityServiceFactory, AIServiceFacade, AIAllServiceFactory
from app.misc import log_helper as log
from app.misc.exceptions import LongMessageException
from app.interfaces.input_handler import IInputHandler
from app.misc.keyboard import Keyboard
from app.interfaces.circuit_breaker import ICircuitBreaker
from app.interfaces.state import IState, IStateContext
from app.misc.exceptions import FallbackException
from app.bot.constants.telegram_api_constants import MAX_MESSAGE_LENGTH, MAX_MESSAGE_SIZE
from app.bot.states.users_states import UsersStates

LOG_STATE_INSTANCE: Final[log.LogHelper] = log.LogHelper("State Logger", "State Thread")
MAX_BUTTONS_PER_STATE: Final[int] = 10


class State(IStateContext):
    """
    Base class of a state that handles callbacks from telegram chat
    """

    class InputHandler(IInputHandler):
        def __init__(self, state: "State"):
            self.state = state

        async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
            from app.bot.telegram_bot import ChatGPTTelegramBot
            successful_handlization = await ChatGPTTelegramBot.handle_callback(update, context)
            if successful_handlization:
                return None
            
            await self.state.initialize_data(update, context)
            query = update.callback_query
            try:
                await query.answer()
            except Exception:
                LOG_STATE_INSTANCE.log(logging.ERROR, "Failed to inform the client that its query was processed by the server.")

            last_query_data = query.data

            if last_query_data == State.FALLBACK:
                if successful_handlization is not None:
                    return await self.state.fallback(update, context)
                return None

            if await self._handle_page_navigation(update, context, last_query_data):
                if successful_handlization is not None:
                    return self.state.get_state_id()
                return None

            if successful_handlization is not None:
                return await self.state._transition_to_next_state(context, last_query_data, update)
            return None

        async def handle_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            # Respond to any state with llm quality by default
            def reorder_models(models_list, model):
                if model not in models_list:
                    return models_list

                index = models_list.index(model)
                if index != 0:
                    models_list[0], models_list[index] = models_list[index], models_list[0]

                return models_list

            # Cleanup old message that was a state
            chat = update.message.chat
            await UsersStates.del_last_menu_in_chat(chat)

            if chat not in UsersStates.open_chats:
                LOG_STATE_INSTANCE.log(logging.INFO, f"Unexpecting chat instance: {chat}")

            # Turn the messaging mode in state
            await self.state.initialize_data(update, context)
            user_msg = update.message.text
            chat_type = update.effective_chat.type
            bot_username = context.bot.username

            if (chat_type not in {"group", "supergroup"}) or (f"@{bot_username}" in user_msg):
                # get chat
                ChatManager.init_chat(update)

                chat_id = update.effective_chat.id
                user_id = update.message.from_user.id

                if TariffManager.has_user_exceeded_quota(user_id):  # has_user_exceeded_quota
                    await self.state._respond(chat,
                                              await self.state.get_any_display_message(update, context, "warning_messages", "exceeded_daily_quota"),
                                              None)
                    return

                # add usage
                TariffManager.add_usage_to_user(user_id)

                await MessageManager.create_message(user_id, chat_id, 1, user_msg)

                # get context
                processed_messages = MessageManager.get_chat_context(chat_id, 10, 10)
                combined_message = MessageManager.messages_to_string(processed_messages)

                # get system message of user translation
                system_message = TranslationManager.get_translation_command(chat_id)

                async def respond_adapter(completion: str):  # For streaming completion
                    await asyncio.sleep(0.15)
                    await self.state._respond(chat, completion, None, streaming=True)

                preferred_models: list = []

                try:

                    preferred_models = [ChatManager.get_llm_model(chat_id)]

                except ValueError as err:
                    # Ensure models are not empty
                    if len(preferred_models) <= 0:
                        preferred_models = await AIQualityServiceFactory.get_models()

                preferred_models = reorder_models(await AIAllServiceFactory.get_models(), preferred_models[0])

                async with Bot(token=telegram_config['token']) as bot:

                    try:
                        await bot.send_chat_action(chat_id=chat_id, action='typing')
                        fr = await AIServiceFacade.create_chat_completion(factory_type=AIAllServiceFactory,
                                                                          models=preferred_models,
                                                                          system=system_message,
                                                                          stream=False,
                                                                          stream_delta_callback=respond_adapter)

                        response = await fr.prompt(
                            combined_message)  # This will be received after the streaming completion

                        create_new_message = context.chat_data.get('create_new_message', False)
                        if create_new_message:
                            context.chat_data['create_new_message'] = False

                        cite_this_message = context.chat_data.get('cite_this_message', None)
                        if cite_this_message is not None:
                            context.chat_data['cite_this_message'] = None

                        await self.state._respond(chat, response, None, streaming=False,
                                                  create_new=create_new_message, cite_this=cite_this_message)

                        await MessageManager.create_message(user_id, chat_id, 2, response)
                    except FallbackException as e:

                        # If request failed already, stop
                        if hasattr(e, 'message'):
                            await AdminManager.send_admin_message(
                                f"User {update.effective_user.id}, {update.effective_user.first_name} {update.effective_user.last_name} "
                                f"has failed to communicate with bot.\n User sent message: {user_msg}. \n Exception reason: {e.message}")

                        # Notify user
                        await self.state._unclean_reply_respond(chat,
                                                                await self.state.get_any_display_message(update,
                                                                                                         context,
                                                                                                         "warning_messages",
                                                                                                         "model_unavailable"),
                                                                reply_markup=None
                                                                )

        async def _handle_page_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, last_query_data) -> bool:
            if self.is_navigational_data(last_query_data):
                self.state._keyboard.handle_page_navigation(last_query_data)
                keyboard_layout = await self.state.get_keyboard()
                reply_markup = InlineKeyboardMarkup(keyboard_layout)
                await self.state._respond(update.effective_chat,
                                          await self.state.get_display_message(update, context), reply_markup)
                return True
            return False

        @staticmethod
        def is_navigational_data(data):
            return data in ['next_page', 'prev_page']

        @staticmethod
        def is_fallback(data):
            return data == State.FALLBACK

    # Class settings
    FALLBACK = 'fallback'
    MAIN_MENU = "menu"
    _B_HAS_FALLBACK = True
    _KEYBOARD_CLASS = Keyboard
    _INPUT_HANDLER_CLASS = InputHandler

    #Class variable
    state_count = 0
    states_dictionary = {}

    class BaseSubState(IState, ABC):

        """Base substate class"""

        def __init__(self, state: "State"):
            self.state = state

        @abstractmethod
        async def handle_enter_state(self, update, context):
            pass

        @abstractmethod
        async def handle_on_user_message(self, update, context):
            pass

        @abstractmethod
        async def handle_callback_query(self, update, context):
            pass

    def __init__(self, keyboard_layout, state_name="No name state", parent_state=None):

        self.context = None
        self.current_sub_state = None
        self.state_name = state_name
        self._state_id = State.set_state_id(state_name)
        self._state_machine_ref = None
        self._parent_state = parent_state
        self._on_transition_requested = None
        self.tg_chat_id = 0
        self.input_handler = self._INPUT_HANDLER_CLASS(self)

        if keyboard_layout is not None:
            self._keyboard = self._instantiate_default_keyboard(keyboard_layout)

    def change_state(self, update, context, new_state):
        self.current_sub_state = new_state

    @staticmethod
    def set_state_id(state_name: str):
        State.state_count += 1
        State.states_dictionary.update({state_name: State.state_count})
        return State.state_count

    def get_main_state_id(self):
        return State.states_dictionary.get(self.MAIN_MENU, -1)

    def is_main_menu(self):
        return self._state_id == self.get_main_state_id()

    def _instantiate_default_keyboard(self, keyboard_layout, starting_page=0):
        """
        Instantiate the default keyboard with the given keyboard layout.

        Parameters:
            keyboard_layout (KeyboardLayout): The layout of the keyboard.

        Returns:
            Keyboard: The instantiated default keyboard.
        """
        fallback_button_data = State.FALLBACK if self._B_HAS_FALLBACK else None
        return self._KEYBOARD_CLASS(keyboard_layout, MAX_BUTTONS_PER_STATE, fallback_button_data, starting_page)

    async def update_keyboard(self, update, context):
        pass

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        # Determine if our update is from callback query or a message handler
        await self.initialize_data(update, context)

        try:
            keyboard = await self.get_keyboard()
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Try to edit or reply to the user when entering a state
            await self._respond(update.effective_chat, await self.get_display_message(update, context), reply_markup)
            return self.get_state_id()

        except NotImplementedError as no_keyboard_except:
            await self._respond(update.effective_chat, await self.get_display_message(update, context), None)
            return self.get_state_id()

    async def on_user_messaged(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Called whenever user messages during this state

        chat_id = update.effective_chat.id
        user_language_id = ChatManager.get_chat_language(chat_id)
        user_language_code = TranslationManager.get_language_code_by_id(user_language_id)
        locale = await make_localized_text(user_language_code)

        if update.message.text == await locale.get_text(f"misc.reply_keyboard.get_5"):
            from app.pipelines.pipes.chat.news_pipeline import NewsManager
            await UsersStates.delete_message(update.message)
            await UsersStates.del_last_menu_in_chat(update.effective_chat.id)
            await NewsManager.send_news_from_pocket_to_chat(update.effective_chat.id)
        else:
            asyncio.create_task(self.input_handler.handle_user_message(update, context))
        return self.get_state_id()

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Base class function that pulls out query answers it and then writes into _state_data member
        In childs you should access the data via _state_data"""
        return await self.input_handler.handle_callback_query(update, context)

    async def _transition_to_next_state(self, context, query_data, update):

        state_to_transition_to = query_data
        # Otherwise go to another state
        return await self.transition_to_state(update, context, state_to_transition_to)

    async def get_keyboard(self):
        # Verify keyboard layout
        if self._keyboard is None:
            LOG_STATE_INSTANCE.raise_exception_with_log(NotImplementedError("Keyboard layout was not implemented in "
                                                                            "this state!"))
        # LEGACY : keyboard = await self._construct_keyboard()
        keyboard = await self._keyboard.get_keyboard()

        return keyboard

    @staticmethod
    async def get_locale_text_by_chat_id(chat_id: int | str, *args) -> str:
        user_language_id = ChatManager.get_chat_language(chat_id)
        user_language_code = TranslationManager.get_language_code_by_id(user_language_id)
        locale = await make_localized_text(user_language_code)
        query = f"{'.'.join(args)}"
        return await locale.get_text(query)

    @staticmethod
    async def get_locale(update):
        user_language_id = ChatManager.get_chat_language(update.effective_chat.id)
        user_language_code = TranslationManager.get_language_code_by_id(user_language_id)
        return await make_localized_text(user_language_code)

    @staticmethod
    async def get_any_display_message(update, context, *args: str):
        return await State._get_any_display_message(await State.get_locale(update), *args)

    @staticmethod
    async def _get_any_display_message(locale, *args):
        query = f"states.{'.'.join(args)}"
        return await locale.get_text(query)

    async def get_current_display_message(self, update, context,
                                          category: str = "state_display_message", subcategory: str = ''):
        return await self._get_current_display_message(await self.get_locale(update), category, subcategory)

    async def _get_current_display_message(self, locale, category, subcategory):
        if subcategory:
            return await self._get_any_display_message(locale, self.state_name, category, subcategory)
        return await self._get_any_display_message(locale, self.state_name, category)

    async def get_display_message(self, update, context):
        return await self._get_display_message(await self.get_locale(update))

    async def _get_display_message(self, locale):
        return await self._get_any_display_message(locale, self.state_name, "state_display_message")

    @staticmethod
    def _is_navigational_data(data):
        return data in ['next_page', 'prev_page']

    async def transition_to_state(self, update, context, state_name):
        return await self._state_machine_ref.transition_to_state(update, context, state_name)

    async def fallback(self, update, context):
        try:
            parent_state_id = self._parent_state.get_state_name()
            return await self.transition_to_state(update, context, parent_state_id)
        except BadRequest:
            LOG_STATE_INSTANCE.log(logging.ERROR,
                                   "Bad request: attempt to access an undefined parent menu entity (possibly via the back button).")
            return None

    def get_state_id(self):
        # Returns state id
        return self._state_id

    def get_state_name(self):
        # Returns state name
        return self.state_name

    @staticmethod
    async def _respond(chat: Chat, respond_text, reply_markup, streaming=False, create_new=False, cite_this=None):
        """
        Attempts to respond to the user via update and keyboard either by editing the last message or replying with new one
        """
        if len(respond_text) <= 0:
            return

        try:
            # Prevent flood exceeding and send a new message instead
            current_message = UsersStates.get_last_message_in_chat(chat)

            if (len(current_message.text.encode('utf-8')) >= MAX_MESSAGE_SIZE or len(
                    current_message.text) >= MAX_MESSAGE_LENGTH) and streaming:
                raise LongMessageException("Long Message")

            if not create_new:
                await State._unclean_edit_respond(chat, respond_text, reply_markup=reply_markup)
            else:
                await State._unclean_new_respond(chat, respond_text, reply_markup=reply_markup, cite_this=cite_this)

        # Catch a too long message and send a new message
        except LongMessageException as long_msg:
            LOG_STATE_INSTANCE.log(logging.INFO, "Existing message got too long, dividing it...")
            await State._unclean_reply_respond(chat, respond_text, reply_markup=reply_markup, cite_this=cite_this)

        # Catch any other exception and send a new message
        except Exception as edit_except:
            try:
                if hasattr(edit_except, 'message') and edit_except.message == (
                        "Message is not modified: specified new message content and reply markup are "
                        "exactly the same as a current content and reply markup of the message"):
                    return

                await State._unclean_new_respond(chat, respond_text, reply_markup=reply_markup, cite_this=cite_this)

            except Exception as reply_except:
                LOG_STATE_INSTANCE.log(logging.ERROR,
                                       f"Exception was raised when trying to send a message. Error message is {reply_except}")

    @staticmethod
    async def _unclean_new_respond(chat: Chat,
                                   respond_text, reply_markup,
                                   parse_mode='HTML', cite_this=None) -> Message:
        return await UsersStates.add_last_message_in_chat(chat,
                                                          respond_text,
                                                          reply_markup=reply_markup,
                                                          parse_mode=parse_mode,
                                                          cite_this=cite_this
                                                          )

    @staticmethod
    async def _unclean_reply_respond(chat: Chat,
                                     respond_text, reply_markup,
                                     parse_mode=None, cite_this=None) -> Message | None:
        return await UsersStates.reply_on_last_message_in_chat(chat,
                                                               respond_text,
                                                               reply_markup=reply_markup,
                                                               parse_mode=parse_mode,
                                                               cite_this=cite_this
                                                               )

    @staticmethod
    async def _unclean_edit_respond(chat: Chat,
                                    respond_text, reply_markup,
                                    parse_mode=None) -> Message | None:
        return await UsersStates.edit_last_message_in_chat(chat,
                                                           respond_text,
                                                           reply_markup=reply_markup,
                                                           parse_mode=parse_mode
                                                           )

    def _set_state_id(self, id: int):
        self._state_id = id

    def _set_state_machine_ref(self, state_machine):
        self._state_machine_ref = state_machine

    async def initialize_data(self, update, context=None):
        if update.message:
            UsersStates.set_last_message_in_chat(update.effective_chat, update.message, is_text=True)
        elif update.callback_query:
            UsersStates.set_last_message_in_chat(update.effective_chat, update.callback_query.message, is_text=False)

        self.context = context
        self.tg_chat_id = update.effective_chat.id
        await self._update_keyboard_language(update)

    async def _update_keyboard_language(self, update):
        """
        Update the keyboard language based on the user's language.
        Retrieves the user's language ID and code, and sets the keyboard language code accordingly.
        If the user's language ID or code is not available, sets the keyboard language code to 'en'.
        """
        if self._keyboard:
            user_language_id = ChatManager.get_chat_language(update.effective_chat.id)
            user_language_code = TranslationManager.get_language_code_by_id(user_language_id)

            if user_language_id is not None and user_language_code is not None:
                await self._keyboard.set_language_code(user_language_code)
            else:
                # Keep english language when couldn't get user language
                await self._keyboard.set_language_code('en')

    def _set_display_message(self, new_display_message: str):
        self._display_message = new_display_message
