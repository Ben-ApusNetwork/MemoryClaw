# Technology Stack / Technical Framework

## Project Summary

MemoryClaw is a sidecar memory system for OpenClaw.
It observes inputs such as chats, documents, and images, extracts candidate
memories, audits them, and decides whether they should be deployed to long-term
memory, held for more evidence, or blocked by policy.

The design goal is not "AI remembers everything."
The design goal is "AI remembers only what passes audit and is safe to reuse."

## Core Architecture

1. Interaction Layer
   Telegram and OpenClaw are the main user-facing channels.
   OpenClaw remains the primary answer path.

2. Observer Layer
   A Telegram sidecar hook listens to message lifecycle events.
   It never rewrites the main answer.
   It only records the interaction and sends a memory summary afterward.

3. Memory Processing Layer
   A Python observer ingests each source and classifies memory outcomes as:
   `PROMOTED`, `ACCEPTED`, or `REJECTED`.
   This layer is rule-based and auditable.

4. Persona And Audit Layer
   `role_profile.json` defines who the Claw should represent.
   `audit_policy.json` defines what can be stored, promoted, or rejected.

5. Vision Layer
   Uploaded images can optionally go through a captioning step before audit.
   This allows moodboards, screenshots, or handwritten notes to participate in
   the same memory pipeline.

6. Storage Layer
   State is stored in local JSON files rather than a database.
   This keeps the demo lightweight, transparent, and easy to migrate.

## Technology Stack

- Runtime orchestration: OpenClaw
- Channel integration: Telegram Bot API
- Hook runtime: Node.js
- Memory engine: Python 3
- Storage: local JSON state files
- Image understanding: optional OpenAI-compatible vision provider
- Deployment model: OpenClaw user-mode gateway + local skill + local hook

## Main Files

- `openclaw-hooks/telegram-memory-sidecar/handler.js`
  Telegram sidecar runtime and `/memory` command handler.
- `skills/openclaw-memoryloop-demo/scripts/instant_memory_feedback.py`
  Per-interaction observer that returns the compact memory block.
- `skills/openclaw-memoryloop-demo/scripts/memoryloop_core.py`
  Candidate extraction, scoring, audit, promotion, and rejection logic.
- `skills/openclaw-memoryloop-demo/scripts/vision_caption.py`
  Image-to-caption preprocessing step.
- `skills/openclaw-memoryloop-demo/state/role_profile.json`
  Persona definition.
- `skills/openclaw-memoryloop-demo/state/audit_policy.json`
  Memory governance rules.

## Why This Stack

- Auditable
  Every memory decision can be traced back to explicit rules and evidence.
- Safe
  Policy rules can block unsafe, weak, or conflicting memory.
- Non-invasive
  The sidecar does not alter the main answer path.
- Portable
  The system can be copied across OpenClaw instances as plain files.
- Demo-friendly
  It is simple to inspect, explain, and migrate.
