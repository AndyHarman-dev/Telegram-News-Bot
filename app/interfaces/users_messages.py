from abc import ABC, abstractmethod
from telegram import Chat, Message


class IUsersStates(ABC):

    @abstractmethod
    def set_last_message_in_chat(cls, chat: Chat, message: Message, is_text: bool):
        pass

    @abstractmethod
    def get_last_message_in_chat(cls, chat: Chat):
        pass

    @abstractmethod
    def message_available_for_changes(cls, chat: Chat):
        pass

    @abstractmethod
    def menu_available_for_changes(cls, chat: Chat):
        pass

    @abstractmethod
    async def add_last_message_in_chat(cls, chat: Chat, text: str, reply_markup, parse_mode):
        pass

    @abstractmethod
    async def reply_on_last_message_in_chat(cls, chat: Chat, text: str, reply_markup, parse_mode):
        pass

    @abstractmethod
    async def edit_last_message_in_chat(cls, chat: Chat, text: str, reply_markup, parse_mode):
        pass

    @abstractmethod
    async def edit_last_menu_in_chat(cls, chat: Chat, text: str, reply_markup, parse_mode):
        pass

    @abstractmethod
    async def del_last_message_in_chat(cls, chat: Chat):
        pass

    @abstractmethod
    async def del_last_menu_in_chat(cls, chat: Chat):
        pass
