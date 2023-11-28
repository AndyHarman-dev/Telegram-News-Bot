import requests
from config import config
from misc import log_helper
from typing import Final

TG_LOG_UNSPLASH = log_helper.LogHelper(__name__, "Unsplash library thread")

# Consts of API
CLIENT_ACCESS_KEY: Final = config.CONFIG_DICT['pexels_access_key']
PEXELS_API_URL: Final = "https://api.pexels.com/v1/"


# Interface for using UNSPLASH Library. It uses key from confit.txt under key: unsplash_client_key
class PexelsAPI:
    def __init__(self):
        pass

    @staticmethod
    def test():

        headers = {
            'Authorization': CLIENT_ACCESS_KEY
        }
        url = PEXELS_API_URL + "search" + "?" + "query=nature"
        response = requests.get(url=url, headers=headers)
        return response
