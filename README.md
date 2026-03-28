# MemoryClaw

MemoryClaw is an audited memory sidecar for OpenClaw.

It does not replace the main agent workflow. Instead, it observes chats,
documents, and images, extracts candidate memories, audits them, and decides
whether they should be:

- `PROMOTED`: deployed to long-term memory
- `ACCEPTED`: held for more evidence
- `REJECTED`: blocked by policy

The project is designed for AI-native organization workflows where memory must
be reusable, explainable, and policy-aware.

## Repository Layout

- `docs/`
  High-level technical documentation.
- `skills/openclaw-memoryloop-demo/`
  The OpenClaw skill, demo runner, memory engine, and seed policy/persona.
- `openclaw-hooks/telegram-memory-sidecar/`
  The Telegram hook that observes interactions and sends memory summaries.

## Key Features

- Audited memory extraction from user interactions
- Compact sidecar summaries after Telegram replies
- `/memory` command support for viewing current stored memory
- Rule-based governance using persona and audit policy files
- Optional image captioning step before memory audit

## Core Output Contract

Each observer summary uses the same compact format:

- `SOURCE_ACCEPTED=...`
- `TRACE_STORED=...`
- `SHORT_TERM_SIGNAL=...`
- `PROMOTED=...`
- `ACCEPTED=...`
- `REJECTED=...`
- `PACK_SIZE=...`

`PACK_SIZE` counts unique promoted long-term memory keys.

## Install Targets

Copy these folders to the target OpenClaw machine:

- `skills/openclaw-memoryloop-demo/` -> `~/.openclaw/skills/openclaw-memoryloop-demo/`
- `openclaw-hooks/telegram-memory-sidecar/` -> `~/.openclaw/hooks/telegram-memory-sidecar/`

Then enable the hook:

```bash
~/.openclaw/bin/openclaw hooks enable telegram-memory-sidecar
```

Restart the user-mode gateway that serves Telegram after installation.

## Requirements

- `python3`
- Telegram configured in `~/.openclaw/openclaw.json`
- `channels.telegram.botToken` configured
- Optional `OPENAI_API_KEY` or another vision-capable provider for raw image understanding

## Additional Docs

- `docs/TECH_STACK.md`
- `skills/openclaw-memoryloop-demo/EXPORT.md`
