from abc import ABC, abstractmethod


class IState(ABC):
    @abstractmethod
    async def handle_enter_state(self, update, context):
        pass

    @abstractmethod
    async def handle_on_user_message(self, update, context):
        pass

    @abstractmethod
    async def handle_callback_query(self, update, context):
        pass


class IStateContext(ABC):
    @abstractmethod
    def change_state(self,update, context, new_state: IState):
        pass
