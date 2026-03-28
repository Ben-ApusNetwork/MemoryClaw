---
name: telegram-memory-sidecar
description: "Append a compact memory observer summary after Telegram replies without changing the main answer path."
metadata:
  {
    "openclaw": {
      "emoji": "🧠",
      "events": ["message:preprocessed", "message:sent"],
      "requires": { "bins": ["python3"] }
    }
  }
---

# Telegram Memory Sidecar

This hook observes Telegram conversations as a sidecar.

It does not change the main model reply.

Instead it:

1. records the latest inbound Telegram message after preprocessing
2. if the inbound message includes an image, optionally runs a vision caption step
3. waits for the outbound reply to be sent successfully
4. calls the memory observer script
5. sends a compact status block as a follow-up Telegram message

## Output Contract

The follow-up message contains only:

- `SOURCE_ACCEPTED=...`
- `TRACE_STORED=...`
- `SHORT_TERM_SIGNAL=...`
- `PROMOTED=...`
- `ACCEPTED=...`
- `REJECTED=...`
- `PACK_SIZE=...`

## Safety

- Telegram only
- skips bot commands
- skips sidecar messages to avoid recursion
- keeps per-session pending input in a small local state file
- reads `channels.telegram.botToken` from `~/.openclaw/openclaw.json`
- uses `OPENAI_API_KEY` when available to caption raw image uploads before memory audit
- can also fall back to a vision-capable OpenAI-compatible provider from `~/.openclaw/openclaw.json`
