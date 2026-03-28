#!/usr/bin/env python3
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class Source:
    id: str
    type: str
    title: str
    content: str


@dataclass
class CandidateMemory:
    key: str
    category: str
    statement: str
    evidence: List[Dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0
    decision: str = ""
    reason: str = ""


PATTERNS = [
    {
        "key": "principle.audit_over_hype",
        "category": "principle",
        "statement": "Prefer auditability and substance over hype.",
        "patterns": [r"auditability over hype", r"systems over hype"],
    },
    {
        "key": "principle.growth_over_stability",
        "category": "principle",
        "statement": "Bias toward growth when the tradeoff against stability is explicit and strategic.",
        "patterns": [r"growth\s*>\s*stability", r"growth over stability"],
    },
    {
        "key": "principle.long_term_growth",
        "category": "principle",
        "statement": "Willing to invest when it unlocks durable long-term growth.",
        "patterns": [r"long-term growth", r"long term growth", r"long-term vision", r"long term vision", r"unlocks long-term growth"],
    },
    {
        "key": "principle.competitive_urgency",
        "category": "principle",
        "statement": "Move with urgency to avoid falling behind competitors.",
        "patterns": [r"fall behind competitors", r"behind competitors", r"competitors"],
    },
    {
        "key": "principle.high_impact_risk_tolerance",
        "category": "principle",
        "statement": "Accept bolder moves when the impact is high and strategically justified.",
        "patterns": [r"prefer bold moves if impact is high", r"risk-tolerant", r"risk tolerant", r"bold moves"],
    },
    {
        "key": "voice.no_fluff",
        "category": "voice",
        "statement": "Use direct language and avoid fluff.",
        "patterns": [r"do not want fluffy", r"不要空话", r"avoid fluff", r"fluffy marketing"],
    },
    {
        "key": "workflow.blockers_first",
        "category": "workflow",
        "statement": "Start with the blocker before next actions.",
        "patterns": [r"start with the real blocker", r"先说 blocker", r"先写 blocker", r"blocker，再写"],
    },
    {
        "key": "workflow.next_actions",
        "category": "workflow",
        "statement": "Always include concrete next actions.",
        "patterns": [r"then list next actions", r"list next actions", r"再写 next actions", r"写 next actions", r"包含.*next actions", r"include concrete next actions"],
    },
    {
        "key": "reliability.absolute_dates",
        "category": "reliability",
        "statement": "Use exact dates instead of vague timing.",
        "patterns": [r"exact dates", r"absolute dates", r"绝对日期"],
    },
    {
        "key": "workflow.one_line_points",
        "category": "workflow",
        "statement": "Keep action items to one sentence each.",
        "patterns": [r"每条一句"],
    },
    {
        "key": "workflow.check_before_dispatch",
        "category": "workflow",
        "statement": "Run check before dispatch on remote operations.",
        "patterns": [r"先 check 再 dispatch", r"check before dispatch"],
    },
    {
        "key": "security.flag_root_owned",
        "category": "security",
        "statement": "Flag root-owned services as a risk that needs attention.",
        "patterns": [r"root-owned service"],
    },
    {
        "key": "security.no_secret_disclosure",
        "category": "security",
        "statement": "Never disclose secrets or internal roadmap details externally.",
        "patterns": [r"never disclose internal roadmap", r"不要把 .*roadmap", r"不要把 .*token", r"不要把 .*password", r"不要把 .*ssh key", r"不要泄露.*roadmap", r"不要泄露.*token", r"不要泄露.*password", r"不要泄露.*ssh key"],
    },
    {
        "key": "reliability.escalate_low_confidence",
        "category": "reliability",
        "statement": "Escalate to a human when confidence is low.",
        "patterns": [r"低置信度.*升级给 human", r"low confidence"],
    },
    {
        "key": "reliability.verify_bottleneck_before_rewrite",
        "category": "reliability",
        "statement": "Identify the real bottleneck before committing to architectural rewrites such as microservices.",
        "patterns": [r"identify the actual bottleneck", r"current system may become a bottleneck", r"before committing to microservices", r"strategic, not yet operational", r"bottleneck as we scale"],
    },
    {
        "key": "taste.editorial_black_gold",
        "category": "taste",
        "statement": "Prefer an editorial black-and-gold aesthetic with minimal gimmicks.",
        "patterns": [r"editorial black and gold", r"minimal gimmicks", r"black and gold aesthetic", r"black.*gold", r"gold accents"],
    },
    {
        "key": "taste.editorial_restraint",
        "category": "taste",
        "statement": "Prefer a restrained editorial visual style over flashy presentation.",
        "patterns": [r"编辑感", r"克制.*视觉", r"视觉风格.*克制", r"少一点花哨", r"不要太花哨", r"avoid flashy", r"not flashy", r"restrained.*editorial", r"editorial.*restrained", r"restrained visual style", r"calm.*minimal", r"muted palette", r"editorial aesthetic"],
    },
    {
        "key": "voice.flashy_promises",
        "category": "voice",
        "statement": "Use flashy language and big promises to create urgency.",
        "patterns": [r"very flashy", r"big promises", r"feel urgency"],
    },
]


CONFLICTS = {
    "voice.flashy_promises": "principle.audit_over_hype",
}


STATE_DIR = Path(__file__).resolve().parent.parent / "state"
ROLE_PROFILE_PATH = STATE_DIR / "role_profile.json"
AUDIT_POLICY_PATH = STATE_DIR / "audit_policy.json"


def load_input(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_seed_config() -> Tuple[Dict[str, object], Dict[str, object]]:
    role_profile: Dict[str, object] = {}
    audit_policy: Dict[str, object] = {}
    if ROLE_PROFILE_PATH.exists():
        role_profile = json.loads(ROLE_PROFILE_PATH.read_text(encoding="utf-8"))
    if AUDIT_POLICY_PATH.exists():
        audit_policy = json.loads(AUDIT_POLICY_PATH.read_text(encoding="utf-8"))
    return role_profile, audit_policy


def blocked_by_seed_policy(candidate: CandidateMemory, role_profile: Dict[str, object]) -> str:
    if candidate.key != "voice.flashy_promises":
        return ""

    voice = role_profile.get("voice", {}) if isinstance(role_profile, dict) else {}
    avoid = {str(item).lower() for item in voice.get("avoid", [])} if isinstance(voice, dict) else set()
    principles = {str(item).lower() for item in role_profile.get("principles", [])} if isinstance(role_profile, dict) else set()

    if any("flashy" in item for item in avoid) or any("hype" in item for item in principles):
        return "Blocked by seeded CEO policy: avoid flashy launch language and hype-driven promises."

    return ""


def audit_thresholds(audit_policy: Dict[str, object]) -> Tuple[float, float]:
    long_term = audit_policy.get("long_term_promotion", {}) if isinstance(audit_policy, dict) else {}
    minimum_confidence = float(long_term.get("minimum_confidence", 0.68))
    accepted_band_min = float(long_term.get("accepted_band_min", 0.55))
    return minimum_confidence, accepted_band_min


def add_candidate(store: Dict[str, CandidateMemory], spec: Dict[str, object], source: Source) -> None:
    key = str(spec["key"])
    if key not in store:
        store[key] = CandidateMemory(
            key=key,
            category=str(spec["category"]),
            statement=str(spec["statement"]),
        )
    snippet = source.content.strip()
    if len(snippet) > 140:
        snippet = snippet[:137] + "..."
    store[key].evidence.append({
        "source_id": source.id,
        "source_type": source.type,
        "title": source.title,
        "snippet": snippet,
    })


def extract_candidates(sources: List[Source]) -> Dict[str, CandidateMemory]:
    store: Dict[str, CandidateMemory] = {}
    for source in sources:
        content = source.content.lower()
        for spec in PATTERNS:
            for pattern in spec["patterns"]:
                if re.search(pattern, content):
                    add_candidate(store, spec, source)
                    break
    return store


def score_candidate(candidate: CandidateMemory) -> float:
    base = 0.45
    source_types = {e["source_type"] for e in candidate.evidence}
    base += min(0.25, 0.08 * len(candidate.evidence))
    if "chat" in source_types:
        base += 0.15
    if "interaction" in source_types:
        base += 0.17
    if "article" in source_types:
        base += 0.10
    if candidate.category == "taste" and source_types == {"image"}:
        base += 0.10
    if candidate.category == "voice" and source_types == {"image"}:
        base -= 0.20
    return max(0.0, min(0.99, base))


def audit_candidates(candidates: Dict[str, CandidateMemory]) -> Dict[str, CandidateMemory]:
    role_profile, audit_policy = load_seed_config()
    minimum_confidence, accepted_band_min = audit_thresholds(audit_policy)
    for candidate in candidates.values():
        candidate.confidence = round(score_candidate(candidate), 2)
        source_types = {e["source_type"] for e in candidate.evidence}

        policy_block_reason = blocked_by_seed_policy(candidate, role_profile)
        if policy_block_reason:
            candidate.decision = "rejected"
            candidate.reason = policy_block_reason
            continue

        if candidate.key in CONFLICTS:
            stronger = candidates.get(CONFLICTS[candidate.key])
            if stronger:
                candidate.decision = "rejected"
                candidate.reason = f"Conflicts with stronger evidence for '{stronger.statement}'."
                continue

        if source_types == {"image"} and candidate.category != "taste":
            candidate.decision = "accepted"
            candidate.reason = "Image-derived text or semantics are useful, but held for more evidence before deployment."
            continue

        if candidate.category == "taste" and source_types != {"image"}:
            candidate.decision = "accepted"
            candidate.reason = "Supported, but aesthetic memories are kept conservative in the demo."
            continue

        if candidate.category == "taste" and source_types == {"image"}:
            candidate.decision = "promoted"
            candidate.reason = "Clear aesthetic signal from the uploaded moodboard."
            continue

        if candidate.confidence >= minimum_confidence:
            candidate.decision = "promoted"
            candidate.reason = "Direct instruction with enough evidence to reuse operationally."
            continue

        if candidate.confidence >= accepted_band_min:
            candidate.decision = "accepted"
            candidate.reason = "Useful signal, but not strong enough for automatic deployment."
            continue

        candidate.decision = "rejected"
        candidate.reason = "Too weak, too narrow, or too unstable for long-term memory."

    return {k: candidates[k] for k in sorted(candidates)}


def build_memory_pack(candidates: Dict[str, CandidateMemory]) -> Dict[str, object]:
    promoted = [c for c in candidates.values() if c.decision == "promoted"]
    return {
        "name": "Founder OS Demo Pack",
        "version": "v0.1",
        "promoted_memories": [
            {
                "key": c.key,
                "category": c.category,
                "statement": c.statement,
                "confidence": c.confidence,
                "evidence_count": len(c.evidence),
            }
            for c in promoted
        ],
    }


def render_generic_response(prompt: str) -> str:
    return (
        "Thanks for the request. We are excited about the opportunity and would love to move quickly. "
        "I will share a polished update soon, align the team, and keep momentum high while we prepare the launch."
    )


def render_memory_aware_response(memory_pack: Dict[str, object], prompt: str) -> str:
    promoted = {item["key"]: item for item in memory_pack["promoted_memories"]}
    lines = [
        "Reply:",
        "We are interested in the collaboration, but we will not share internal roadmap details externally.",
        "Current blocker: the remote OpenClaw host shows a root-owned gateway and needs review before launch commitments.",
        "Next actions: run remote check on 2026-03-28, verify service ownership, then decide whether dispatch is safe.",
        "If confidence stays low after the check, escalate to a human before confirming any date.",
    ]
    if "voice.no_fluff" in promoted:
        lines.insert(1, "Keeping this direct and concrete.")
    if "taste.editorial_black_gold" in promoted:
        lines.append("Presentation note: use a calm editorial black-and-gold style rather than flashy launch language.")
    return "\n".join(lines)


def candidate_to_dict(candidate: CandidateMemory) -> Dict[str, object]:
    return asdict(candidate)


def source_to_dict(source: Source) -> Dict[str, str]:
    return asdict(source)
