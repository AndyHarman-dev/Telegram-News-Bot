# SMM_Chat_Bot — Agent Instructions

## Project Overview
Telegram bot with AI functions (chat, image generation, news parsing, subscriptions). Built on `python-telegram-bot` v21, uses state machine for conversation flow.

## Key Commands
```bash
# Install dependencies (uses Poetry)
poetry install

# Run with auto-reload on file changes (dev)
poetry run start

# Run directly (production)
python -m app.main

# Or background production (from docs/ServerCommands.txt)
sudo nohup python3 app/main.py > output.log 2>&1 &
```

## Environment Setup
Required in `.env`:
```
TELEGRAM_BOT_TOKEN=<from BotFather>
OPENAI_API_KEY=<OpenAI key>
# Optional: PERPLEXITY_API_KEY, STABILITY_API_KEY, PEXELS_API_KEY
```
Config loaded in `app/bot/config.py` — reads all settings from env vars with defaults.

## Entry Points
- **Dev**: `app/main_watchdog.py:main` — watches `app/main.py` for changes, restarts subprocess
- **Prod**: `app/main.py:main` — initializes DB, registers LLM/image prototypes, starts scheduler + Telegram bot

## Architecture Highlights
- **State machine** (`app/bot/states/bot_state_machine.py`) drives all conversation flows
- **Pipelines** (`app/pipelines/`) for parsing (RSS, Telegram channels, websites) and news delivery
- **Database**: SQLite via `aiosqlite` — init in `app/database/db_init.py:create_database()`
- **LLM registry** (`app/misc/registry_objects/chat_completions_registry.py`) — multiple providers (OpenAI, Perplexity, local)
- **Image generation** facade (`app/llm/image_generator/image_generator_facade.py`) — DALL-E, Pexels
- **Localization**: JSON files in `settings/localization/` (10 languages)

## Testing
No formal test runner configured. Two test files exist:
- `app/pipelines/pipes/test_pipeline.py`
- `app/misc/unittest/unit_test_telegram.py` (manual mock test)

Run manually: `python -m app.pipelines.pipes.test_pipeline`

## Linting / Type Checking
Not configured. Add `ruff`, `mypy`, or `pyright` to `pyproject.toml` if needed.

## Common Gotchas
- `config.py` calls `exit(1)` if required env vars missing — handle in scripts
- `eval()` used for boolean env vars (`ENABLE_PARSER`, `DEBUG_MODE`, etc.) — only `True`/`False` strings work
- Watchdog only monitors `app/main.py` (not recursive) — changes to other files won't trigger restart
- Database path resolved via `app/misc/paths.py:Paths.get_saved_dir()`
- Admin user IDs from `ADMIN_USER_IDS` env (comma-separated)

## Directory Structure (key)
```
app/
├── main.py                 # Production entry
├── main_watchdog.py        # Dev entry (auto-reload)
├── init.py                 # Registers LLM/image prototypes
├── bot/
│   ├── config.py           # All settings from .env
│   ├── telegram_bot.py     # Bot class, handlers, state machine setup
│   └── states/             # Conversation states (state machine)
├── pipelines/pipes/        # Parsing, news, DB utilities
├── database/               # SQLite models & managers
├── llm/                    # Chat completion, image generation
└── misc/                   # Logging, scheduler, registry, admin, localization
```

## Bot Commands (from BotFather)
```
/start  - start bot
/menu   - main menu
/image  - generate image
/news   - get news
```