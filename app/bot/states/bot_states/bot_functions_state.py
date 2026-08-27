import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from app.bot.states import state
from app.bot.states.users_states import UsersStates
from app.bot.telegram_helper import TelegramHelper

from app.database.db_tariff import TariffManager
from app.database.db_users_action import UserActionManager

from app.factories.ai_factories import AIServiceFacade, AIQualityServiceFactory
from app.llm.image_generator.image_generation_requests import ImgPaths
from app.pipelines.pipes.chat.news_pipeline import NewsManager
from app.misc.log_helper import LogHelper

LOG_FUNCTIONS_STATE = LogHelper(__name__, "Functions State Thread")


class BotGetNewsState(state.State):
    # Defines BotGetNewsState
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id

        # Send a confirmation message to the user
        await context.bot.send_message(chat_id=chat_id, text="LOADING...")

        # typing simulations
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        asyncio.create_task(NewsManager.send_news_to(chat_id))

        return await super().enter_state(update, context)


class BotGenerateImageState(state.State):
    # Defines BotGenerateImageState
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        LOG_FUNCTIONS_STATE.log(logging.INFO, "Bot enter in Generate Image State")
        return await super().enter_state(update, context)

    async def on_user_messaged(self, update: Update, context: ContextTypes.DEFAULT_TYPE):



        await UsersStates.del_last_message_in_chat(update.effective_chat)
        chat_id = update.effective_chat.id
        user_id = update.message.from_user.id
        prompt = update.message.text
        datetime = str(update.message.date.date()) + str(update.message.date.time()).replace(':', '_')
        image_name = f"{chat_id}_{datetime}"

        #register user activity in DB
        UserActionManager.create_user_action(user_id, "generate_image")

        if TariffManager.has_user_exceeded_monthly_quota(user_id):  # Check if the user has exceeded their monthly quota
            await self._respond(update.effective_chat,
                                await self.get_any_display_message(update, context, "warning_messages", "exceeded_monthly_quota"),
                                None)
            return self.get_state_id()
        asyncio.create_task(BotGenerateImageState.image_generating(chat_id, prompt, update, context))
        # Return to the standard state
        return await self.fallback(update, context)

    @staticmethod
    async def image_generating(chat_id, prompt, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Send a loading animation and get its ID
        loading_message_id = await TelegramHelper.send_loading_animation(update, context, 5)

        # Generate the image
        try:
            gen = await AIServiceFacade.create_image_generator(factory_type=AIQualityServiceFactory,
                                                               size="1792x1024",
                                                               n=1
                                                               )

            img_path = await gen.generate(prompt)
            if isinstance(img_path, ImgPaths):
                image_path = img_path.paths[0]
                await context.bot.send_document(chat_id=chat_id, document=image_path)
                await context.bot.delete_message(chat_id=chat_id, message_id=loading_message_id)
        except Exception as e:
            LOG_FUNCTIONS_STATE.raise_exception_with_log(ValueError(f"An error ocurred while trying to generate an image. {str(e)}"))


class BotGeneratePostState(state.State):
    # Defines BotGeneratePostState
    pass


class BotFunctionsState(state.State):
    # Defines Function state of telegram bot
    pass
