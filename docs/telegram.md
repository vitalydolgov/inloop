# Telegram

Exposes the agent as a Telegram bot, living at `demo/telegram/`. It talks to Telegram over a webhook rather than polling: Telegram pushes each update to a public HTTPS URL the bot registers on startup.

## Setup

```sh
uv sync --group telegram --group anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

Set in `.env` or the environment:

- `TELEGRAM_BOT_TOKEN` — the bot's API token, from [@BotFather](https://t.me/BotFather).
- `TELEGRAM_USER_ID` — the only Telegram user id the bot will respond to.
- `TELEGRAM_WEBHOOK_URL` — the public HTTPS URL Telegram should deliver updates to; its path becomes the route the bot listens on. Must be reachable from Telegram's servers, so a locally run bot needs a tunnel (e.g. ngrok) in front of it.

```sh
uv run telegram-demo
```

The process listens on `0.0.0.0:8080` by default, overridable with `PORT`, and registers `TELEGRAM_WEBHOOK_URL` with Telegram on startup.

## Behavior

Every incoming update is checked against a per-bot secret token (derived from `TELEGRAM_BOT_TOKEN`, sent to Telegram at webhook registration) before anything else runs, so only Telegram's own callbacks are accepted. Messages from any user other than `TELEGRAM_USER_ID` are silently dropped.

Accepted messages are fed to a single long-running `Agent`, so the conversation persists across messages for the allowed user. Tool calls are announced as their own message (`⛭ tool_name`) before the reply that follows.

The agent's Markdown replies (bold, italic, inline/fenced code, links, lists, blockquotes) are converted to Telegram's HTML formatting by `demo/telegram/formatting.py` before sending.
