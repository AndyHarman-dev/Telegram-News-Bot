import logging
import os

from dotenv import load_dotenv

#telegram API constants
from app.bot.constants.telegram_api_constants import telegram_api_config

# Read .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Check if the required environment variables are set
required_values = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY']
missing_values = [value for value in required_values if os.environ.get(value) is None]
if len(missing_values) > 0:
    logging.error(f'The following environment values are missing in your .env: {", ".join(missing_values)}')
    exit(1)

# Setup configurations
model = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
openai_config = {
    'api_key': os.environ['OPENAI_API_KEY'],
    'show_usage': os.environ.get('SHOW_USAGE', 'false').lower() == 'true',
    'stream': os.environ.get('STREAM', 'true').lower() == 'true',
    'proxy': os.environ.get('PROXY', None),
    'max_history_size': int(os.environ.get('MAX_HISTORY_SIZE', 15)),
    'max_conversation_age_minutes': int(os.environ.get('MAX_CONVERSATION_AGE_MINUTES', 180)),
    'assistant_prompt': os.environ.get('ASSISTANT_PROMPT', 'You are a helpful assistant.'),
    #'max_tokens': int(os.environ.get('MAX_TOKENS', max_tokens_default)),
    'n_choices': int(os.environ.get('N_CHOICES', 1)),
    'temperature': float(os.environ.get('TEMPERATURE', 1.0)),
    'image_model': os.environ.get('IMAGE_MODEL', 'dall-e-2'),
    'image_quality': os.environ.get('IMAGE_QUALITY', 'standard'),
    'image_style': os.environ.get('IMAGE_STYLE', 'vivid'),
    'image_size': os.environ.get('IMAGE_SIZE', '512x512'),
    'model': model,
    # 'enable_functions': os.environ.get('ENABLE_FUNCTIONS', str(functions_available)).lower() == 'true',
    'functions_max_consecutive_calls': int(os.environ.get('FUNCTIONS_MAX_CONSECUTIVE_CALLS', 10)),
    'presence_penalty': float(os.environ.get('PRESENCE_PENALTY', 0.0)),
    'frequency_penalty': float(os.environ.get('FREQUENCY_PENALTY', 0.0)),
    'bot_language': os.environ.get('BOT_LANGUAGE', 'en'),
    'show_plugins_used': os.environ.get('SHOW_PLUGINS_USED', 'false').lower() == 'true',
    'whisper_prompt': os.environ.get('WHISPER_PROMPT', ''),
    'tts_model': os.environ.get('TTS_MODEL', 'tts-1'),
    'tts_voice': os.environ.get('TTS_VOICE', 'alloy'),
    'llm_threads_limit': os.environ.get('LLM_THREADS_LIMIT', 6),
}

llm_services_config = {
    'max_tokens': int(os.environ.get('MAX_TOKENS', 3000))
}

telegram_config = {
    'token': os.environ['TELEGRAM_BOT_TOKEN'],
    'admin_user_ids': os.environ.get('ADMIN_USER_IDS', '-'),
    'allowed_user_ids': os.environ.get('ALLOWED_TELEGRAM_USER_IDS', '*'),
    'enable_quoting': os.environ.get('ENABLE_QUOTING', 'true').lower() == 'true',
    'enable_image_generation': os.environ.get('ENABLE_IMAGE_GENERATION', 'true').lower() == 'true',
    'enable_transcription': os.environ.get('ENABLE_TRANSCRIPTION', 'true').lower() == 'true',
    'enable_tts_generation': os.environ.get('ENABLE_TTS_GENERATION', 'true').lower() == 'true',
    'budget_period': os.environ.get('BUDGET_PERIOD', 'monthly').lower(),
    'user_budgets': os.environ.get('USER_BUDGETS', os.environ.get('MONTHLY_USER_BUDGETS', '*')),
    'guest_budget': float(os.environ.get('GUEST_BUDGET', os.environ.get('MONTHLY_GUEST_BUDGET', '100.0'))),
    'stream': os.environ.get('STREAM', 'false').lower() == 'true',
    'proxy': os.environ.get('PROXY', None),
    'voice_reply_transcript': os.environ.get('VOICE_REPLY_WITH_TRANSCRIPT_ONLY', 'false').lower() == 'true',
    'voice_reply_prompts': os.environ.get('VOICE_REPLY_PROMPTS', '').split(';'),
    'ignore_group_transcriptions': os.environ.get('IGNORE_GROUP_TRANSCRIPTIONS', 'true').lower() == 'true',
    'group_trigger_keyword': os.environ.get('GROUP_TRIGGER_KEYWORD', ''),
    'token_price': float(os.environ.get('TOKEN_PRICE', 0.002)),
    'image_prices': [float(i) for i in os.environ.get('IMAGE_PRICES', "0.016,0.018,0.02").split(",")],
    'image_receive_mode': os.environ.get('IMAGE_FORMAT', "photo"),
    'tts_model': os.environ.get('TTS_MODEL', 'tts-1'),
    'tts_prices': [float(i) for i in os.environ.get('TTS_PRICES', "0.015,0.030").split(",")],
    'transcription_price': float(os.environ.get('TRANSCRIPTION_PRICE', 0.006)),
    'bot_language': os.environ.get('BOT_LANGUAGE', 'en'),
    'bot_api': os.environ.get('TELEGRAM_API_ID'),
    'bot_hash': os.environ.get('TELEGRAM_API_HASH'),
    'bot_name': os.environ.get('BOT_NAME', 'NewsGPT'),
}

plugin_config = {
    'plugins': os.environ.get('PLUGINS', '').split(',')
}

# Load startup config
startup_config = {
    'enable_parser': eval(os.environ.get('ENABLE_PARSER', 'False')),
    'parsing_interval': eval(os.environ.get('PARSING_INTERVAL_M', '60')),
    'enable_news_sending': eval(os.environ.get('ENABLE_NEWS_SENDING', 'False')),
    'news_sending_interval': eval(os.environ.get('NEWS_SENDING_INTERVAL_M', '60')),
    'enable_database_cleanup': eval(os.environ.get('ENABLE_DATABASE_CLEANUP', 'False')),
    'debug_mode': eval(os.environ.get('DEBUG_MODE', 'False')),
}


# Load startup config
util_config = {
    'debug_mode': eval(os.environ.get('DEBUG_MODE', 'False')),
}

#API SERVICES KEYS
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY', "")
STABILITY_API_KEY = os.environ.get('STABILITY_API_KEY', "")
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY', "")


class LLMModels:
    GPT_3_5_TURBO = "gpt-3.5-turbo-1106"
    GPT_4 = "gpt-4"
    GPT_4_1106_PREVIEW = "gpt-4-1106-preview"
    MISTRAL_7B_INSTR = "mistral-7b-instruct"
    MISTRAL_8x7B_INSTR = "mistral-8x7b-instruct"
    LLAMA_3_SONAR_SMALL_CHAT = "llama-3.1-sonar-small-128k-online"
    LLAMA_3_SONAR_LARGE_CHAT = "llama-3.1-sonar-large-128k-online"
    LLAMA_3_SONAR_HUGE_CHAT = "llama-3.1-sonar-huge-128k-online"
    LLAMA_3_8B_INSTRUCT = "llama-3.1-8b-instruct"
    LLAMA_3_70B_INSTRUCT = "llama-3.1-70b-instruct"


class ImageModels:
    PEXELS = "pexels"
    DALL_E_3 = "dall-e-3"


AVAILABLE_MODELS = [
    LLMModels.GPT_4,
    LLMModels.GPT_4_1106_PREVIEW,
    LLMModels.GPT_3_5_TURBO,
    LLMModels.MISTRAL_7B_INSTR,
    LLMModels.MISTRAL_8x7B_INSTR,
    LLMModels.LLAMA_3_SONAR_SMALL_CHAT,
    LLMModels.LLAMA_3_SONAR_LARGE_CHAT,
    LLMModels.LLAMA_3_SONAR_HUGE_CHAT,
    LLMModels.LLAMA_3_70B_INSTRUCT
]


ACTIVE_MODELS = {
    "fast": LLMModels.LLAMA_3_SONAR_SMALL_CHAT,
    "common": LLMModels.LLAMA_3_SONAR_LARGE_CHAT,
    "smart": LLMModels.LLAMA_3_SONAR_HUGE_CHAT
}

SERVER_REGION = os.environ.get('SERVER_REGION', "Europe/London")
