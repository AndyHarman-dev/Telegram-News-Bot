import asyncio
import logging
from datetime import datetime, timedelta
import random

from telegram.constants import ChatAction

import app.bot.states.state as state
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot, Message
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.config import telegram_config
from app.bot.states.users_states import UsersStates
from app.database.db_chat import ChatManager
from app.database.db_message import MessageManager
from app.database.db_translation import TranslationManager
from app.factories.ai_factories import AIServiceFacade, AIQualityServiceFactory, AIAllServiceFactory
from app.llm.image_generator.image_generation_requests import ImgPaths
from app.misc.admin.admin_manager import AdminManager
from app.misc.exceptions import FallbackException
from app.misc.keyboard import Keyboard, TextRetrievedKeyboard
from app.misc.localization.lang_loc import make_localized_text
from app.pipelines.pipes.chat.news_pipeline import NewsManager
from app.misc.log_helper import LogHelper
from app.interfaces.cor import BaseHandler

LOG_GUIDE = LogHelper(__name__, "Guide State Thread")


class GuideState(state.State):
    _seconds_limit = 1


class BotStartGuideState(GuideState, BaseHandler):
    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)
        await self._respond(update.effective_chat, await self.get_display_message(update, context), None)
        return await self.transition_to_state(update, context, 'new_llm_communication')

    async def handle(self, *args, **kwargs):
        return await self.transition_to_state(kwargs['update'], kwargs['context'], self.get_state_name())


class BotGettingRequestForGenerateMessage(GuideState, BaseHandler):
    _B_HAS_FALLBACK = False
    QUESTION_MAX_COUNT = 3

    class _LLMCommunicationKeyboard(TextRetrievedKeyboard):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.llm_state = None

        async def transform_button_text(self, key, data=None):
            locale = await make_localized_text(self._lang_code)
            button_text = await locale.get_text(f"misc.guide_keyboard.{key.lower()}")
            return button_text

    _KEYBOARD_CLASS = _LLMCommunicationKeyboard

    def __init__(self, keyboard_layout, state_name="No name state", parent_state=None):
        super().__init__(keyboard_layout, state_name, parent_state)
        questions = [f'question_{i}' for i in range(1, self.QUESTION_MAX_COUNT + 1)]
        keyboard_layout = {question: question for question in questions}
        self._keyboard = self._instantiate_default_keyboard(keyboard_layout)
        self._keyboard.style_state = self

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)
        keyboard_layout = await self.get_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard_layout)
        chat = update.effective_chat
        await self._unclean_new_respond(chat, await self.get_display_message(update, context), None)
        context.chat_data['gen_message_for_deleting']: Message = \
            await self._unclean_new_respond(chat,
                                            await self.get_current_display_message(update,
                                                                                   context,
                                                                                   "auxiliary_message"),
                                            reply_markup)
        return self.get_state_id()

    async def on_user_messaged(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        async def create_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat = update.message.chat
            await self.initialize_data(update, context)
            bot_name = context.bot.username
            user_msg = context.chat_data.get('delayed_message', f'@{bot_name} tell me interesting story, please')
            del context.chat_data['delayed_message']
            chat_type = update.effective_chat.type
            if (chat_type not in {"group", "supergroup"}) or (f"@{bot_name}" in user_msg):
                user_msg = user_msg.replace(f"@{bot_name}", "")
                ChatManager.init_chat(update)
                chat_id = update.effective_chat.id
                user_id = update.message.from_user.id
                await MessageManager.create_message(user_id, chat_id, 1, user_msg)
                system_message = TranslationManager.get_translation_command(chat_id)
                preferred_models = await AIQualityServiceFactory.get_models()
                request_failed = False
                async with Bot(token=telegram_config['token']) as bot:
                    while True:
                        try:
                            await bot.send_chat_action(chat_id=chat_id, action='typing')
                            fr = await AIServiceFacade.create_chat_completion(factory_type=AIQualityServiceFactory,
                                                                              models=preferred_models,
                                                                              system=system_message,
                                                                              stream=False)
                            response = await fr.prompt(user_msg)
                            await self._unclean_new_respond(chat,
                                                            response,
                                                            None,
                                                            None,
                                                            cite_this=context.chat_data.get('delayed_message.id', None))
                            del context.chat_data['delayed_message.id']
                            await MessageManager.create_message(user_id, chat_id, 2, response)
                            break
                        except FallbackException as e:
                            if request_failed:
                                await AdminManager.send_admin_message(
                                    f"User {update.effective_user.id}, {update.effective_user.first_name} {update.effective_user.last_name} "
                                    f"has failed to communicate with bot.\n User sent message: {user_msg}. \n Exception reason: {e.message}")
                                break
                            await self._unclean_reply_respond(chat,
                                                              await self.get_any_display_message(update,
                                                                                                 context,
                                                                                                 "warning_messages",
                                                                                                 "model_unavailable"),
                                                              reply_markup=None
                                                              )
                            await asyncio.sleep(5)
                            await UsersStates.del_last_message_in_chat(chat)
                            preferred_models = await AIAllServiceFactory.get_models()
                            request_failed = True

        user_prompt = update.message.text
        bot_username = f"@{context.bot.username}"
        context.chat_data['delayed_message'] = user_prompt.replace(bot_username, '')
        context.chat_data['delayed_message.id'] = update.message.message_id
        await UsersStates.delete_message(context.chat_data.get('gen_message_for_deleting', None))
        del context.chat_data['gen_message_for_deleting']
        asyncio.create_task(create_message(update, context))
        return await self.transition_to_state(update, context, 'new_end')


class BotGettingRequestForGenerateImage(GuideState, BaseHandler):
    _B_HAS_FALLBACK = False
    PROMT_IMAGES_MAX = 10
    PROMT_IMAGES_CURRENT = 5

    class _ImageGenerationKeyboard(TextRetrievedKeyboard):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.llm_state = None

        async def transform_button_text(self, key, data=None):
            locale = await make_localized_text(self._lang_code)
            button_text = await locale.get_text(f"misc.guide_keyboard.{key.lower()}")
            return button_text

    _KEYBOARD_CLASS = _ImageGenerationKeyboard

    def __init__(self, keyboard_layout, state_name="No name state", parent_state=None):
        super().__init__(keyboard_layout, state_name, parent_state)
        images_sample = random.sample(list(range(1, self.PROMT_IMAGES_MAX + 1)), self.PROMT_IMAGES_CURRENT)
        promt_images = [f'image_{i}' for i in images_sample]
        keyboard_layout = {promt_image: promt_image for promt_image in promt_images}
        self._keyboard = self._instantiate_default_keyboard(keyboard_layout)
        self._keyboard.style_state = self

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)
        chat = update.effective_chat
        await self._unclean_reply_respond(chat, await self.get_display_message(update, context), None)
        keyboard_layout = await self.get_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard_layout)
        context.chat_data['gen_image_for_deleting']: Message = \
            await self._unclean_reply_respond(chat,
                                              await self.get_current_display_message(update,
                                                                                     context,
                                                                                     "auxiliary_message"),
                                              reply_markup)
        return self.get_state_id()

    async def on_user_messaged(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        async def create_image(_update: Update, _context: ContextTypes.DEFAULT_TYPE):
            chat = _update.effective_chat
            await self._unclean_new_respond(chat,
                                            await self.get_current_display_message(_update,
                                                                                   _context,
                                                                                   category="update_state",
                                                                                   subcategory="process") +
                                            _context.chat_data.get('delayed_image', 'some cool image'),
                                            None,
                                            None,
                                            _context.chat_data.get('delayed_image.id', None))
            try:
                gen = await AIServiceFacade.create_image_generator(factory_type=AIQualityServiceFactory,
                                                                   size="1792x1024",
                                                                   n=1)
                img_path = await gen.generate(user_prompt)
                if isinstance(img_path, ImgPaths):
                    image_path = img_path.paths[0]
                    await self._unclean_new_respond(chat,
                                                    await self.get_current_display_message(_update,
                                                                                           _context,
                                                                                           category="update_state",
                                                                                           subcategory="success"),
                                                    None,
                                                    None,
                                                    _context.chat_data.get('delayed_image.id', None))
                    await _context.bot.send_document(chat_id=_update.effective_chat.id, document=image_path)
            except Exception as e:
                await self._unclean_new_respond(chat,
                                                await self.get_current_display_message(_update,
                                                                                       _context,
                                                                                       category="update_state",
                                                                                       subcategory="wrong") +
                                                e,
                                                None,
                                                None,
                                                _context.chat_data.get('delayed_image.id', None))
            del _context.chat_data['delayed_image']
            del _context.chat_data['delayed_image.id']

        user_prompt = update.message.text
        bot_username = f"@{context.bot.username}"
        context.chat_data['delayed_image'] = user_prompt.replace(bot_username, '')
        context.chat_data['delayed_image.id'] = update.message.message_id
        await UsersStates.delete_message(context.chat_data.get('gen_image_for_deleting', None))
        del context.chat_data['gen_image_for_deleting']
        asyncio.create_task(create_image(update, context))
        return await self.transition_to_state(update, context, 'new_end')


class BotDoEverything(GuideState, BaseHandler):
    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        async def create_news(_update: Update, _context: ContextTypes.DEFAULT_TYPE):
            chat_id = _update.effective_chat.id
            await _context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await NewsManager.send_news_to(chat_id, 2)
            await self._unclean_new_respond(_update.effective_chat,
                                            await self.get_current_display_message(_update,
                                                                                   _context,
                                                                                   category="update_state"),
                                            None,
                                            None,
                                            _context.chat_data.get('delayed_news.id', None))
            del _context.chat_data['delayed_news.id']

        await self.initialize_data(update, context)
        respond_text: str = await self.get_display_message(update, context)
        respond_text = respond_text.replace('/1', '/menu').replace('/2', '/help').replace('/3', '/reset')
        respond_text = respond_text.replace('1/', '/menu').replace('2/', '/help').replace('3/', '/reset')
        await self._unclean_new_respond(update.effective_chat,
                                        respond_text,
                                        None)
        context.chat_data['delayed_news.id'] = UsersStates.get_last_message_in_chat(update.effective_chat).message_id
        asyncio.create_task(create_news(update, context))
        return self.get_state_id()


class BotShowLLMCommunicationState(GuideState):
    _seconds_limit = 2
    _B_HAS_FALLBACK = False
    QUESTION_MAX_COUNT = 3

    class _LLMCommunicationKeyboard(TextRetrievedKeyboard):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.llm_state = None

        async def transform_button_text(self, key, data=None):
            locale = await make_localized_text(self._lang_code)
            button_text = await locale.get_text(f"misc.guide_keyboard.{key.lower()}")
            return button_text

    _KEYBOARD_CLASS = _LLMCommunicationKeyboard

    def __init__(self, keyboard_layout, state_name="No name state", parent_state=None):
        super().__init__(keyboard_layout, state_name, parent_state)
        questions = [f'question_{i}' for i in range(1, self.QUESTION_MAX_COUNT + 1)]
        keyboard_layout = {question: question for question in questions}
        self._keyboard = self._instantiate_default_keyboard(keyboard_layout)
        self._keyboard.style_state = self

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)
        keyboard_layout = await self.get_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard_layout)
        chat = update.effective_chat
        await self._unclean_reply_respond(chat, await self.get_display_message(update, context), None)
        await self._unclean_reply_respond(chat,
                                          await self.get_current_display_message(update,
                                                                                 context,
                                                                                 "auxiliary_message"),
                                          reply_markup)
        return self.get_state_id()

    async def on_user_messaged(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.chat_data['create_new_message'] = True
        context.chat_data['cite_this_message'] = update.message.message_id
        await super().on_user_messaged(update, context)
        return await self.transition_to_state(update, context, 'news_sending')


class BotNewsSendingState(GuideState):
    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        async def sending_news(_update: Update, _context: ContextTypes.DEFAULT_TYPE):
            chat_id = _update.effective_chat.id
            await _context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await _context.bot.send_message(chat_id=chat_id, text="LOADING...")
            await NewsManager.send_news_to(chat_id, 5)

        await self.initialize_data(update, context)
        await self._unclean_reply_respond(update.effective_chat, await self.get_display_message(update, context), None)
        asyncio.create_task(sending_news(update, context))
        return await self.transition_to_state(update, context, 'image_generation_prompt')


class BotImageGenerationPromptState(GuideState):
    _B_HAS_FALLBACK = False
    PROMT_IMAGES_MAX = 10
    PROMT_IMAGES_CURRENT = 5

    class _ImageGenerationKeyboard(TextRetrievedKeyboard):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.llm_state = None

        async def transform_button_text(self, key, data=None):
            locale = await make_localized_text(self._lang_code)
            button_text = await locale.get_text(f"misc.guide_keyboard.{key.lower()}")
            return button_text

    _KEYBOARD_CLASS = _ImageGenerationKeyboard

    def __init__(self, keyboard_layout, state_name="No name state", parent_state=None):
        super().__init__(keyboard_layout, state_name, parent_state)
        images_sample = random.sample(list(range(1, self.PROMT_IMAGES_MAX + 1)), self.PROMT_IMAGES_CURRENT)
        promt_images = [f'image_{i}' for i in images_sample]
        keyboard_layout = {promt_image: promt_image for promt_image in promt_images}
        self._keyboard = self._instantiate_default_keyboard(keyboard_layout)
        self._keyboard.style_state = self

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)
        chat = update.effective_chat
        await self._unclean_reply_respond(chat, await self.get_display_message(update, context), None)
        keyboard_layout = await self.get_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard_layout)
        await self._unclean_reply_respond(chat, await self.get_current_display_message(update, context, "auxiliary_message"),
                                          reply_markup)
        return self.get_state_id()

    async def on_user_messaged(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await UsersStates.del_last_message_in_chat(update.effective_chat)
        user_prompt = update.message.text
        bot_username = f"@{context.bot.username}"
        context.user_data['image_prompt'] = user_prompt.replace(bot_username, '')
        return await self.transition_to_state(update, context, 'guided_generate_image')


class BotGuidedGenerateImageState(GuideState):
    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        async def sending_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
            try:
                # Generate image
                gen = await AIServiceFacade.create_image_generator(factory_type=AIQualityServiceFactory,
                                                                   size="1792x1024",
                                                                   n=1)
                img_path = await gen.generate(user_prompt)
                if isinstance(img_path, ImgPaths):
                    image_path = img_path.paths[0]
                    await self._unclean_reply_respond(chat, await self.get_current_display_message(update, context,
                                                                                                   subcategory="success"),
                                                      None)
                    await context.bot.send_document(chat_id=update.effective_chat.id, document=image_path)
            except Exception as e:
                await self._unclean_reply_respond(chat,
                                                  await self.get_current_display_message(update, context,
                                                                                         subcategory="wrong"),
                                                  None)

        await self.initialize_data(update, context)
        chat = update.effective_chat
        user_prompt = context.user_data.get('image_prompt', 'default prompt')
        await self._unclean_reply_respond(chat, await self.get_current_display_message(update, context, subcategory="process") + user_prompt,
                                          None)

        asyncio.create_task(sending_image(update, context))

        return await self.transition_to_state(update, context, 'end')


class BotEndGuideState(GuideState):
    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)

        await self._unclean_reply_respond(update.effective_chat,
                                          await self.get_display_message(update, context), None)
        return await self.transition_to_state(update, context, 'menu')
