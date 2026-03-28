#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from hashlib import sha1
from json import JSONDecodeError
from pathlib import Path
from typing import Dict, List

from memoryloop_core import (
    Source,
    audit_candidates,
    build_memory_pack,
    candidate_to_dict,
    extract_candidates,
    source_to_dict,
)


DEFAULT_STATE = {"sources": [], "history": [], "working_signals": []}
GREETING_PATTERN = re.compile(r"^\s*(hi|hello|hey|你好|您好|嗨|哈喽)\s*[!,.?？。]*\s*$", re.IGNORECASE)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def default_state() -> Dict[str, object]:
    return {
        "sources": [],
        "history": [],
        "working_signals": [],
    }


def normalize_state(state: Dict[str, object]) -> Dict[str, object]:
    normalized = dict(DEFAULT_STATE)
    normalized.update(state or {})
    normalized["sources"] = list(normalized.get("sources", []))
    normalized["history"] = list(normalized.get("history", []))
    normalized["working_signals"] = prune_expired_signals(list(normalized.get("working_signals", [])))
    return normalized


def load_state(path: Path) -> Dict[str, object]:
    if not path.exists():
        return default_state()
    try:
        return normalize_state(json.loads(path.read_text(encoding="utf-8")))
    except JSONDecodeError:
        return default_state()


def write_state(path: Path, state: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def promoted_keys(memory_pack: Dict[str, object]) -> List[str]:
    return [item["key"] for item in memory_pack["promoted_memories"]]


def prune_expired_signals(signals: List[Dict[str, object]]) -> List[Dict[str, object]]:
    now = utc_now()
    kept: List[Dict[str, object]] = []
    for signal in signals:
        expires_at = str(signal.get("expires_at", "")).strip()
        if not expires_at:
            kept.append(signal)
            continue
        try:
            expiry = datetime.fromisoformat(expires_at)
        except ValueError:
            kept.append(signal)
            continue
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry > now:
            kept.append(signal)
    return kept


def trace_ref(source: Source) -> str:
    return f"{source.type}:{source.id}"


def is_question_like(text: str) -> bool:
    lowered = text.lower()
    if "?" in text or "？" in text:
        return True
    if re.search(r"\b(why|what|when|where|latest|news)\b", lowered):
        return True
    prompts = ["什么", "多少", "几", "怎么", "如何", "最新", "情况", "新闻"]
    return any(token in text for token in prompts)


def topic_slug(text: str) -> str:
    lowered = text.lower()
    if "缅甸" in text and "地震" in text:
        return "interest.myanmar_earthquake"
    if "国际新闻" in text or "international news" in lowered:
        return "interest.international_news"
    if "地震" in text:
        return "interest.earthquake_followup"
    if "新闻" in text or "news" in lowered:
        return "interest.current_events"
    compact = re.sub(r"\s+", "-", text.strip().lower())
    compact = re.sub(r"[^a-z0-9\-\u4e00-\u9fff]+", "", compact)
    compact = compact.strip("-")
    if compact:
        compact = compact[:32]
        return f"interest.followup.{compact}"
    digest = sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"interest.followup.{digest}"


def extract_short_term_signals(source: Source, assistant_text: str) -> List[Dict[str, object]]:
    if source.type != "interaction":
        return []
    text = source.content.strip()
    if not text or GREETING_PATTERN.match(text):
        return []
    if not is_question_like(text):
        return []

    ttl_hours = 6
    answer_preview = re.sub(r"\s+", " ", assistant_text.strip())
    if len(answer_preview) > 160:
        answer_preview = answer_preview[:157] + "..."

    return [
        {
            "key": topic_slug(text),
            "kind": "topical_followup",
            "source_id": source.id,
            "source_title": source.title,
            "question_preview": text[:80],
            "answer_preview": answer_preview,
            "ttl_hours": ttl_hours,
            "expires_at": (utc_now() + timedelta(hours=ttl_hours)).isoformat(),
        }
    ]


def merge_working_signals(
    existing: List[Dict[str, object]],
    new_signals: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    merged: Dict[str, Dict[str, object]] = {signal["key"]: signal for signal in existing}
    for signal in new_signals:
        merged[signal["key"]] = signal
    return [merged[key] for key in sorted(merged)]


def render_short_term_signal(signals: List[Dict[str, object]]) -> str:
    if not signals:
        return "SHORT_TERM_SIGNAL=none"
    rendered = [f"{signal['key']}@{signal['ttl_hours']}h" for signal in signals]
    return "SHORT_TERM_SIGNAL=" + ",".join(rendered)


def source_decision_buckets(
    audited: Dict[str, object],
    source_id: str,
) -> Dict[str, List[str]]:
    buckets = {
        "promoted": [],
        "accepted": [],
        "rejected": [],
    }
    for key, candidate in audited.items():
        if not any(e["source_id"] == source_id for e in candidate.evidence):
            continue
        decision = str(candidate.decision)
        if decision in buckets:
            buckets[decision].append(key)
    return buckets


def render_bucket(name: str, values: List[str]) -> str:
    return f"{name}=" + (",".join(values) if values else "none")


def summarize_feedback(
    source: Source,
    decision_buckets: Dict[str, List[str]],
    new_signals: List[Dict[str, object]],
    current_pack: Dict[str, object],
) -> str:
    lines: List[str] = []
    lines.append(f"SOURCE_ACCEPTED={source.type}:{source.title}")
    lines.append(f"TRACE_STORED={trace_ref(source)}")
    lines.append(render_short_term_signal(new_signals))
    lines.append(render_bucket("PROMOTED", decision_buckets["promoted"]))
    lines.append(render_bucket("ACCEPTED", decision_buckets["accepted"]))
    lines.append(render_bucket("REJECTED", decision_buckets["rejected"]))
    lines.append(f"PACK_SIZE={len(current_pack['promoted_memories'])}")
    return "\n".join(lines)


def next_source_id(previous_sources: List[Source]) -> str:
    return f"live-{len(previous_sources) + 1}"


def append_state_entry(
    state: Dict[str, object],
    state_path: Path,
    source: Source,
    all_sources: List[Source],
    feedback: str,
    decision_buckets: Dict[str, List[str]],
    pack: Dict[str, object],
    audited: Dict[str, object],
    new_signals: List[Dict[str, object]],
    assistant_text: str = "",
) -> None:
    state["sources"] = [source_to_dict(item) for item in all_sources]
    state["working_signals"] = merge_working_signals(
        list(state.get("working_signals", [])),
        new_signals,
    )
    entry = {
        "source": source_to_dict(source),
        "feedback": feedback,
        "decision_buckets": decision_buckets,
        "short_term_signals": new_signals,
        "active_working_signals": state["working_signals"],
        "memory_pack": pack,
        "audited_candidates": [candidate_to_dict(audited[key]) for key in sorted(audited)],
    }
    if assistant_text:
        entry["assistant_text"] = assistant_text
    state.setdefault("history", []).append(entry)
    write_state(state_path, state)


def maybe_write_report(report: str, feedback: str) -> None:
    if not report:
        return
    report_path = Path(report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(feedback + "\n", encoding="utf-8")


def cmd_reset(args: argparse.Namespace) -> int:
    state = default_state()
    write_state(Path(args.state), state)
    print("PACK_SIZE=0")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    state = load_state(state_path)
    previous_sources = [Source(**item) for item in state.get("sources", [])]

    source = Source(
        id=args.source_id or next_source_id(previous_sources),
        type=args.source_type,
        title=args.title,
        content=args.content,
    )
    all_sources = previous_sources + [source]
    audited = audit_candidates(extract_candidates(all_sources))
    pack = build_memory_pack(audited)
    new_signals: List[Dict[str, object]] = []
    decision_buckets = source_decision_buckets(audited, source.id)

    feedback = summarize_feedback(source, decision_buckets, new_signals, pack)
    append_state_entry(state, state_path, source, all_sources, feedback, decision_buckets, pack, audited, new_signals)
    maybe_write_report(args.report, feedback)

    print(feedback)
    return 0


def cmd_observe(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    state = load_state(state_path)
    previous_sources = [Source(**item) for item in state.get("sources", [])]

    title = args.title or args.user_text.strip().replace("\n", " ")[:48] or "interaction"
    source = Source(
        id=args.source_id or next_source_id(previous_sources),
        type=args.source_type,
        title=title,
        content=args.user_text,
    )
    all_sources = previous_sources + [source]
    audited = audit_candidates(extract_candidates(all_sources))
    pack = build_memory_pack(audited)
    new_signals = extract_short_term_signals(source, args.assistant_text)
    decision_buckets = source_decision_buckets(audited, source.id)

    feedback = summarize_feedback(source, decision_buckets, new_signals, pack)
    append_state_entry(
        state,
        state_path,
        source,
        all_sources,
        feedback,
        decision_buckets,
        pack,
        audited,
        new_signals,
        assistant_text=args.assistant_text,
    )
    maybe_write_report(args.report, feedback)

    print(feedback)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Incremental instant feedback for the OpenClaw MemoryLoop demo.")
    parser.add_argument("--state", required=True, help="Path to the live session state JSON")

    sub = parser.add_subparsers(dest="cmd", required=True)

    reset = sub.add_parser("reset", help="Reset the live demo state")
    reset.set_defaults(func=cmd_reset)

    ingest = sub.add_parser("ingest", help="Ingest one source and return immediate memory feedback")
    ingest.add_argument("--source-type", required=True, choices=["article", "image", "chat"], help="Source type")
    ingest.add_argument("--title", required=True, help="Short title for the source")
    ingest.add_argument("--content", required=True, help="Plain-text content or caption")
    ingest.add_argument("--source-id", default="", help="Optional fixed source id")
    ingest.add_argument("--report", default="", help="Optional path to write the latest feedback text")
    ingest.set_defaults(func=cmd_ingest)

    observe = sub.add_parser("observe", help="Observe a finished interaction and emit sidecar feedback")
    observe.add_argument("--source-type", default="interaction", choices=["interaction", "article", "image", "chat"], help="Observed source type")
    observe.add_argument("--user-text", required=True, help="Original user input")
    observe.add_argument("--assistant-text", default="", help="Rendered assistant answer for trace only")
    observe.add_argument("--title", default="", help="Optional short title for the interaction")
    observe.add_argument("--source-id", default="", help="Optional fixed source id")
    observe.add_argument("--report", default="", help="Optional path to write the latest feedback text")
    observe.set_defaults(func=cmd_observe)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
