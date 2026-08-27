from app.interfaces.ret_val import IRetValue


class ChatCompletionValue(IRetValue):

    def __init__(self, response_string: str):
        self.response_message = response_string

    async def is_valid(self) -> bool:
        return len(self.response_message) > 0

    def __await__(self):
        return self.response_message

    def __str__(self):
        return self.response_message
