#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Dict, List

from memoryloop_core import (
    CandidateMemory,
    Source,
    audit_candidates,
    build_memory_pack,
    extract_candidates,
    load_input,
    render_generic_response,
    render_memory_aware_response,
)


def render_report(
    input_path: Path,
    challenge_prompt: str,
    sources: List[Source],
    candidates: Dict[str, CandidateMemory],
    memory_pack: Dict[str, object],
) -> str:
    lines: List[str] = []
    lines.append("# OpenClaw MemoryLoop Demo Report")
    lines.append("")
    lines.append(f"- Input: `{input_path}`")
    lines.append(f"- Sources: `{len(sources)}`")
    lines.append(f"- Candidate memories: `{len(candidates)}`")
    lines.append(f"- Promoted memories: `{len(memory_pack['promoted_memories'])}`")
    lines.append("")
    lines.append("## Challenge Prompt")
    lines.append("")
    lines.append(challenge_prompt)
    lines.append("")
    lines.append("## Candidate Memories")
    lines.append("")
    for candidate in candidates.values():
        lines.append(f"### {candidate.statement}")
        lines.append("")
        lines.append(f"- Key: `{candidate.key}`")
        lines.append(f"- Category: `{candidate.category}`")
        lines.append(f"- Confidence: `{candidate.confidence}`")
        lines.append(f"- Decision: `{candidate.decision}`")
        lines.append(f"- Reason: {candidate.reason}")
        for evidence in candidate.evidence:
            lines.append(
                f"- Evidence: `{evidence['source_type']}` / `{evidence['title']}` / {evidence['snippet']}"
            )
        lines.append("")
    lines.append("## Promoted Role Memory Pack")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(memory_pack, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## Generic Claw Response")
    lines.append("")
    lines.append(render_generic_response(challenge_prompt))
    lines.append("")
    lines.append("## Memory-Aware Claw Response")
    lines.append("")
    lines.append(render_memory_aware_response(memory_pack, challenge_prompt))
    lines.append("")
    return "\n".join(lines)


def write_outputs(output_path: Path, report: str, memory_pack: Dict[str, object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    json_path = output_path.with_suffix(".json")
    json_path.write_text(json.dumps(memory_pack, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a deterministic OpenClaw memory loop demo.")
    parser.add_argument("--input", required=True, help="Path to demo sources JSON")
    parser.add_argument("--output", required=True, help="Path to report Markdown output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    payload = load_input(input_path)
    challenge_prompt = str(payload["challenge_prompt"])
    sources = [Source(**item) for item in payload["sources"]]

    candidates = extract_candidates(sources)
    audited = audit_candidates(candidates)
    memory_pack = build_memory_pack(audited)
    report = render_report(input_path, challenge_prompt, sources, audited, memory_pack)
    write_outputs(output_path, report, memory_pack)

    print(f"REPORT={output_path}")
    print(f"MEMORY_PACK={output_path.with_suffix('.json')}")
    print(f"PROMOTED={len(memory_pack['promoted_memories'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
