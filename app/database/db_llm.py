from app.bot.config import LLMModels
from app.database.db_hashtag import main_categories, HashtagManager
import asyncio

from app.database.db_translation import TranslationManager
from app.factories.ai_factories import AIServiceFacade, AIFastServiceFactory, AIFreeServiceFactory
from app.llm.fallback_requester import AIFallbackRequester
from app.misc.registry_objects.chat_completions_registry import register_llm_chat_completion_requests

import logging
from app.misc.log_helper import LogHelper

LOG_LLMDB = LogHelper(__name__, "LLMDB")


class DatabaseLlmManager:

    @staticmethod
    async def run_tasks_in_batches(tasks, batch_size=5):
        total_tasks = len(tasks)
        total_batches = (total_tasks + batch_size - 1) // batch_size

        for i in range(0, total_tasks, batch_size):
            batch = tasks[i:i + batch_size]
            await asyncio.gather(*batch)

            # Печатаем прогресс после завершения каждого пакета задач
            batch_end = min(i + batch_size, total_tasks)
            LOG_LLMDB.log(logging.INFO, f"Завершено {batch_end}/{total_tasks} задач (Пакет {i // batch_size + 1} из {total_batches})")

    @staticmethod
    async def llm_summarize_text(content: str) -> str:

        fr = await AIServiceFacade.create_chat_completion(factory_type=AIFastServiceFactory,
                                                          system="Summarize text. Answer only with the summary.",
                                                          max_tokens=100)

        return await fr.prompt(content)

    @staticmethod
    async def llm_rate_post(content: str, attempt=1) -> int:
        try:

            fr = await AIServiceFacade.create_chat_completion(factory_type=AIFastServiceFactory,
                                                              system="Rate posts importance from 1 to 5. Answer with only a single natural number.",
                                                              max_tokens=10)

            response = await fr.prompt(content)

            # Try to convert response to integer
            try:
                rating = int(response)
            except ValueError:
                rating = 1  # Default value if conversion fails

            except Exception as e:
                LOG_LLMDB.log(logging.ERROR, f"Error in llm_rate_post: {e}")

            # Ensure rating is within 1 to 5
            return max(1, min(rating, 5))



        except Exception as e:
            LOG_LLMDB.log(logging.ERROR, f"Error in llm_rate_post: {e}")

            # Retry the request if it's the first attempt
            if attempt == 1:
                LOG_LLMDB.log(logging.INFO, "Retrying get rate again...")
                return await DatabaseLlmManager.llm_rate_post(content, attempt + 1)
            else:
                # Return default value if the retry attempt also fails
                return 1

    @staticmethod
    async def process_text_with_hashtags(post_content, entity_id, entity_table):

        # Step 1: Send initial request to the language model with post content and category list
        response = ""

        try:
            system = str("Based on the post content, select relevant categories from the following list and "
                               "respond ONLY with the selected categories, separated by commas:"
                               + ', '.join(main_categories))
            fr = await AIServiceFacade.create_chat_completion(factory_type=AIFastServiceFactory,
                                                              system=system,
                                                              max_tokens=100,
                                                              from_parser=True)
            response = await fr.prompt(post_content)

        except Exception as e:
            LOG_LLMDB.log(logging.ERROR, f"Error in process_text_with_hashtags: {e}")
            return 1
        '''
        categories_response, *_ = await llm_fast.send_request(post_content, common_args={
            "messages": [
                {"role": "system",
                 "content": "Based on the post content, select relevant categories from the following list and respond with ONLY the selected categories, separated by commas: " + ', '.join(
                     main_categories)}
            ],
            "max_tokens": 100
        })
        '''
        # Extract selected categories from the response
        selected_categories = response.strip().split(', ')

        # Step 2: Get hashtags for selected categories
        hashtags = []
        for category in selected_categories:
            hashtags.extend(HashtagManager.get_hashtags_for_categories(category))

        # request hashtags from list of hashtags
        try:
            system = str("Based on the post content and available hashtags, please provide relevant hashtags. "
                               "Respond with ONLY the selected hashtags, separated by commas:"
                               + ', '.join(hashtags))

            fr = await AIServiceFacade.create_chat_completion(factory_type=AIFastServiceFactory,
                                                              system=system,
                                                              max_tokens=100,
                                                              from_parser=True)
            response = await fr.prompt(post_content)

        except Exception as e:
            LOG_LLMDB.log(logging.ERROR, f"Error in process_text_with_hashtags: {e}")
            return 1


        # Extract selected hashtags from the response
        selected_hashtags = HashtagManager.extract_hashtags(response)

        # Step 4: Check for hashtag existence in the database and add to the post
        for hashtag_name in selected_hashtags:
            hashtag_id = HashtagManager.get_hashtag_id(hashtag_name)
            if hashtag_id is not None:
                # Add hashtag to the entity
                HashtagManager.add_hashtag_to_entity(entity_id, hashtag_id, entity_table)
            else:
                LOG_LLMDB.log(logging.WARNING, f"Hashtag {hashtag_name} not found in the database.")

    @staticmethod
    async def process_text_with_hashtags_wrapper(post_content, entity_id, entity_table, index, total):
        await DatabaseLlmManager.process_text_with_hashtags(post_content, entity_id, entity_table)

    @staticmethod
    async def llm_translate_text(text, language_id, style_id, briefmode=False, from_news_manager=False):
        # Get the language and style from the database

        if not text:
            LOG_LLMDB.log(logging.ERROR, "llm_translate_text no input text")
            return None

        language = TranslationManager.get_language_name(language_id)
        style = TranslationManager.get_style_name_by_id(style_id)
        style_description = TranslationManager.get_style_description_by_id(style_id)

        # Подготовка промпта для языковой модели
        if briefmode:
            # Если briefmode активен, генерируем очень краткий заголовок
            system_prompt = f"Translate a very brief headline in {language} language for the following text, summarizing it in a {style} style: {style_description}, write only translation, do not add any additional text"
        else:
            # Если briefmode не активен, переводим текст и создаем заголовок
            system_prompt = f"Translate the following text into {language} and create a headline in a {style} style: {style_description}, write only translation, do not add any additional text"

        fr = await AIServiceFacade.create_chat_completion(factory_type=AIFreeServiceFactory,
                                                          models=await AIFreeServiceFactory.get_models(),
                                                          system=system_prompt,
                                                          from_news_manager=from_news_manager
                                                          )
                                                          #models=[LLMModels.LLAMA_3_70B_INSTRUCT, LLMModels.GPT_3_5_TURBO])
        return await fr.prompt(text)


async def test():
    register_llm_chat_completion_requests()

    content = """Michael asks: How are the billions of pounds of tax money being pumped into Ukraine by the UK and
    other governments being spent - are detailed accounts published or is it just sent on trust?"""

    print(await DatabaseLlmManager.llm_rate_post(content))


if __name__ == '__main__':
    asyncio.run(test())
    # Example usage

    # post = """Michael asks: How are the billions of pounds of tax money being pumped into Ukraine by the UK and
    # other governments being spent - are detailed accounts published or is it just sent on trust?
    #     Money sent to Ukraine largely falls under three categories: military, humanitarian and financial.
    #     Some of it is, for example, used to help Kyiv pay for public services including teachers’ and doctors’ wages.
    #     """
    #
    # asyncio.run(DatabaseLlmManager.process_text_with_hashtags(post, 3, "posts_hashtags"))
