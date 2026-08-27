import logging
import os
import asyncio

from dotenv import load_dotenv
from app.misc.log_helper import LogHelper

LOG_ADMIN_MANAGER = LogHelper(__name__, "Management Manager Thread")


class ManagementManager:
    _instance = None
    _managers_lock = asyncio.Lock()
    _managers: list[str] = []
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            load_dotenv()
            managers_ids = os.getenv('MANAGER_IDS')
            managers = managers_ids.split(',')
            if managers:
                self._managers.extend(managers)
            self._initialized = True

    @classmethod
    async def add_manager(cls, manager: str) -> None:
        async with cls._managers_lock:
            if manager not in cls._managers:
                cls._managers.append(manager)

    @classmethod
    async def remove_manager(cls, manager: str) -> None:
        async with cls._managers_lock:
            if manager in cls._managers:
                cls._managers.remove(manager)

    @classmethod
    async def get_managers(cls) -> list[str]:
        if not cls._managers:
            cls()
        async with cls._managers_lock:
            return cls._managers.copy()

    @classmethod
    async def is_manager(cls, user_id: str) -> bool:
        async with cls._managers_lock:
            return user_id in cls._managers

    @classmethod
    async def send_admin_message(cls, message):
        try:
            from app.bot.states.users_states import UsersStates
            managers = await cls.get_managers()
            for manager_id in managers:
                await UsersStates.add_last_message_in_chat(chat=int(manager_id), text=message)
        except Exception as e:
            LOG_ADMIN_MANAGER.log(logging.ERROR,
                                  f"While retrieving the list of managers an error was received: {e}")

