import asyncio

import g4f
from config import config
from misc.log_helper import LogHelper, logging
from misc.pexels_library import PexelsAPI


TG_LOG_PG = LogHelper(__name__, "Post generator thread")

TOPIC_RELEVANCE_PROMPT = config.CONFIG_DICT['topic_relevance']


# Generates post using AI chat technology and image generation
class PostGenerator:
    def __init__(self, topic, avoid_topics, images_count):
        self.topic = topic
        self.avoid_topics = avoid_topics
        self.images_count = images_count
        TG_LOG_PG.log(logging.INFO, "Post generator initialized")

    # Generators
    async def __generate_prompt(self):
        TG_LOG_PG.log(logging.INFO, "Generating prompt...")
        prompt = f"Write a post about {self.topic}. Avoid topics related to {', '.join(self.avoid_topics)}."
        TG_LOG_PG.log(logging.INFO, f"Prompt is {prompt}")
        return prompt

    # Generates a text for a post and returns image urls
    async def generate_post(self, images_count) -> (str, []):

        # Check if topic is relevant
        if await is_topic_relevant(self.topic):
            prompt = await self.__generate_prompt()
            # Use ChatGPT to generate the post based on the prompt
            try:
                # Make async response
                task = asyncio.create_task(g4f.ChatCompletion.create_async(
                    model=g4f.models.gpt_4,
                    messages=[
                        {"role": "system", "content": "Be precise and accurate. "},
                        {"role": "user", "content": prompt}
                    ]
                ))

                # Request image urls and then await the task to complete
                image_urls = PexelsAPI.search_images(self.topic)
                return await task, image_urls

            except Exception as e:
                err_msg = f"Exception was raised while generating post: {e}"
                TG_LOG_PG.log(logging.ERROR, err_msg)
                return err_msg


# Checks if the topic provided is relevant and indeed a topic for a post

async def is_topic_relevant(topic: str) -> bool:
    try:
        # Use GPT-3.5 to check if the topic is relevant
        prompt = f"Topic: {topic}\n {TOPIC_RELEVANCE_PROMPT}. Answer only with one word : yes or no"
        TG_LOG_PG.log(logging.INFO, f"Checking topic relevance, prompt: {prompt}...")
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_35_turbo_16k,  # This model seems to answer more accurately
            messages=[
                {"role": "system", "content": prompt},
            ]
        )

        # Assuming that we strictly defined "yes" in the prompt
        if 'yes' in response.lower():
            TG_LOG_PG.log(logging.INFO, f"Topic {topic} is relevant.")
            return True
        else:
            TG_LOG_PG.log(logging.INFO, f"Topic {topic} is not relevant.")
            return False

    except Exception as e:
        TG_LOG_PG.log(logging.ERROR, f"Error while checking topic relevance: {e}")
        return False
