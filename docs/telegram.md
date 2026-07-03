# Telegram

Exposes the agent as a Telegram bot, living at `demo/telegram/`. It talks to Telegram over a webhook rather than polling: Telegram pushes each update to a public HTTPS URL the bot registers on startup.

## Setup

```sh
uv sync --group telegram --group anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

Set in `.env` or the environment:

- `TELEGRAM_BOT_TOKEN` — the bot's API token, from [@BotFather](https://t.me/BotFather).
- `TELEGRAM_WEBHOOK_URL` — the public HTTPS URL Telegram should deliver updates to; its path becomes the route the bot listens on. Optional when running with `--ngrok`.

```sh
uv run telegram-demo
```

The process listens on `0.0.0.0:8080` by default, overridable with `PORT`, and registers `TELEGRAM_WEBHOOK_URL` with Telegram on startup.

Pass `--ngrok` to run behind an ad-hoc [ngrok](https://ngrok.com/) tunnel instead, for a locally run bot with no public URL of its own. The tunnel's host replaces `TELEGRAM_WEBHOOK_URL`'s, so the variable can be omitted entirely.

> [!TIP]
> The bot itself doesn't restrict who can message it. To limit access, use [@BotFather](https://t.me/BotFather)'s *Bot Settings* → *Access* → *Restrict bot usage*, which lets Telegram itself drop messages from anyone not on the allowed users list.

## Behavior

Every incoming update is checked against a per-bot secret token (derived from `TELEGRAM_BOT_TOKEN`, sent to Telegram at webhook registration) before anything else runs, so only Telegram's own callbacks are accepted.

Accepted messages are fed to a single long-running `Agent`, so the conversation persists across messages. Tool calls are announced as their own message (`⛭ tool_name`) before the reply that follows.
