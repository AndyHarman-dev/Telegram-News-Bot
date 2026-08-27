from __future__ import annotations

import asyncio
import json
import logging
from typing import Final

from app.bot.states.bot_states.bot_chat_state import BotChatState
from app.bot.states.bot_states.bot_functions_state import BotGenerateImageState
from app.bot.states.users_states import UsersStates
from app.database.db_chat import ChatManager
from app.database.db_pocket_news import PocketNewsManager
from app.database.db_tariff import TariffManager

from telegram import Update, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.error import TelegramError, BadRequest

from app.bot.states.bot_states.bot_settings_state.bot_hashtags_state import (BotHashtagsState,
                                                                             BotHashtagsState_Init,
                                                                             BotInitHashtagerState,
                                                                             BotResetHashtagerState)
from app.bot.states.bot_states.bot_settings_state.bot_blacklist_state import BotBlacklistState
from app.bot.states.bot_states.initial_states import (BotLanguageStateInit, BotStylesStateInit, BotUTCShiftStateInit,
                                                      BotResetStylesState, BotResetUTCShiftState)
from app.bot.states.bot_states import bot_features_guide_states

from app.bot.states.bot_state_machine import BotStateMachine
from telegram.ext import CommandHandler, MessageHandler, filters

import app.bot.states.bot_states.bot_menu_state as MainStates
import app.bot.states.bot_states.bot_help_states as HelpState
from app.misc.admin.admin_commands import AdminCommands
from app.misc.log_helper import LogHelper
from app.misc.utilities import number_to_emoji
from app.pipelines.pipes.chat.news_pipeline import NewsManager
from app.bot.states.bot_states.unread_news_state import UnreadNewsState

LOG_TG_BOT = LogHelper(__name__, "Telegram Bot Thread")
DOUBLED_MENU_MARK: Final = [
    '_contact_us_gen_###',
    '_help_to_main_###'
]  # WARNING: Don't use any of these marks' full text when naming states manually!


class ChatGPTTelegramBot:

    def __init__(self, token=""):
        self.token = token

    async def image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Generates an image for the given prompt using DALL·E APIs
        """
        await BotGenerateImageState.on_user_messaged(self, update, context)
        return

    async def news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Gathers news for user
        """
        await NewsManager.send_news_to(update.effective_chat.id)
        return

    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await UsersStates.del_last_menu_in_chat(UsersStates.get_chat(update))
        return await self.state_machine.transition_to_state(update, context, "menu")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await UsersStates.del_last_menu_in_chat(UsersStates.get_chat(update))
        return await self.state_machine.transition_to_state(update, context, "help_command")

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await UsersStates.del_last_menu_in_chat(UsersStates.get_chat(update))
        return await self.state_machine.transition_to_state(update, context, "reset_styles")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Return to the first state

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        user_language_code = update.effective_user.language_code
        chat_type = update.effective_chat.type
        start_state = self.state_machine.get_state_by_name("start")

        # Filter admins, owners, and moderators in groups and channels
        if chat_type in ['group', 'supergroup', 'channel']:
            # Retrieve the list of chat administrators
            admins = await context.bot.get_chat_administrators(chat_id)
            # Create a list of IDs for users who are admins, owners, or have special privileges
            admin_ids = [admin.user.id for admin in admins if admin.status in ['administrator', 'creator']]
            # Check if the user is an admin or the chat creator (owner)
            if user_id not in admin_ids:
                await update.message.reply_text('Sorry, you need to be an admin or the owner to do that.')
                return 0

        ChatManager.init_chat(update)

        # Set the language for chat
        ChatManager.set_chat_language(chat_id, user_language_code)

        return await start_state.handle(update=update, context=context)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Return to the first state
        return await self.state_machine.transition_to_state(update, context, "menu")

    async def start_tutorial(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self.state_machine.transition_to_state(update, context, "start_guide")

    async def read(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await UsersStates.del_last_menu_in_chat(UsersStates.get_chat(update))
        return await self.state_machine.transition_to_state(update, context, "unread_news")

    async def chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self.state_machine.transition_to_state(update, context, "chat")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        LOG_TG_BOT.log(logging.ERROR, f"Error while handling an update: {update} with context: {context}")
        # if self.application:
        #     await self.application.stop()
        # loop = asyncio.get_running_loop()
        # loop.stop()

    async def on_news_sent_to_pocket(self):
        for chat in UsersStates.open_chats:
            unread_count = PocketNewsManager.get_unread_news_count(chat)
            emoji_number = number_to_emoji(unread_count)
            message = f"You have {emoji_number} unread news"

            reply_markup = ReplyKeyboardMarkup(
                [["Read!"]],
                resize_keyboard=True,
                one_time_keyboard=True
            )

            await UsersStates.add_last_message_in_chat(chat, message, reply_markup=reply_markup)

    async def successful_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Get the successful payment details
        payment = update.message.successful_payment

        # Extract relevant information from the payment object
        user_id = update.effective_user.id
        amount = payment.total_amount
        currency = payment.currency
        invoice_payload = json.loads(payment.invoice_payload)

        tariff = invoice_payload['tariff']

        TariffManager.set_tariff(user_id, tariff)  # Set person's tariff

        # Send a confirmation message to the user
        await context.bot.send_message(chat_id=user_id, text="Payment successful! Thank you for your subscription.")

    def _initialize_bot_states(self):
        self.state_machine = self._create_state_machine()

        self._setup_entries()

        # Add entry point chat
        # self.state_machine.add_entry(CommandHandler(
        #    'chat', self.chat, filters=filters.ChatType.GROUP | filters.ChatType.SUPERGROUP))
        # In Chat: we just start chatting right away

        self._setup_states()

    def _setup_states(self):

        self.state_machine.add_states(self.get_states_tree())

        self._setup_init_states()

        self._setup_reset_states()

    def get_states_tree(self):

        contact_us_menu = {
            "contact_us": (
                HelpState.BotContactUsState,
                {
                    "write_problem": (HelpState.BotWriteProblemState, {}),
                    "suggest_idea": (HelpState.BotSuggestIdeaState, {})
                }
            )
        }
        help_menu = {
            "bot_skills": (HelpState.BotSkillsState, {}),
            "setting_reset": (
                HelpState.BotSettingResetState,
                {
                    "are_you_sure": (HelpState.BotAreYouSureState, {})
                }
            ),
            "faq": (HelpState.BotFAQState, {}),
            **contact_us_menu
        }
        contact_us_menu_in_main = self.doubled_menu_modified(contact_us_menu, DOUBLED_MENU_MARK[0])
        help_menu_in_main = self.doubled_menu_modified(help_menu, DOUBLED_MENU_MARK[1])

        return {
            # First initial states
            # 'start': (BotLanguageState_Init, {}),
            'start': (BotStylesStateInit, {}),
            # 'init_hashtags': (BotHashtagsState_Init, {}),
            'init_hashtager': (BotInitHashtagerState, {}),
            'init_utc_shift': (BotUTCShiftStateInit, {}),
            'chat': (BotChatState, {}),
            "help_command": (
                HelpState.BotHelpState,
                help_menu
            ),

            'unread_news': (UnreadNewsState, {}),

            'menu': (
                MainStates.BotMenuState,
                {
                    "functions": (MainStates.FuncState.BotFunctionsState,
                                  {
                                      "get_news": (MainStates.FuncState.BotGetNewsState, {}),
                                      # "generate_post": (MainStates.FuncState.BotGeneratePostState, {}),
                                      "generate_image": (MainStates.FuncState.BotGenerateImageState, {}),
                                  }
                                  ),
                    "settings": (MainStates.SettingsState.BotSettingsState,
                                 {
                                     "hashtags": (BotHashtagsState, {}),
                                     "blacklist": (BotBlacklistState, {}),
                                     "models": (MainStates.SettingsState.BotLLMSelectorState, {}),
                                     "language": (MainStates.SettingsState.BotLanguageState, {}),
                                     "style": (MainStates.SettingsState.BotStyleState, {}),
                                     "utc_shift": (MainStates.SettingsState.BotUTCShiftState, {}),
                                 }
                                 ),
                    "pay_to_pasha": (MainStates.SubscrState.BotPayToPashaState, {}),

                    **contact_us_menu_in_main,
                    "help": (
                        MainStates.BotHelpState,
                        help_menu_in_main
                    ),
                }
            ),
            "subscription": (MainStates.SubscrState.BotManageSubscriptionState,
                             {
                                "pay": (MainStates.SubscrState.BotPayState, {}),
                                "info": (MainStates.SubscrState.BotInfoLimitsState, {}),
                             }
                             ),
            'reset_styles': (BotResetStylesState, {}),
            'reset_utc_shift': (BotResetUTCShiftState, {}),
            'reset_hashtager': (BotResetHashtagerState, {}),

            'start_guide': (bot_features_guide_states.BotStartGuideState, {}),
            'show_llm_communication': (bot_features_guide_states.BotShowLLMCommunicationState, {}),
            'news_sending': (bot_features_guide_states.BotNewsSendingState, {}),
            'image_generation_prompt': (bot_features_guide_states.BotImageGenerationPromptState, {}),
            'guided_generate_image': (bot_features_guide_states.BotGuidedGenerateImageState, {}),
            'end': (bot_features_guide_states.BotEndGuideState, {}),

            'new_llm_communication': (bot_features_guide_states.BotGettingRequestForGenerateMessage, {}),
            'new_image_generation': (bot_features_guide_states.BotGettingRequestForGenerateImage, {}),
            'new_end': (bot_features_guide_states.BotDoEverything, {}),
        }

    def _setup_reset_states(self):
        reset_styles = self.state_machine.get_state_by_name("reset_styles")
        reset_utc_shift = self.state_machine.get_state_by_name("reset_utc_shift")
        reset_hashtager = self.state_machine.get_state_by_name("reset_hashtager")
        reset_styles.set_next(reset_utc_shift)
        reset_utc_shift.set_next(reset_hashtager)

    def _setup_init_states(self):
        # Compound the chaing of responsibility for the initialization of the user
        init_styles = self.state_machine.get_state_by_name("start")
        init_hashtager = self.state_machine.get_state_by_name("init_hashtager")
        init_utc_shift = self.state_machine.get_state_by_name("init_utc_shift")
        start_guide = self.state_machine.get_state_by_name("start_guide")
        # COR: start -> init_styles -> init_utc_shift -> init_hashtags -> menu
        # NEW COR (2024.07.19): start -> init_styles -> init_utc_shift -> init_hashtager -> menu
        init_styles.set_next(init_utc_shift)
        init_utc_shift.set_next(init_hashtager)
        init_hashtager.set_next(start_guide)

    def _setup_entries(self):
        # Add Entry point menu
        self.state_machine.add_entry(CommandHandler('menu', self.menu))
        self.state_machine.add_entry(CommandHandler('reset', self.reset))
        self.state_machine.add_entry(CommandHandler('read', self.read))
        self.state_machine.add_entry(CommandHandler('test', self.start_tutorial))
        self.state_machine.add_entry(CommandHandler('start', self.start))
        self.state_machine.add_entry(CommandHandler('image', self.image))
        self.state_machine.add_entry(CommandHandler('news', self.news))
        self.state_machine.add_entry(CommandHandler('help', self.help))

    @staticmethod
    async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from app.bot.states.state import State

        if not await UsersStates.menu_ref_existence_checking(update.effective_chat, update):

            try:
                await update.callback_query.message.delete()

            except BadRequest:
                try:
                    await update.callback_query.edit_message_reply_markup(
                        reply_markup=InlineKeyboardMarkup([])
                    )

                except BadRequest:
                    respond_text: str = await State.get_any_display_message(update, context, "warning_messages",
                                                                            "old_menu_cannot_be_deleted")
                    respond_text = respond_text.replace('/1', '/menu').replace('1/', '/menu')
                    await update.callback_query.answer(respond_text, show_alert=True)
                    return None

            if not UsersStates.menu_available_for_changes(update.effective_chat):
                respond_text: str = await State.get_any_display_message(update, context, "warning_messages",
                                                                        "old_menu_deleted")
                respond_text = respond_text.replace('/1', '/menu').replace('1/', '/menu')
                await State._unclean_new_respond(update.effective_chat, respond_text, None)
            return True
        return False

    def run(self):
        """
        Runs the bot indefinitely until the user presses Ctrl+C
        """
        application = (ApplicationBuilder().
                       token(self.token).
                       pool_timeout(30.0).
                       read_timeout(30.0).
                       connect_timeout(30.0).
                       connection_pool_size(200).
                       build())

        self._initialize_bot_states()
        self._add_handlers(application)
        #
        # Bind to global news sending event.
        # if not NewsManager.ON_NEWS_SENT.is_registered(self.on_news_sent_to_pocket):
        #    NewsManager.ON_NEWS_SENT.register(self.on_news_sent_to_pocket)
        #
        application.run_polling()

    def _add_handlers(self, application):
        # Add states to the telegram API
        conv_handler = ConversationHandler(
            entry_points=self.state_machine.get_entry_points(),
            states=self.state_machine.get_states(),
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CommandHandler('menu', self.menu),
                CommandHandler('help', self.help),
                CommandHandler('read', self.read),
                CommandHandler('reset', self.reset)
            ]
        )
        application.add_handler(conv_handler)
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.chat))
        application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, self.successful_payment_callback))
        application.add_handler(CommandHandler("execute", AdminCommands.execute_dynamic_command))
        application.add_handler(CommandHandler("start_tutorial", self.start_tutorial))
        application.add_error_handler(self.error_handler)

    @staticmethod
    def doubled_menu_modified(recurse_dict, addition_string):
        if not recurse_dict:
            return {}

        new_dict = {}
        for key, (value, nested_dict) in recurse_dict.items():
            new_key = key + addition_string
            new_nested_dict = ChatGPTTelegramBot.doubled_menu_modified(nested_dict, addition_string)
            new_dict[new_key] = (value, new_nested_dict)

        return new_dict

    @staticmethod
    def menu_generalization(original_string):
        for pattern_string in DOUBLED_MENU_MARK:
            if pattern_string in original_string:
                while pattern_string in original_string:
                    original_string = original_string.replace(pattern_string, '')
                return original_string
        return original_string

    def _create_state_machine(self) -> BotStateMachine:
        return BotStateMachine()
