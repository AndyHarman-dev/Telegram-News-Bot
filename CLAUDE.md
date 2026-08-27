# SMM_Chat_Bot — Project Notes for Claude Code

See [`AGENTS.md`](./AGENTS.md) for the canonical command/architecture reference (kept in
sync with this file since some tooling reads one or the other). This file adds Claude-Code-
specific framing on top of that.

## What this repo actually is

An unfinished spike: a Telegram bot that parses news, tags it with hashtags, and delivers
it based on per-chat hashtag preferences, plus a general AI chat/image-generation surface
with a full inline-keyboard UI. It was never deployed to production. Treat anything not
directly exercised by `app/main.py`'s startup path with suspicion — there is a lot of
commented-out code, `# TODO` stubs, and abandoned alternate implementations (e.g.
`app/llm/gemini_api.py`, `app/llm/Claude_API.py`) left mid-integration. See the README's
["Known gaps"](./README.md#known-gaps-honest-status) section before assuming a feature is
wired up end to end.

**Important**: the "vector database" implied by `sentence-transformers` /
`scikit-learn` in `pyproject.toml` is not a real persisted index. It's
`app/misc/vectorization/hashtager.py` computing embeddings in memory once at process start
and doing a one-off cosine-similarity match to turn a user's free-text preferences into
hashtags. Actual news delivery (`app/pipelines/pipes/chat/news_pipeline.py`) is a plain SQL
join on hashtag IDs — no embeddings involved at serve time. Don't assume a vector store
exists anywhere in this codebase.

## Commands

```bash
poetry install              # install deps
poetry run start             # dev, auto-reloads on changes to app/main.py only
python -m app.main            # run directly / production
```

No linter, formatter, or test runner is configured. If asked to add one, ask which
tool the user wants rather than guessing (ruff vs. flake8, pytest vs. unittest, etc.) — the
existing ad hoc scripts under `app/test/` are manual/exploratory, not a suite to extend.

## Required env vars (`.env`)

`TELEGRAM_BOT_TOKEN` and `OPENAI_API_KEY` are required — `app/bot/config.py` calls
`exit(1)` at import time if either is missing, which will crash any script that imports
`app.bot.config` (directly or transitively) if `.env` isn't set up. Optional keys:
`PERPLEXITY_API_KEY`, `STABILITY_API_KEY`, `PEXELS_API_KEY`, `TELEGRAM_API_ID`,
`TELEGRAM_API_HASH`. Boolean-ish startup flags (`ENABLE_PARSER`, `DEBUG_MODE`, etc.) are
parsed with `eval()` — only the literal strings `True`/`False` work.

## Gotchas specific to editing this codebase

- The state machine (`app/bot/states/`) is the entry point for almost all bot behavior —
  before changing a Telegram flow, find the relevant `State`/`BaseSubState` subclass rather
  than editing `telegram_bot.py` handlers directly.
- Hashtag taxonomy lives in `app/database/db_hashtag.py` (`hashtag_categories`) and is
  mirrored into localization JSON under `settings/localization/*.json` — a new hashtag
  needs both a DB-side category entry and a translation key in every locale file, or the
  keyboard label will fall back oddly.
- `app/pipelines/pipeline.py`'s `Pipeline`/`DynamicPipeline` classes are the scheduling
  primitives used by both the parser and the news sender (`app/misc/scheduler.py`
  wires them to `APScheduler`). New periodic jobs should follow that pattern rather than
  spinning up ad hoc threads.
- Several classes (`AIFallbackRequester`, `ImageGeneratorFacade`, prototypes in
  `app/misc/prototype_registry.py`) rely on a `clone()`/`copy()` prototype pattern to avoid
  mutating shared registered instances — if a new resource type skips implementing
  `clone()` correctly, concurrent requests will corrupt each other's state.
- RSS-bridge parsing (`Parser.rss_bridge_parser`) assumes a local `rss-bridge` Docker
  container is reachable; it's disabled by default in `parser_pipeline.py`'s `main()`.

## Given the spike status

Don't "finish" or "productionize" adjacent code (add deployment config, wire up the stubbed
transcription/speech factories, fix unrelated dead code) unless explicitly asked — this
repo has a lot of half-built surface area, and cleanup work here should be scoped tightly
to what's requested to avoid resurrecting features nobody asked to complete.
