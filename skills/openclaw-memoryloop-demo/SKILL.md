---
name: openclaw-memoryloop-demo
description: Use when the user wants a small demo showing how uploaded articles, images, and chats can be distilled into audited long-term memory for an OpenClaw persona. Triggers include "memory loop demo", "OpenClaw personality demo", "上传文章图片聊天做记忆审计", and "audited memory pack".
---

# OpenClaw MemoryLoop Demo

Use this skill to run a deterministic local demo of an audited memory loop:

1. ingest mixed-source materials such as articles, image captions, raw uploaded images, and chats
2. extract candidate memories
3. audit each candidate for confidence, conflict, and safety
4. promote approved memories into a role memory pack
5. show how that memory pack changes the final response

## Demo Goal

This demo is not "the agent stored notes." The demo is:

- the system can defend why a memory was accepted
- the system can reject weak or conflicting memories
- the promoted memory pack changes how the Claw speaks and decides

## Run The Demo

From the workspace root:

```bash
python3 skills/openclaw-memoryloop-demo/scripts/run_memoryloop_demo.py \
  --input skills/openclaw-memoryloop-demo/assets/demo_sources.json \
  --output skills/openclaw-memoryloop-demo/artifacts/demo_report.md
```

The script writes:

- a Markdown report with candidate memories, audit decisions, and a final response
- a JSON artifact with the promoted role memory pack beside the report

## Instant Feedback Mode

Use this mode when you want the Skill to behave like a sidecar observer. It should not change the main OpenClaw task logic. It only watches each ingested source and emits a compact status block.

Reset the live demo state:

```bash
python3 skills/openclaw-memoryloop-demo/scripts/instant_memory_feedback.py \
  --state skills/openclaw-memoryloop-demo/state/live_demo.json \
  reset
```

Then ingest each source one at a time:

```bash
python3 skills/openclaw-memoryloop-demo/scripts/instant_memory_feedback.py \
  --state skills/openclaw-memoryloop-demo/state/live_demo.json \
  ingest \
  --source-type chat \
  --title "Operating style" \
  --content "不要空话。先说 blocker。每条一句。远程操作先 check 再 dispatch。发现 root-owned service 必须标红。"
```

The command returns a compact sidecar block:

- `SOURCE_ACCEPTED=...`
- `TRACE_STORED=...`
- `SHORT_TERM_SIGNAL=...`
- `PROMOTED=...`
- `ACCEPTED=...`
- `REJECTED=...`
- `PACK_SIZE=...`

You can also observe a completed Q&A without changing the main answer path:

```bash
python3 skills/openclaw-memoryloop-demo/scripts/instant_memory_feedback.py \
  --state skills/openclaw-memoryloop-demo/state/live_demo.json \
  observe \
  --user-text "帮我看看最新的国际新闻" \
  --assistant-text "Here is the answer that the main OpenClaw already returned."
```

Interpretation:

- `TRACE_STORED` means the raw source plus answer trace was recorded for audit and replay.
- `SHORT_TERM_SIGNAL` is a TTL-bound working-memory hint such as a current topic the user is tracking.
- `PROMOTED / ACCEPTED / REJECTED` show the audit decision for this source's candidate memories.
- raw `image` uploads can now go through an optional vision step; if `OPENAI_API_KEY` is present, the sidecar will first generate a compact visual caption and then audit that as an `image` source
- if `OPENAI_API_KEY` is absent, the vision step can also fall back to a vision-capable OpenAI-compatible provider configured inside `~/.openclaw/openclaw.json`

Use this sequentially. Do not ingest multiple sources in parallel against the same state file.

## Seed Config

The skill now ships with starter config files that define what the Claw is supposed to represent and how memory should be audited:

- [role_profile.json](/Users/ben/Documents/New%20project/skills/openclaw-memoryloop-demo/state/role_profile.json)
- [audit_policy.json](/Users/ben/Documents/New%20project/skills/openclaw-memoryloop-demo/state/audit_policy.json)

In this sample:

- `role_profile.json` describes a systems-first CEO persona
- `audit_policy.json` describes what should stay in trace, what should become short-term memory, and what can be promoted into long-term memory

## What The Demo Shows

- `article` sources inform principles and judgment
- `image` sources inform aesthetic taste, but should not overclaim beyond the evidence
- `chat` sources inform voice, workflow, escalation, and security boundaries

## Audit Rules

- promote memories that are directly supported and stable enough to reuse
- reject memories that conflict with stronger evidence
- reject or hold memories that are sensitive, temporary, or weakly supported
- treat image-only inferences as lower confidence unless they are clearly aesthetic

## Expected Output

The report should visibly show:

- accepted vs rejected candidate memories
- the promoted role memory pack
- a generic answer
- a memory-aware answer that sounds more aligned, safer, and more operational
