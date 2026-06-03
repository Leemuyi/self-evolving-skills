#!/usr/bin/env python3
"""Review self-evolution decision YAML and produce triage recommendations.

This is an advisory tool. It does not approve, reject, apply, patch memory, or
call external APIs. It reads a decisions YAML file and writes either a Markdown
review report or an annotated copy of the YAML with review suggestions.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"PyYAML is required: {exc}")

TRANSIENT_RE = re.compile(r"(?i)\b(feedid|feed id|event id|job_id|commit sha|pr #|issue #|已发布|发布成功|完成了|done)\b")
SECRET_RE = re.compile(r"(?i)(api[_-]?key|authorization|bearer|token|password|secret|credential|凭证|私钥)")
NOISE_RE = re.compile(r"(?i)(CONTEXT COMPACTION|Completed Actions|Remaining Work|tool:|\[tool|read_file|write_file|terminal|final response)")
IDENTITY_RE = re.compile(r"(记住你只是客人|Core Truths|Boundaries|SOUL\.md|USER\.md|MEMORY\.md)", re.I)
STRONG_REUSE_RE = re.compile(r"(skill|技能|自进化|流程|闭环|验证通过|exit_code|失败.*成功|过时|缺少|坑|pitfall|workflow)", re.I)
EXTERNAL_SIDE_EFFECT_RE = re.compile(r"(发布|发送|外部|\bauth\b|github_token|gpg|ssh key|Meyo|觅游|cron|gateway|配置)", re.I)


def load(path: Path) -> dict[str, Any]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("decisions"), list):
        raise SystemExit("Decision file must contain a decisions list")
    return doc


def text_of(decision: dict[str, Any]) -> str:
    parts = [
        str(decision.get("summary", "")),
        str((decision.get("evidence") or {}).get("details", "")),
        str(decision.get("target", "")),
        str(decision.get("candidate_type", "")),
    ]
    return "\n".join(parts)


def review_one(decision: dict[str, Any]) -> dict[str, Any]:
    txt = text_of(decision)
    ctype = decision.get("candidate_type", "unknown")
    target = decision.get("target") or "unmapped"
    scores = decision.get("scores") or {}
    confidence_score = int(scores.get("confidence_score") or 0)
    risk = int(scores.get("risk") or 0)
    value = int(scores.get("value") or 0)

    reasons: list[str] = []
    bucket = "review"
    suggested_status = "pending"

    if SECRET_RE.search(txt):
        bucket = "needs_confirmation"
        reasons.append("contains credential/auth/security terms; require explicit review and redaction")
    if TRANSIENT_RE.search(txt):
        bucket = "reject"
        suggested_status = "rejected"
        reasons.append("looks transient or task-status-like")
    if NOISE_RE.search(txt):
        bucket = "reject"
        suggested_status = "rejected"
        reasons.append("looks like tool/compaction/session-summary noise")
    if IDENTITY_RE.search(txt):
        bucket = "reject"
        suggested_status = "rejected"
        reasons.append("identity/persona file content is already captured elsewhere")

    if bucket not in {"reject"}:
        if EXTERNAL_SIDE_EFFECT_RE.search(txt):
            bucket = "needs_confirmation"
            reasons.append("could affect external workflow or skill behavior; ask before applying")
        elif ctype in {"skill_patch", "new_skill"} and target != "unmapped" and confidence_score >= 40 and risk <= 20:
            bucket = "suggest_approve"
            reasons.append("mapped reusable skill candidate with acceptable confidence/risk")
        elif ctype == "memory" and confidence_score >= 55 and risk <= 10 and not EXTERNAL_SIDE_EFFECT_RE.search(txt):
            bucket = "suggest_approve"
            reasons.append("durable memory-looking preference with low risk")
        elif EXTERNAL_SIDE_EFFECT_RE.search(txt) or ctype in {"skill_patch", "new_skill"}:
            bucket = "needs_confirmation"
            reasons.append("could affect external workflow or skill behavior; ask before applying")
        elif confidence_score < 40 or value < 40:
            bucket = "reject"
            suggested_status = "rejected"
            reasons.append("low confidence/value after v2 scoring")
        elif STRONG_REUSE_RE.search(txt):
            bucket = "review"
            reasons.append("possibly reusable but target/action needs human mapping")
        else:
            bucket = "reject"
            suggested_status = "rejected"
            reasons.append("weak reuse signal")

    if not reasons:
        reasons.append("default review")

    return {
        "bucket": bucket,
        "suggested_status": suggested_status,
        "reasons": reasons,
        "confidence_score": confidence_score,
        "risk_score": risk,
        "value_score": value,
    }


def markdown_report(doc: dict[str, Any], reviews: dict[str, dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    decisions = doc.get("decisions", [])
    by_id = {str(d.get("id")): d for d in decisions}
    for did, review in reviews.items():
        grouped[review["bucket"]].append(by_id[did])
    counts = Counter(r["bucket"] for r in reviews.values())

    lines: list[str] = []
    lines.append("# Decision Review Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Source: {doc.get('source', 'unknown')}")
    lines.append(f"Decisions reviewed: {len(decisions)}")
    lines.append(f"Buckets: {dict(counts)}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("This report is advisory only. It does not change decision statuses or apply changes.")
    lines.append("")

    order = [
        ("suggest_approve", "## Suggested Approvals"),
        ("needs_confirmation", "## Needs Confirmation"),
        ("review", "## Manual Review"),
        ("reject", "## Suggested Rejections / Noise"),
    ]
    for bucket, title in order:
        lines.append(title)
        lines.append("")
        items = grouped.get(bucket, [])
        if not items:
            lines.append("_None._")
            lines.append("")
            continue
        for d in items:
            did = str(d.get("id"))
            r = reviews[did]
            lines.append(f"### {did}")
            lines.append(f"- Type: `{d.get('candidate_type')}` target=`{d.get('target')}`")
            lines.append(f"- Summary: {str(d.get('summary', ''))[:240]}")
            lines.append(f"- Scores: value={r['value_score']} risk={r['risk_score']} confidence={r['confidence_score']}")
            lines.append(f"- Suggested status: `{r['suggested_status']}`")
            lines.append("- Reasons:")
            for reason in r["reasons"]:
                lines.append(f"  - {reason}")
            lines.append("")

    lines.append("## Next Step")
    lines.append("")
    lines.append("Edit `reports/evolution-decisions.yaml` manually: set only trusted items to `status: approved` and fill `apply.mode/path/content`, then run `apply_decisions.py` first without `--apply`.")
    lines.append("")
    return "\n".join(lines)


def approval_summary(doc: dict[str, Any], reviews: dict[str, dict[str, Any]]) -> str:
    """Generate a chat-friendly approval summary from review buckets."""
    decisions = doc.get("decisions", [])
    by_id = {str(d.get("id")): d for d in decisions}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for did, review in reviews.items():
        item = dict(by_id.get(did, {}))
        item["_review"] = review
        groups[review.get("bucket", "review")].append(item)

    labels = [
        ("suggest_approve", "## 建议批准"),
        ("needs_confirmation", "## 需要确认"),
        ("review", "## 需要人工审查"),
        ("reject", "## 建议拒绝"),
    ]
    lines = ["# Self-Evolving Skills Approval Summary", ""]
    for bucket, title in labels:
        lines.append(title)
        lines.append("")
        items = groups.get(bucket, [])
        if not items:
            lines.append("_无。_")
            lines.append("")
            continue
        for idx, d in enumerate(items, 1):
            review = d.get("_review", {})
            reasons = "; ".join(review.get("reasons", []))
            lines.append(f"{idx}. `{d.get('id')}` → `{d.get('candidate_type')}` / `{d.get('target')}`")
            lines.append(f"   - 摘要：{str(d.get('summary', ''))[:180]}")
            lines.append(f"   - 原因：{reasons or 'default review'}")
        lines.append("")
    lines.append("下一步：只把可信条目改为 `status: approved`，补全 `apply.mode/path/content`，先 dry-run 再 apply。")
    return "\n".join(lines)


def annotate(doc: dict[str, Any], reviews: dict[str, dict[str, Any]]) -> dict[str, Any]:
    new_doc = dict(doc)
    annotated = []
    for decision in doc.get("decisions", []):
        d = dict(decision)
        did = str(d.get("id"))
        review = reviews.get(did, {})
        existing_review = dict(d.get("review") or {})
        existing_review["auto_review"] = {
            "bucket": review.get("bucket"),
            "suggested_status": review.get("suggested_status"),
            "reasons": review.get("reasons", []),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        d["review"] = existing_review
        annotated.append(d)
    new_doc["decisions"] = annotated
    new_doc["auto_review_generated_at"] = datetime.now(timezone.utc).isoformat()
    return new_doc


def main() -> int:
    parser = argparse.ArgumentParser(description="Review self-evolving skill decisions and produce advisory triage.")
    parser.add_argument("decisions", type=Path, help="Decision YAML from generate_decisions.py")
    parser.add_argument("--output", type=Path, default=Path("reports/decision-review.md"), help="Markdown review report path")
    parser.add_argument("--annotated-output", type=Path, help="Optional annotated YAML copy; does not modify input")
    parser.add_argument("--approval-summary-output", type=Path, help="Optional chat-friendly approval summary path")
    args = parser.parse_args()

    doc = load(args.decisions)
    reviews = {str(d.get("id")): review_one(d) for d in doc.get("decisions", [])}

    report = markdown_report(doc, reviews)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report + "\n", encoding="utf-8")
    print(f"WROTE {args.output}")

    if args.annotated_output:
        annotated = annotate(doc, reviews)
        args.annotated_output.parent.mkdir(parents=True, exist_ok=True)
        args.annotated_output.write_text(yaml.safe_dump(annotated, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"WROTE {args.annotated_output}")

    if args.approval_summary_output:
        summary = approval_summary(doc, reviews)
        args.approval_summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.approval_summary_output.write_text(summary + "\n", encoding="utf-8")
        print(f"WROTE {args.approval_summary_output}")

    counts = Counter(r["bucket"] for r in reviews.values())
    print("BUCKETS", dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
