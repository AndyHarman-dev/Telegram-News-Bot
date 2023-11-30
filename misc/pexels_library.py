import requests
from config import config
from misc import log_helper
from typing import Final

TG_LOG_UNSPLASH = log_helper.LogHelper(__name__, "Unsplash library thread")

# Consts of API
CLIENT_ACCESS_KEY: Final = config.CONFIG_DICT['pexels_access_key']
PEXELS_API_URL: Final = "https://api.pexels.com/v1/"


# Interface for using PexelsAPI Library. It uses key from confit.txt under key: unsplash_client_key
class PexelsAPI:
    def __init__(self):
        pass

    @staticmethod
    def search_images(prompt):
        # Gather request
        headers = {
            'Authorization': CLIENT_ACCESS_KEY
        }
        url = PEXELS_API_URL + "search" + "?" + f"query={prompt}"

        response = requests.get(url=url, headers=headers)

        # Process response
        json_response = response.json()
        photos = json_response[0]['photos']
        # Transform the json photos to each image urls
        image_urls = list(map(lambda photo_obj: photo_obj['src']['original'], photos))
        return image_urls

