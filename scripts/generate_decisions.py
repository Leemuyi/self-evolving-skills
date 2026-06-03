#!/usr/bin/env python3
"""Generate a reviewable decisions YAML from scan_recent_sessions JSON output.

This script is proposal-only. It does not apply changes. Typical flow:

  python3 scripts/scan_recent_sessions.py --hours 48 --json > reports/candidates-v3.json
  python3 scripts/generate_decisions.py reports/candidates-v3.json --output reports/evolution-decisions.yaml

The generated YAML defaults every item to status=pending and action=none.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"PyYAML is required: {exc}")

ACTION_BY_TYPE = {
    "memory": "propose_memory",
    "skill_patch": "propose_skill_patch",
    "new_skill": "propose_new_skill",
    "project_doc": "propose_project_doc",
    "ignore": "none",
}


def slugify(text: str, max_len: int = 32) -> str:
    text = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text).strip("-").lower()
    return text[:max_len].strip("-") or "candidate"


def load_candidates(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "candidates" not in payload:
        raise SystemExit("Input must be JSON from scan_recent_sessions.py --json")
    return payload


def proposal_for(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    candidate_type = candidate.get("candidate_type", "unknown")
    summary = str(candidate.get("summary", ""))
    target_hint = candidate.get("target") or "unmapped"
    confidence = candidate.get("confidence", "unknown")
    recommendation = candidate.get("recommendation", "review")
    status = "pending"
    if candidate_type == "ignore" or recommendation == "ignore":
        status = "rejected"

    return {
        "id": f"evo-{index:03d}-{slugify(candidate_type + '-' + summary)}",
        "status": status,  # pending | approved | rejected | applied
        "candidate_type": candidate_type,
        "action": ACTION_BY_TYPE.get(candidate_type, "none"),
        "target": target_hint,
        "summary": summary,
        "evidence": candidate.get("evidence", {}),
        "scores": {
            "value": candidate.get("value_score"),
            "risk": candidate.get("risk_score"),
            "confidence_score": candidate.get("confidence_score"),
            "confidence": confidence,
        },
        "recommendation": recommendation,
        "confirmation": candidate.get("confirmation", "review"),
        "session": candidate.get("session", {}),
        "review": {
            "decision_reason": "",
            "reviewer": "",
            "reviewed_at": "",
        },
        "apply": {
            "mode": "manual",  # manual | append_markdown
            "path": "",        # required for append_markdown; restricted by apply_decisions.py
            "section": "",     # optional heading/context for humans
            "content": "",     # required for append_markdown
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate self-evolution decision YAML from candidate JSON.")
    parser.add_argument("input", type=Path, help="JSON file from scan_recent_sessions.py --json")
    parser.add_argument("--output", type=Path, default=Path("reports/evolution-decisions.yaml"))
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    payload = load_candidates(args.input)
    candidates = payload.get("candidates", [])[: args.limit]
    doc = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(args.input),
        "policy": {
            "default_status": "pending",
            "apply_requires_status": "approved",
            "default_apply_mode": "dry-run",
            "notes": [
                "This file is a human/agent review queue, not an instruction to auto-apply.",
                "Do not include secrets or unredacted private content in apply.content.",
                "apply_decisions.py only supports constrained local file appends unless explicitly extended.",
            ],
        },
        "decisions": [proposal_for(c, i + 1) for i, c in enumerate(candidates)],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"WROTE {args.output} decisions={len(doc['decisions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
