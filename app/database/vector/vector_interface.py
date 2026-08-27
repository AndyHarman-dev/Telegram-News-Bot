from abc import ABC, abstractmethod


class IVectorInterface(ABC):

    @abstractmethod
    def add_post(self, post_id: int, content: str):
        pass

    @abstractmethod
    def delete_post(self, post_id: int):
        pass

    @abstractmethod
    def add_user_preferences(self, user_id: int, content: str):
        pass

    @abstractmethod
    def delete_user_preferences(self, user_id: int):
        pass

    @abstractmethod
    def get_user_preferences(self, user_id: int):
        pass

    @abstractmethod
    def get_similar_posts(self, user_prf_msg: str, count: int) -> int:
        pass