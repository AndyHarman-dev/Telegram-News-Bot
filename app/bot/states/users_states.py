import logging

from telegram import Bot, Chat, Update, Message
from app.bot.config import telegram_config
from app.interfaces.users_messages import IUsersStates
from app.misc.log_helper import LogHelper

LOG_USER_STATE_INSTANCE = LogHelper(__name__, "Users' State Thread")


class UsersStates(IUsersStates):
    open_chats: dict[int, dict] = {}
    _timed_out_retreats = 3

    # appropriate fields name:
    __last_message = "last_message"
    __is_text = "is_text"
    __ref = "ref"
    __last_reply = "reply"

    @classmethod
    def get_default_chat(cls, chat: Chat | int):
        chat = UsersStates.to_chat_id(chat)
        return {chat: {cls.__last_message: {cls.__is_text: True,
                                            cls.__ref: None
                                            },
                       cls.__last_reply: None
                       }
                }

    @classmethod
    def set_last_reply_in_chat(cls, chat: Chat | int, message: Message):
        chat = UsersStates.to_chat_id(chat)
        if chat not in cls.open_chats:
            cls.open_chats.update(cls.get_default_chat(chat))
        cls.open_chats[chat][cls.__last_reply] = message

    @classmethod
    async def delete_last_reply_in_chat(cls, chat: Chat | int):
        chat = UsersStates.to_chat_id(chat)
        if chat not in cls.open_chats:
            return None
        reply_message: Message = cls.open_chats[chat][cls.__last_reply]
        if reply_message is not None:
            await cls.delete_message(reply_message)

    @classmethod
    def set_last_message_in_chat(cls, chat: Chat | int, message: Message, is_text: bool = False):
        chat = UsersStates.to_chat_id(chat)
        if chat not in cls.open_chats:
            cls.open_chats.update(cls.get_default_chat(chat))
        cls.open_chats[chat][cls.__last_message][cls.__ref] = message
        cls.open_chats[chat][cls.__last_message][cls.__is_text] = is_text

    @classmethod
    def get_last_message_in_chat(cls, chat: Chat | int) -> Message | None:
        chat = UsersStates.to_chat_id(chat)
        if chat not in cls.open_chats:
            raise KeyError('This chat does not exist')
        return cls.open_chats[chat][cls.__last_message][cls.__ref]

    @classmethod
    def message_available_for_changes(cls, chat: Chat | int):
        chat = UsersStates.to_chat_id(chat)
        return chat in cls.open_chats and cls.open_chats[chat][cls.__last_message][cls.__ref] is not None

    @classmethod
    def menu_available_for_changes(cls, chat: Chat | int):
        chat = UsersStates.to_chat_id(chat)
        return cls.message_available_for_changes(chat) and not cls.open_chats[chat][cls.__last_message][cls.__is_text]

    @classmethod
    async def add_last_message_in_chat(cls, chat: Chat | int,
                                       text: str,
                                       reply_markup=None,
                                       parse_mode=None,
                                       cite_this=None) -> Message | None:
        chat = UsersStates.to_chat_id(chat)

        current_retreat, successfully = 0, False
        while current_retreat < UsersStates._timed_out_retreats and not successfully:
            try:
                async with Bot(token=telegram_config['token']) as bot:
                    new_message: Message = await bot.send_message(chat_id=chat, text=text, reply_markup=reply_markup,
                                                                  parse_mode=parse_mode, reply_to_message_id=cite_this)
                successfully = True
            except Exception as e:
                if 'timed out' not in str(e).lower():
                    LOG_USER_STATE_INSTANCE.log(logging.ERROR,
                                                f"Unexpected error \"{e}\" while sending message in chat {chat}")
                    return None
                LOG_USER_STATE_INSTANCE.log(logging.ERROR,
                                            f"Timeout error \"{e}\" while sending message in chat {chat}")
                current_retreat += 1

        if not successfully:
            return None

        is_text = True if reply_markup is None else False
        cls.set_last_message_in_chat(chat, new_message, is_text)
        return new_message

    @classmethod
    async def reply_on_last_message_in_chat(cls, chat: Chat | int,
                                            text: str,
                                            reply_markup=None,
                                            parse_mode=None,
                                            cite_this=None) -> Message | None:
        chat = UsersStates.to_chat_id(chat)
        if cls.message_available_for_changes(chat):
            return await cls.__reply_on_last_message_from_chat(chat, text, reply_markup, parse_mode, cite_this)
        return None

    @classmethod
    async def edit_last_message_in_chat(cls, chat: Chat | int,
                                        text: str,
                                        reply_markup=None,
                                        parse_mode=None) -> Message | None:
        chat = UsersStates.to_chat_id(chat)
        if cls.message_available_for_changes(chat):
            return await cls.__edit_massage_from_chat(chat, text, reply_markup, parse_mode)
        return None

    @classmethod
    async def edit_last_menu_in_chat(cls, chat: Chat | int,
                                     text: str,
                                     reply_markup=None,
                                     parse_mode=None) -> Message | None:
        chat = UsersStates.to_chat_id(chat)
        if cls.menu_available_for_changes(chat):
            return await cls.__edit_massage_from_chat(chat, text, reply_markup, parse_mode)
        return None

    @classmethod
    async def del_last_message_in_chat(cls, chat: Chat | int):
        chat = UsersStates.to_chat_id(chat)
        if cls.message_available_for_changes(chat):
            await cls.__delete_massage_from_chat(chat)

    @classmethod
    async def del_last_menu_in_chat(cls, chat: Chat | int):
        chat = UsersStates.to_chat_id(chat)
        if cls.menu_available_for_changes(chat):
            await cls.__delete_massage_from_chat(chat)

    @classmethod
    async def menu_ref_existence_checking(cls, chat: Chat | int, update: Update) -> bool:
        chat = UsersStates.to_chat_id(chat)
        if not cls.menu_available_for_changes(chat):
            return False
        return update.callback_query.message.message_id == cls.open_chats[chat][cls.__last_message][cls.__ref].message_id

    @classmethod
    async def __edit_massage_from_chat(cls, chat: int,
                                       text: str,
                                       reply_markup=None,
                                       parse_mode=None) -> Message:
        old_message: Message = cls.open_chats[chat][cls.__last_message][cls.__ref]
        new_message: Message = await old_message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        cls.open_chats[chat][cls.__last_message][cls.__ref] = new_message
        cls.open_chats[chat][cls.__last_message][cls.__is_text] = True if reply_markup is None else False
        return new_message

    @classmethod
    async def __reply_on_last_message_from_chat(cls, chat: int,
                                                text: str,
                                                reply_markup=None,
                                                parse_mode=None,
                                                cite_this=None) -> Message | None:
        old_message: Message = cls.open_chats[chat][cls.__last_message][cls.__ref]

        current_retreat, successfully = 0, False
        while current_retreat < UsersStates._timed_out_retreats and not successfully:
            try:
                new_message: Message = await old_message.reply_text(text,
                                                                    reply_markup=reply_markup,
                                                                    parse_mode=parse_mode,
                                                                    reply_to_message_id=cite_this)
                successfully = True
            except Exception as e:
                if 'timed out' not in str(e).lower():
                    LOG_USER_STATE_INSTANCE.log(logging.ERROR,
                                                f"Unexpected error \"{e}\" while sending message in chat {chat}")
                    return None
                LOG_USER_STATE_INSTANCE.log(logging.ERROR,
                                            f"Timeout error \"{e}\" while sending message in chat {chat}")
                current_retreat += 1

        if not successfully:
            return None

        cls.open_chats[chat][cls.__last_message][cls.__ref] = new_message
        cls.open_chats[chat][cls.__last_message][cls.__is_text] = True if reply_markup is None else False
        return new_message

    @classmethod
    async def __delete_massage_from_chat(cls, chat: int):
        old_message: Message = cls.open_chats[chat][cls.__last_message][cls.__ref]

        current_retreat, successfully = 0, False
        while current_retreat < UsersStates._timed_out_retreats and not successfully:
            try:
                await UsersStates.delete_message(old_message)
                successfully = True
            except Exception as e:
                if 'timed out' not in str(e).lower():
                    LOG_USER_STATE_INSTANCE.log(logging.ERROR,
                                                f"Unexpected error \"{e}\" while deleting message in chat {chat}")
                    return None
                LOG_USER_STATE_INSTANCE.log(logging.ERROR,
                                            f"Timeout error \"{e}\" while sending deleting in chat {chat}")
                current_retreat += 1

        if not successfully:
            LOG_USER_STATE_INSTANCE.log(logging.ERROR,
                                        f"Repeatedly timeout error. Message cannot be deleted.")
            return None

        cls.open_chats[chat][cls.__last_message][cls.__ref] = None
        cls.open_chats[chat][cls.__last_message][cls.__is_text] = True

    @staticmethod
    async def delete_message(message: Message):
        current_retreat, successfully = 0, False
        while current_retreat < UsersStates._timed_out_retreats and not successfully:
            try:
                async with Bot(token=telegram_config['token']) as bot:
                    await bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
                successfully = True
            except Exception as e:
                if 'timed out' not in str(e).lower():
                    LOG_USER_STATE_INSTANCE.log(logging.ERROR,
                                                f"Unexpected error \"{e}\" while deleting message")
                    return None
                LOG_USER_STATE_INSTANCE.log(logging.ERROR,
                                            f"Timeout error \"{e}\" while deleting message")
                current_retreat += 1

        if not successfully:
            LOG_USER_STATE_INSTANCE.log(logging.ERROR,
                                        f"Repeatedly timeout error. Message cannot be deleted.")

    @staticmethod
    def get_chat(update: Update):
        if update.message:
            return update.message.chat
        return update.callback_query.message.chat

    @staticmethod
    def to_chat_id(chat: Chat | int) -> int:
        if isinstance(chat, Chat):
            return chat.id
        return chat
