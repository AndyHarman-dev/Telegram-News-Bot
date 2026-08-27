from typing import Callable

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from app.bot.states import state
from app.database.db_pocket_news import PocketNewsManager


class UnreadNewsState(state.State):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_error = None
        self._complete_callback = None

    async def enter_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.initialize_data(update, context)

        chat_id = update.effective_chat.id

        await UnreadNewsState.create_message_for_chat(chat_id)

        return self.get_state_id()

    @staticmethod
    def number_to_emoji(number):
        emoji_numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        if number <= 0:
            return emoji_numbers[0]
        str_number = ""
        while number > 0:
            str_number = emoji_numbers[number % 10] + str_number
            number //= 10
        return str_number

    @staticmethod
    async def create_message_for_chat(chat_id):
        from app.bot.states.users_states import UsersStates

        unread_count = PocketNewsManager.get_unread_news_count(chat_id)
        if unread_count > 0:
            if unread_count > 5:
                message = await UnreadNewsState.get_locale_text_by_chat_id(chat_id, 'states',
                                                                           "unread_news", "a_lot_of_news")
            else:
                message = await UnreadNewsState.get_locale_text_by_chat_id(chat_id, 'states',
                                                                           "unread_news", "some_news")
            emoji_number = UnreadNewsState.number_to_emoji(unread_count)
            button = await UnreadNewsState.get_locale_text_by_chat_id(chat_id, 'misc', "reply_keyboard", "get_5")
            message = message.replace('/1', emoji_number).replace('/2', button)
            message = message.replace('1/', emoji_number).replace('2/', button)
            reply_markup = ReplyKeyboardMarkup([[button]])
            await UsersStates.delete_last_reply_in_chat(chat_id)
            message = await UsersStates.add_last_message_in_chat(chat_id, message, reply_markup)
            UsersStates.set_last_reply_in_chat(chat_id, message)
        else:
            message = await UnreadNewsState.get_locale_text_by_chat_id(chat_id, 'states',
                                                                       "unread_news", "no_news")
            message = message.replace('/1', '/menu')
            message = message.replace('1/', '/menu')
            await UsersStates.add_last_message_in_chat(chat_id, message)

    @staticmethod
    async def create_update_message_for_chat(chat_id):
        from app.bot.states.users_states import UsersStates
        message = await UnreadNewsState.get_locale_text_by_chat_id(chat_id, 'states',
                                                                   "unread_news", "update_news")
        await UsersStates.delete_last_reply_in_chat(chat_id)
        message = await UsersStates.add_last_message_in_chat(chat_id, message)
        UsersStates.set_last_reply_in_chat(chat_id, message)
