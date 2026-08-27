# SMM Chat Bot

A Telegram bot that combines an AI news feed with a general-purpose AI chat assistant. It
parses news from RSS feeds, Telegram channels and websites, tags each item with hashtags,
and delivers only the news a given user (or channel) has opted into — alongside regular
LLM chat, model switching, and image generation, all through a fully button-driven Telegram
UI.

> **Status: unfinished prototype / spike.** Most of the surface area described below is
> implemented, but the project never reached a deployed, production state. Expect dead code
> paths, commented-out experiments, missing tests, and rough edges — see
> [Known gaps](#known-gaps-honest-status) before assuming any of this works end to end.

## Core idea

1. **Parse** — a scheduled pipeline pulls posts from RSS feeds, RSS-bridge sources,
   Telegram channels and a handful of scraped websites, dedupes them, and stores them in
   SQLite.
2. **Tag** — each post is rated by an LLM and, if it scores well, tagged with hashtags from
   a fixed taxonomy (categories → hashtags, see `app/database/db_hashtag.py`).
3. **Match preferences to hashtags** — a user's interests are represented as the same
   hashtags. Preferences can be set two ways:
   - Manually, by tapping hashtags in an inline-keyboard category browser.
   - By free-text description ("I like elephants, jazz and blockchain"), which is embedded
     with `sentence-transformers` and matched to the closest hashtags via cosine similarity
     (`app/misc/vectorization/`).
4. **Deliver** — a scheduler periodically finds unseen posts whose hashtags match a chat's
   selected hashtags (plain SQL `JOIN`s against `chats_hashtags` / `posts_hashtags`,
   see `app/pipelines/pipes/chat/news_pipeline.py`) and pushes them to Telegram, each with
   an AI-generated or stock image.
5. **Chat** — outside of news, users can talk to an LLM directly, switch models, and
   generate images on demand — all through the same Telegram state machine.

## Feature surface

- **News pipeline**: RSS / RSS-bridge / Telegram-channel / website parsing, LLM-based
  quality rating, automatic hashtag tagging, per-post translation and per-user "pocket"
  (read/unread) tracking.
- **Preference system**: hashtag categories browsable via inline keyboard, plus a
  natural-language "describe your interests" onboarding flow.
- **Chat**: multi-provider LLM chat completions (OpenAI, Perplexity/Llama, Gemini, Claude)
  behind a common fallback/circuit-breaker requester, with per-chat model selection.
- **Image generation**: DALL·E and Pexels backends behind a shared facade.
- **Telegram UI**: a custom state-machine (`app/bot/states/`) drives menus, settings,
  hashtag pickers, blacklists, tutorials and help — almost entirely via inline buttons.
- **Localization**: UI strings translated into 10 languages (`settings/localization/`).
- **Monetization scaffolding**: tariffs, usage quotas and Telegram Payments handling
  (`app/database/db_tariff.py`, `db_payment.py`) — present in the data model and bot
  handlers, unverified against a real payment provider.

## Known gaps (honest status)

- **No real vector database.** `sentence-transformers` embeddings are computed in memory
  and compared with `sklearn` cosine similarity purely to map free-text preferences onto
  the fixed hashtag list at onboarding time (`app/misc/vectorization/hashtager.py`). There
  is no persisted vector index (no FAISS/Chroma/pgvector/etc.) and actual news delivery
  doesn't use embeddings at all — it's a plain SQL hashtag join.
- **Never deployed.** Running notes in `docs/ServerCommands.txt` assume manual
  `nohup`/`screen`-style process management on a VPS; there is no Dockerfile, CI, or
  process manager config in this repo.
- **No automated tests.** A couple of manual/ad-hoc scripts exist under `app/test/` and
  `app/pipelines/pipes/test_pipeline.py`, but there's no test runner wired up.
- **Multiple half-finished LLM integrations.** OpenAI is the primary, working path;
  Claude, Gemini and Perplexity/Llama integrations exist in `app/llm/` in varying states of
  completeness. Image generation via DALL·E works; some factory methods (transcription,
  speech) are stubbed with `TODO`.
- **RSS-bridge parsing expects a local `rss-bridge` Docker container** to be running
  (see `docs/ServerCommands.txt`); it's disabled by default in `parser_pipeline.py`.

## Architecture

```
app/
├── main.py                    # Production entry point: init DB, schedulers, bot
├── main_watchdog.py           # Dev entry point: restarts main.py on file change
├── init.py                    # Registers LLM / image-generator prototypes
├── bot/
│   ├── config.py              # All settings, read from .env
│   ├── telegram_bot.py        # Bot class, command/handler wiring
│   └── states/                # State machine: menus, settings, hashtags, chat, etc.
├── pipelines/
│   ├── pipeline.py            # Base Pipeline / DynamicPipeline scheduling primitives
│   └── pipes/
│       ├── parser/            # RSS, RSS-bridge, Telegram-channel, website parsing
│       └── chat/news_pipeline.py  # Hashtag matching + news delivery to chats
├── database/                  # SQLite managers (posts, hashtags, chats, tariffs, ...)
├── llm/                       # Chat completion + image generation providers, fallback logic
├── misc/
│   └── vectorization/         # Embedding-based free-text → hashtag matcher
└── web/                       # Small FastAPI surface (experimental, unused by the bot)
```

State flow, hashtag taxonomy and startup env vars are documented in more detail in
[`AGENTS.md`](./AGENTS.md).

## Tech stack

Python 3.11 · [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) v21
· `aiosqlite` · `sentence-transformers` + `scikit-learn` (hashtag matching) · `feedparser` /
`telethon` / `BeautifulSoup` (parsing) · `APScheduler` · `FastAPI` (unused web stub) ·
OpenAI / Perplexity / Gemini / Claude APIs · DALL·E / Pexels (images) · Poetry.

## Running it

```bash
# install dependencies
poetry install

# required in a .env file at the repo root
TELEGRAM_BOT_TOKEN=<from BotFather>
OPENAI_API_KEY=<OpenAI key>
# optional, depending on which providers/features you enable:
# PERPLEXITY_API_KEY, STABILITY_API_KEY, PEXELS_API_KEY, TELEGRAM_API_ID, TELEGRAM_API_HASH

# dev, with auto-reload on changes to app/main.py
poetry run start

# or run directly
python -m app.main
```

`config.py` will `exit(1)` at import time if `TELEGRAM_BOT_TOKEN` or `OPENAI_API_KEY` are
missing. News parsing and news-sending are both **off by default** — enable them with
`ENABLE_PARSER=True` / `ENABLE_NEWS_SENDING=True` in `.env` once channels are configured
under `settings/parser/`.

## Repo layout outside `app/`

- `settings/` — runtime config: parser source lists, admin user list, localization JSON.
- `docs/` — operational notes captured during development (server commands, BotFather
  setup, DB schema sketch) — historical, not guaranteed current.
- `content/` — static assets (fonts, gifs) used by bot messages.
