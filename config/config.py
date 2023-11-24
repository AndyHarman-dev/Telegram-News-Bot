from typing import Final
import os

# function for extracting a token from text file
def get_token(filename: str) -> str:
    with open(filename, "r") as file:
        return file.read()



# global token const
TOKEN : Final = get_token('token.txt')
DEFAULT_LOGGING_PATH = "/Users/wiam/Develop/python/ai_social_media_manager/saved/logs"