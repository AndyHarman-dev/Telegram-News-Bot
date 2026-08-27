import json
import random
import string
import requests
from app.pipelines.pipes.chat.news_pipeline import NewsManager
from app.init import init_default_classes
from fastapi import FastAPI
from pydantic import BaseModel, Field


init_default_classes()
FAS_app = FastAPI(
    title='AstroSynth AI'
)


class ApiManager:
    @staticmethod
    async def get_posts(hashtag_name, num_posts=5, language=1, style=1, debug=False):
        if num_posts > 10:
            num_posts = 10
        posts_list, json_result = [], {}
        try:
            news = await NewsManager.gather_posts_for_hashtag(hashtag_name, num_posts, language, style)
            for post_id, title, full_post, image_path in news:
                post_dict = {
                    "id": post_id,
                    "title": title,
                    "content": full_post,
                    "image_path": image_path
                }
                posts_list.append(post_dict)
        except ValueError:
            if not debug:
                raise ValueError('Content execute error!')

            def generate_random_text(length):
                characters = string.ascii_letters + string.digits + string.punctuation + string.whitespace
                random_text = ''.join(random.choice(characters) for _ in range(length))
                return random_text

            def generate_random_url():
                try:
                    _request = requests.request('get', 'https://random.dog/woof.json')
                    _request = json.loads(_request.content)
                    return _request['url']
                except TypeError:
                    return generate_random_text(random.randint(25, 100))

            for i in range(num_posts):
                post_dict = {
                    "id": i,
                    "title": generate_random_text(random.randint(20, 100)),
                    "content": generate_random_text(random.randint(100, 500)),
                    "image_path": generate_random_url()
                }
                posts_list.append(post_dict)
        return posts_list


@FAS_app.get('/', response_model=str)
async def init_message():
    return 'Welcome to the AstroSynth AI Universe!'


class HashtagModel(BaseModel):
    hashtag_name: str = Field(default='#Politics')
    num_post: int = Field(ge=1, default=5)
    language: int = Field(ge=0, default=1)
    style: int = Field(ge=0, default=1)


class NewsModel(BaseModel):
    id: int
    title: str
    content: str
    image_path: str | None


@FAS_app.post('/api/v2.0', response_model=list[NewsModel])
async def get_news(news_request: HashtagModel):
    _resp = await ApiManager.get_posts(news_request.hashtag_name, news_request.num_post,
                                       news_request.language, news_request.style, True)
    return _resp


# enter
# uvicorn app.web.api_server:FAS_app --reload
# in terminal for api testing
# and waiting
# INFO:     Application startup complete.
# message in console
# and follow the link http://127.0.0.1:8000/docs for further testing
