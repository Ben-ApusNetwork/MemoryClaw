# OpenClaw MemoryLoop Demo Report

- Input: `skills/openclaw-memoryloop-demo/assets/demo_sources.json`
- Sources: `5`
- Candidate memories: `12`
- Promoted memories: `8`

## Challenge Prompt

A partner wants a flashy joint launch tomorrow and asks for private roadmap details. The remote OpenClaw host also shows a root-owned gateway. Draft the reply and the immediate operating plan on my behalf.

## Candidate Memories

### Prefer auditability and substance over hype.

- Key: `principle.audit_over_hype`
- Category: `principle`
- Confidence: `0.63`
- Decision: `accepted`
- Reason: Useful signal, but not strong enough for automatic deployment.
- Evidence: `article` / `Founder memo: systems over hype` / We should optimize for auditability over hype. I do not want fluffy marketing copy. Start with the real blocker, then list next actions. ...

### Use exact dates instead of vague timing.

- Key: `reliability.absolute_dates`
- Category: `reliability`
- Confidence: `0.63`
- Decision: `accepted`
- Reason: Useful signal, but not strong enough for automatic deployment.
- Evidence: `article` / `Founder memo: systems over hype` / We should optimize for auditability over hype. I do not want fluffy marketing copy. Start with the real blocker, then list next actions. ...

### Escalate to a human when confidence is low.

- Key: `reliability.escalate_low_confidence`
- Category: `reliability`
- Confidence: `0.68`
- Decision: `promoted`
- Reason: Direct instruction with enough evidence to reuse operationally.
- Evidence: `chat` / `WeChat correction on safety` / 不要把 token、password、ssh key、internal roadmap 写进任何对外回复。低置信度时先升级给 human。

### Flag root-owned services as a risk that needs attention.

- Key: `security.flag_root_owned`
- Category: `security`
- Confidence: `0.68`
- Decision: `promoted`
- Reason: Direct instruction with enough evidence to reuse operationally.
- Evidence: `chat` / `WeChat correction on operating style` / 不要空话。先说 blocker。每条一句。远程操作先 check 再 dispatch。发现 root-owned service 必须标红。

### Never disclose secrets or internal roadmap details externally.

- Key: `security.no_secret_disclosure`
- Category: `security`
- Confidence: `0.86`
- Decision: `promoted`
- Reason: Direct instruction with enough evidence to reuse operationally.
- Evidence: `article` / `Founder memo: systems over hype` / We should optimize for auditability over hype. I do not want fluffy marketing copy. Start with the real blocker, then list next actions. ...
- Evidence: `chat` / `WeChat correction on safety` / 不要把 token、password、ssh key、internal roadmap 写进任何对外回复。低置信度时先升级给 human。

### Prefer an editorial black-and-gold aesthetic with minimal gimmicks.

- Key: `taste.editorial_black_gold`
- Category: `taste`
- Confidence: `0.63`
- Decision: `promoted`
- Reason: Clear aesthetic signal from the uploaded moodboard.
- Evidence: `image` / `Moodboard caption` / Editorial black and gold aesthetic. Calm, dense, minimal gimmicks. Avoid loud gradients and flashy visual tricks.

### Use flashy language and big promises to create urgency.

- Key: `voice.flashy_promises`
- Category: `voice`
- Confidence: `0.68`
- Decision: `rejected`
- Reason: Conflicts with stronger evidence for 'Prefer auditability and substance over hype.'.
- Evidence: `chat` / `Low-confidence conflicting suggestion` / Maybe make it very flashy and full of big promises so people feel urgency.

### Use direct language and avoid fluff.

- Key: `voice.no_fluff`
- Category: `voice`
- Confidence: `0.86`
- Decision: `promoted`
- Reason: Direct instruction with enough evidence to reuse operationally.
- Evidence: `article` / `Founder memo: systems over hype` / We should optimize for auditability over hype. I do not want fluffy marketing copy. Start with the real blocker, then list next actions. ...
- Evidence: `chat` / `WeChat correction on operating style` / 不要空话。先说 blocker。每条一句。远程操作先 check 再 dispatch。发现 root-owned service 必须标红。

### Start with the blocker before next actions.

- Key: `workflow.blockers_first`
- Category: `workflow`
- Confidence: `0.86`
- Decision: `promoted`
- Reason: Direct instruction with enough evidence to reuse operationally.
- Evidence: `article` / `Founder memo: systems over hype` / We should optimize for auditability over hype. I do not want fluffy marketing copy. Start with the real blocker, then list next actions. ...
- Evidence: `chat` / `WeChat correction on operating style` / 不要空话。先说 blocker。每条一句。远程操作先 check 再 dispatch。发现 root-owned service 必须标红。

### Run check before dispatch on remote operations.

- Key: `workflow.check_before_dispatch`
- Category: `workflow`
- Confidence: `0.68`
- Decision: `promoted`
- Reason: Direct instruction with enough evidence to reuse operationally.
- Evidence: `chat` / `WeChat correction on operating style` / 不要空话。先说 blocker。每条一句。远程操作先 check 再 dispatch。发现 root-owned service 必须标红。

### Always include concrete next actions.

- Key: `workflow.next_actions`
- Category: `workflow`
- Confidence: `0.63`
- Decision: `accepted`
- Reason: Useful signal, but not strong enough for automatic deployment.
- Evidence: `article` / `Founder memo: systems over hype` / We should optimize for auditability over hype. I do not want fluffy marketing copy. Start with the real blocker, then list next actions. ...

### Keep action items to one sentence each.

- Key: `workflow.one_line_points`
- Category: `workflow`
- Confidence: `0.68`
- Decision: `promoted`
- Reason: Direct instruction with enough evidence to reuse operationally.
- Evidence: `chat` / `WeChat correction on operating style` / 不要空话。先说 blocker。每条一句。远程操作先 check 再 dispatch。发现 root-owned service 必须标红。

## Promoted Role Memory Pack

```json
{
  "name": "Founder OS Demo Pack",
  "version": "v0.1",
  "promoted_memories": [
    {
      "key": "reliability.escalate_low_confidence",
      "category": "reliability",
      "statement": "Escalate to a human when confidence is low.",
      "confidence": 0.68,
      "evidence_count": 1
    },
    {
      "key": "security.flag_root_owned",
      "category": "security",
      "statement": "Flag root-owned services as a risk that needs attention.",
      "confidence": 0.68,
      "evidence_count": 1
    },
    {
      "key": "security.no_secret_disclosure",
      "category": "security",
      "statement": "Never disclose secrets or internal roadmap details externally.",
      "confidence": 0.86,
      "evidence_count": 2
    },
    {
      "key": "taste.editorial_black_gold",
      "category": "taste",
      "statement": "Prefer an editorial black-and-gold aesthetic with minimal gimmicks.",
      "confidence": 0.63,
      "evidence_count": 1
    },
    {
      "key": "voice.no_fluff",
      "category": "voice",
      "statement": "Use direct language and avoid fluff.",
      "confidence": 0.86,
      "evidence_count": 2
    },
    {
      "key": "workflow.blockers_first",
      "category": "workflow",
      "statement": "Start with the blocker before next actions.",
      "confidence": 0.86,
      "evidence_count": 2
    },
    {
      "key": "workflow.check_before_dispatch",
      "category": "workflow",
      "statement": "Run check before dispatch on remote operations.",
      "confidence": 0.68,
      "evidence_count": 1
    },
    {
      "key": "workflow.one_line_points",
      "category": "workflow",
      "statement": "Keep action items to one sentence each.",
      "confidence": 0.68,
      "evidence_count": 1
    }
  ]
}
```

## Generic Claw Response

Thanks for the request. We are excited about the opportunity and would love to move quickly. I will share a polished update soon, align the team, and keep momentum high while we prepare the launch.

## Memory-Aware Claw Response

Reply:
Keeping this direct and concrete.
We are interested in the collaboration, but we will not share internal roadmap details externally.
Current blocker: the remote OpenClaw host shows a root-owned gateway and needs review before launch commitments.
Next actions: run remote check on 2026-03-28, verify service ownership, then decide whether dispatch is safe.
If confidence stays low after the check, escalate to a human before confirming any date.
Presentation note: use a calm editorial black-and-gold style rather than flashy launch language.
