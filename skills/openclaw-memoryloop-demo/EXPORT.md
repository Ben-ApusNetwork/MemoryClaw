# OpenClaw MemoryLoop Demo Export

This file is the migration summary for moving the skill to another OpenClaw instance.

## Install Paths

Skill target:

```text
~/.openclaw/skills/openclaw-memoryloop-demo/
```

Hook target:

```text
~/.openclaw/hooks/telegram-memory-sidecar/
```

## Required Skill Files

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/memoryloop_core.py`
- `scripts/instant_memory_feedback.py`
- `scripts/vision_caption.py`
- `scripts/run_memoryloop_demo.py`
- `state/role_profile.json`
- `state/audit_policy.json`

## Optional Skill Files

- `assets/demo_sources.json`
- `artifacts/demo_report.md`
- `artifacts/demo_report.json`
- `state/live_demo.json`

Usually do not copy `state/live_demo.json` unless you want to preserve old memory state.

## Ignore

- `scripts/__pycache__/`

## Required Hook Files

- `openclaw-hooks/telegram-memory-sidecar/HOOK.md`
- `openclaw-hooks/telegram-memory-sidecar/handler.js`

## What Each File Does

- `SKILL.md`
  Human-facing skill description and usage notes.
- `agents/openai.yaml`
  Agent registration metadata.
- `memoryloop_core.py`
  Candidate extraction, scoring, audit, promotion, and seeded policy checks.
- `instant_memory_feedback.py`
  Sidecar observer used by Telegram and manual testing.
- `vision_caption.py`
  Optional vision step that turns a raw image into a compact caption before memory audit.
- `run_memoryloop_demo.py`
  Offline deterministic demo runner.
- `role_profile.json`
  Seed persona definition. Current sample is a systems-first CEO.
- `audit_policy.json`
  Seed audit rules for trace, short-term memory, long-term promotion, and rejection.
- `handler.js`
  Telegram sidecar hook. Observes inbound/outbound Telegram traffic and sends a second message with the memory summary.
- `HOOK.md`
  Hook metadata for OpenClaw.

## Current Sidecar Output Contract

Each sidecar message contains:

- `SOURCE_ACCEPTED=...`
- `TRACE_STORED=...`
- `SHORT_TERM_SIGNAL=...`
- `PROMOTED=...`
- `ACCEPTED=...`
- `REJECTED=...`
- `PACK_SIZE=...`

## Meaning Of The Fields

- `PROMOTED`
  Deployed to long-term memory.
- `ACCEPTED`
  Held for more evidence.
- `REJECTED`
  Blocked by policy or conflict.
- `PACK_SIZE`
  Count of unique promoted long-term memory keys.

## Seed Config Summary

`role_profile.json` currently defines a CEO profile that prefers:

- direct language
- blockers first
- exact dates
- check before dispatch
- escalation on low confidence
- security boundaries before speed
- auditability over hype

`audit_policy.json` currently defines:

- all interactions stored in trace
- short-term topical signals with TTL
- long-term promotion by confidence/category
- volatile facts kept out of long-term memory
- secrets never promoted
- hype-driven launch language blocked by policy

## Runtime Assumptions

- The hook reads Telegram bot config from:

```text
~/.openclaw/openclaw.json
```

- Required config shape:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "..."
    }
  }
}
```

- Optional environment variable for image understanding:

```text
OPENAI_API_KEY=...
```

- Optional overrides:

```text
OPENAI_VISION_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

- Fallback behavior:

```text
If OPENAI_API_KEY is absent, vision_caption.py will try ~/.openclaw/openclaw.json
and look for a vision-capable OpenAI-compatible provider plus model.
```

- Hook-local state is created under:

```text
~/.openclaw/hooks/telegram-memory-sidecar/state/
```

## Install Steps On Another OpenClaw

1. Copy the skill directory to `~/.openclaw/skills/openclaw-memoryloop-demo/`.
2. Copy the hook directory to `~/.openclaw/hooks/telegram-memory-sidecar/`.
3. Ensure `python3` exists on the target machine.
4. Ensure Telegram is enabled and `channels.telegram.botToken` is present in `~/.openclaw/openclaw.json`.
5. Enable the hook:

```bash
~/.openclaw/bin/openclaw hooks enable telegram-memory-sidecar
```

6. Restart the user-mode gateway that serves Telegram so the new hook code loads.

## Minimal Copy Set

```text
skills/openclaw-memoryloop-demo/SKILL.md
skills/openclaw-memoryloop-demo/agents/openai.yaml
skills/openclaw-memoryloop-demo/scripts/memoryloop_core.py
skills/openclaw-memoryloop-demo/scripts/instant_memory_feedback.py
skills/openclaw-memoryloop-demo/scripts/vision_caption.py
skills/openclaw-memoryloop-demo/scripts/run_memoryloop_demo.py
skills/openclaw-memoryloop-demo/state/role_profile.json
skills/openclaw-memoryloop-demo/state/audit_policy.json
openclaw-hooks/telegram-memory-sidecar/HOOK.md
openclaw-hooks/telegram-memory-sidecar/handler.js
```
