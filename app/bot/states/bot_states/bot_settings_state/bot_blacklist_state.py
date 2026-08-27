from app.bot.states.state import State
from app.bot.states.bot_states.bot_settings_state.bot_hashtags_state import BotHashtagsState


class BotBlacklistState(BotHashtagsState):
    # Blacklist state that manages blacklist of hashtags
    LINKING_TABLE_NAME = "chats_blacklist_hashtags"
    pass
