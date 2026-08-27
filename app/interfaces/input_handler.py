from abc import ABC, abstractmethod

from telegram import Update
from telegram.ext import ContextTypes


class IInputHandler(ABC):
    @abstractmethod
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        pass

    @abstractmethod
    async def handle_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass
