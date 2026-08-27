import logging
import os
from app.misc.google_translator import GoogleTranslator
import json
import asyncio
import aiofiles
import aiohttp

from app.misc.localization.lang_loc import PATH_TO_LOCALE_FILES
from app.database.db_translation import TranslationManager
from app.database.db_hashtag import HashtagManager
from app.misc.paths import Paths
from app.misc.log_helper import LogHelper

CPU_CORES = os.cpu_count()
LOG_LOCALE_FILES = LogHelper(__name__, "Locale Files Thread")


async def translate_text(session, text, dest_language):
    return await GoogleTranslator.translate_text_async(text=text, target_language=dest_language, custom_session=session)


async def translate_json_content(session, data, dest_language):
    """
    Asynchronously translates the content of a JSON data structure to the specified destination language.

    Args:
        session: The aiohttp ClientSession used to make the translation requests.
        data: The JSON data to be translated.
        dest_language: The destination language to translate the content to.

    Returns:
        The translated JSON content in the specified destination language.
    """
    if isinstance(data, dict):
        tasks = {k: translate_json_content(session, v, dest_language) for k, v in data.items()}
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))
    elif isinstance(data, list):
        tasks = [translate_json_content(session, item, dest_language) for item in data]
        return await asyncio.gather(*tasks)
    elif isinstance(data, str):
        return await translate_text(session, data, dest_language)
    return data


async def translate_to_language(session, content, lang_code):
    translated_content = await translate_json_content(session, content, lang_code)
    output_file = f'{PATH_TO_LOCALE_FILES}{lang_code}.json'
    async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(translated_content, ensure_ascii=False, indent=4))
    LOG_LOCALE_FILES.log(logging.INFO, f"Translated file saved as: {output_file}")


async def translate_locales():
    input_file = f"{PATH_TO_LOCALE_FILES}en.json"
    languages_to_translate = TranslationManager.get_languages_codes()  # Assuming this returns a list of language codes

    # Fetch categories and hashtags
    raw_categories = HashtagManager.get_hashtag_categories_list()
    transformed_categories = {text.lower(): [value, {}] for text, value in zip(raw_categories, raw_categories.copy())}

    hashtag_categories = {}
    for category in raw_categories:
        hashtags = HashtagManager.get_hashtags_for_categories(category)
        transformed_hashtags = {key.lower(): value for key, value in zip(hashtags, hashtags.copy())}

        transformed_categories[category.lower()][1] = transformed_hashtags

    async with aiofiles.open(input_file, 'r+', encoding='utf-8') as f:
        content = json.loads(await f.read())

        # Add categories and hashtags to the content
        content['hashtag_categories'] = transformed_categories

        # Write the modified content back to the input file
        await f.seek(0)
        await f.write(json.dumps(content, ensure_ascii=False, indent=4))
        await f.truncate()

    async with aiohttp.ClientSession() as session:
        tasks = [translate_to_language(session, content.copy(), lang_code) for lang_code in languages_to_translate]
        await asyncio.gather(*tasks)


async def compare_states(data1, data2):
    new_entries = {}

    for state, state_data in data1['states'].items():
        if state not in data2['states']:
            new_entries[state] = state_data
        else:
            new_state_data = {}
            for key, value in state_data.items():
                if key not in data2['states'][state] or data2['states'][state][key] != value:
                    new_state_data[key] = value
            if new_state_data:
                new_entries[state] = new_state_data

    return new_entries


async def compare_misc(data1, data2):
    new_entries = {}

    for key, value in data1['misc'].items():
        if key not in data2['misc']:
            new_entries[key] = value
        else:
            new_misc_data = {}
            for subkey, subvalue in value.items():
                if subkey not in data2['misc'][key] or data2['misc'][key][subkey] != subvalue:
                    new_misc_data[subkey] = subvalue
            if new_misc_data:
                new_entries[key] = new_misc_data

    return new_entries


async def compare_styles(data1, data2):
    new_entries = {}

    for style, value in data1['styles'].items():
        if style not in data2['styles'] or data2['styles'][style] != value:
            new_entries[style] = value

    return new_entries


async def compare_locales(file1, file2):
    async with aiofiles.open(file1, 'r', encoding='utf-8') as f1, aiofiles.open(file2, 'r', encoding='utf-8') as f2:
        data1 = json.loads(await f1.read())
        data2 = json.loads(await f2.read())

    new_entries = {}

    for category, subcategories in data1['hashtag_categories'].items():
        if category not in data2['hashtag_categories']:
            new_entries[category] = subcategories
        else:
            new_hashtags = {}
            for hashtag, value in subcategories[1].items():
                if hashtag not in data2['hashtag_categories'][category][1] or data2['hashtag_categories'][category][1][hashtag] != value:
                    new_hashtags[hashtag] = value
            if new_hashtags:
                if 'hashtag_categories' not in new_entries:
                    new_entries['hashtag_categories'] = {}

                new_entries['hashtag_categories'][category] = [subcategories[0], new_hashtags]

    new_states = await compare_states(data1, data2)
    if new_states:
        new_entries['states'] = new_states

    new_misc = await compare_misc(data1, data2)
    if new_misc:
        new_entries['misc'] = new_misc

    new_styles = await compare_styles(data1, data2)
    if new_styles:
        new_entries['styles'] = new_styles

    return new_entries


async def merge_dict(main_dict, new_dict):
    for key, value in new_dict.items():
        if isinstance(value, dict):
            if key not in main_dict:
                main_dict[key] = {}
            await merge_dict(main_dict[key], value)
        else:
            main_dict[key] = value


async def merge_locales(main_locale_file, new_entries):
    async with aiofiles.open(main_locale_file, 'r', encoding='utf-8') as f:
        main_locale = json.loads(await f.read())

    for section, entries in new_entries.items():
        if section == 'hashtag_categories':
            for category, subcategories in entries.items():
                if category not in main_locale['hashtag_categories']:
                    main_locale['hashtag_categories'][category] = subcategories
                else:
                    main_locale['hashtag_categories'][category][1].update(subcategories[1])
        elif section in ['states', 'misc', 'styles']:
            await merge_dict(main_locale[section], entries)

    async with aiofiles.open(main_locale_file, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(main_locale, ensure_ascii=False, indent=4))


async def merge_translations():
    input_file = f"{PATH_TO_LOCALE_FILES}en.json"
    languages_to_translate = TranslationManager.get_languages_codes()  # Assuming this returns a list of language codes

    async with aiofiles.open(input_file, 'r') as f:
        main_locale = json.loads(await f.read())

    for code in languages_to_translate:
        if code == 'en': continue

        file_path = f"{PATH_TO_LOCALE_FILES}{code}.json"

        LOG_LOCALE_FILES.log(logging.INFO, f"Checking {file_path}")
        if Paths.exists(file_path):
            LOG_LOCALE_FILES.log(logging.INFO, f"Path {file_path} exists, comparing...")
            new_entries = await compare_locales(input_file, file_path)

            if len(new_entries) == 0:
                LOG_LOCALE_FILES.log(logging.INFO, f"No new entries found")
                continue

            LOG_LOCALE_FILES.log(logging.INFO, f"Found {len(new_entries)} new entries")

            async with aiohttp.ClientSession() as session:
                translated_entries = await translate_json_content(session, new_entries.copy(), code)

            LOG_LOCALE_FILES.log(logging.INFO, f"Merging {len(translated_entries)} new entries")
            await merge_locales(file_path, translated_entries)
        else:
            LOG_LOCALE_FILES.log(logging.INFO, f"Path {file_path} does not exist, creating...")
            async with aiohttp.ClientSession() as session:
                await translate_to_language(session, main_locale.copy(), code)


if __name__ == "__main__":
    asyncio.run(merge_translations())
    # test()
