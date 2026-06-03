#!/usr/bin/env python3
"""Heuristic extractor for self-evolving skill candidates.

This script is conservative by design. It turns plain text into proposal
candidates for a human/agent review step. It does not modify memory or skills.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|authorization|token|password|secret)\s*[:=]\s*\S+"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)(ghp|github_pat|sk-[A-Za-z0-9])[A-Za-z0-9_\-]{16,}"),
]

TRANSIENT_PATTERNS = [
    re.compile(r"(?i)\b(feedid|feed id|issue #|pr #|pull request|commit sha|job_id|event id)\b"),
    re.compile(r"\b[0-9A-F]{32,}\b"),  # fingerprints / opaque ids: usually not skill material
]

SKIP_PATTERNS = [
    re.compile(r"^\s*(CONTEXT COMPACTION|## Active Task|## Completed Actions|## Remaining Work)\b"),
    re.compile(r"^\s*\d+\.\s+.*\[(tool|tool:|final response|tool output)", re.I),
    re.compile(r"^\s*\d+\|"),  # read_file numbered lines
    re.compile(r"^\s*[{}\[\]]\s*$"),
    re.compile(r"^\s*[-*]\s*\*\*(Name|Pronouns|Timezone|Core Truths|Boundaries)\b", re.I),
    re.compile(r"^\s*(---|_.*_$)"),
]

SIGNAL_DEFS = [
    ("explicit_remember", re.compile(r"(记住|remember this|保存为经验|沉淀|以后都|长期上下文)", re.I), 34),
    ("user_correction", re.compile(r"(不是这样|不对|应该是|以后不要|以后别|别再|不要再|actually|instead of|not .+ but)", re.I), 32),
    ("skill_gap", re.compile(r"(skill|技能).*(过时|缺少|错误|不兼容|stale|missing|wrong|outdated|pitfall|坑)", re.I), 35),
    ("workflow_request", re.compile(r"(构建|落地|实现|自动化|workflow|流程|闭环|cron|扫描).*(skill|技能|经验|会话|session|记忆|memory)", re.I), 26),
    ("verified_fix", re.compile(r"(验证通过|测试通过|成功修复|真实跑过|exit_code.?0|fixed|works|validated)", re.I), 22),
    ("failure_then_fix", re.compile(r"(失败|报错|timeout|Traceback|Exception|error).*(后|然后|改为|修正|重试|成功|通过)", re.I), 24),
    ("preference", re.compile(r"(偏好|喜欢|不喜欢|倾向|prefer|expects?|要求).*(中文|简洁|直接|确认|测试|commit|发布)", re.I), 24),
]

TARGET_HINTS = [
    ("hermes-agent-skill-authoring", re.compile(r"(skill|技能).*(开发|author|frontmatter|/opt/dev|SKILL\.md)", re.I)),
    ("self-evolving-skills", re.compile(r"(自进化|evolving|会话.*技能|skill.*进化|scan_recent_sessions)", re.I)),
    ("github-auth", re.compile(r"(gh auth|github_token|gpg|ssh key|签名)", re.I)),
    ("meyo-community-onboarding", re.compile(r"(Meyo|觅游|干活虾|behaviors/task_executed|task_executed)", re.I)),
]


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda m: re.split(r"[:=]", m.group(0), maxsplit=1)[0] + "=[REDACTED]", text)
    return text


def normalize(text: str) -> str:
    text = redact(text or "")
    text = text.replace("\r", " ").replace("\t", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def skip_reason(line: str, role: str = "user") -> str | None:
    stripped = line.strip()
    if not stripped or len(stripped) < 8:
        return "too_short"
    if len(stripped) > 1200:
        return "too_long_line"
    if any(p.search(stripped) for p in SKIP_PATTERNS):
        return "structural_or_summary_noise"
    if role == "tool" and not re.search(r"(skill|技能|验证通过|exit_code.?0|Traceback|Exception|error)", stripped, re.I):
        return "tool_noise"
    if stripped.count("\\n") > 4:
        return "multi_line_blob"
    return None


def classify(line: str, signals: list[str]) -> str:
    lowered = line.lower()
    if any(p.search(line) for p in TRANSIENT_PATTERNS):
        return "ignore"
    if "skill_gap" in signals or "skill" in lowered or "技能" in line:
        if "自进化" in line or "new skill" in lowered or "构建" in line:
            return "new_skill"
        return "skill_patch"
    if any(s in signals for s in ["explicit_remember", "user_correction", "preference"]):
        return "memory"
    if any(s in signals for s in ["verified_fix", "failure_then_fix", "workflow_request"]):
        return "project_doc"
    return "ignore"


def target_hint(line: str) -> str | None:
    for name, pattern in TARGET_HINTS:
        if pattern.search(line):
            return name
    return None


def score_candidate(line: str, signals: list[str], candidate_type: str, role: str) -> dict[str, Any]:
    value = sum(weight for name, pattern, weight in SIGNAL_DEFS if name in signals)
    if role == "user":
        value += 10
    if candidate_type in {"skill_patch", "new_skill"}:
        value += 8
    if "验证" in line or "tested" in line.lower() or "exit_code" in line.lower():
        value += 8

    risk = 0
    if any(p.search(line) for p in SECRET_PATTERNS):
        risk += 45
    if any(p.search(line) for p in TRANSIENT_PATTERNS):
        risk += 35
    if re.search(r"(发布|发送|外部|token|credential|凭证|删除|rm -rf|auth)", line, re.I):
        risk += 18
    if len(line) > 500:
        risk += 10

    confidence_raw = max(0, min(100, value - risk // 2))
    if candidate_type == "ignore":
        confidence_raw = min(confidence_raw, 25)
    confidence = "high" if confidence_raw >= 65 else "medium" if confidence_raw >= 40 else "low"
    if candidate_type in {"skill_patch", "new_skill"} or risk >= 30:
        confirmation = "required"
    elif confidence == "high" and candidate_type == "memory":
        confirmation = "recommended"
    else:
        confirmation = "review"
    recommendation = "apply_after_review" if confidence == "high" and risk < 25 else "ask" if confirmation == "required" else "review" if candidate_type != "ignore" else "ignore"
    return {
        "value_score": value,
        "risk_score": risk,
        "confidence_score": confidence_raw,
        "confidence": confidence,
        "confirmation": confirmation,
        "recommendation": recommendation,
    }


def extract(text: str, *, role: str = "user", source: str = "text") -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for raw in text.splitlines():
        reason = skip_reason(raw, role=role)
        if reason:
            continue
        line = normalize(raw)
        matched = [name for name, pattern, _weight in SIGNAL_DEFS if pattern.search(line)]
        if not matched:
            continue
        candidate_type = classify(line, matched)
        scoring = score_candidate(line, matched, candidate_type, role)
        # Low-confidence ignored/transient noise does not help reports.
        if candidate_type == "ignore" and scoring["confidence_score"] < 20 and "explicit_remember" not in matched:
            continue
        candidate = {
            "candidate_type": candidate_type,
            "target": target_hint(line),
            "summary": line[:240],
            "evidence": {"source": source, "signals": matched, "details": line[:500]},
            "status": "proposed",
            **scoring,
        }
        candidates.append(candidate)
    return candidates


def main() -> int:
    if len(sys.argv) > 1:
        text = "\n".join(Path(p).read_text(encoding="utf-8", errors="replace") for p in sys.argv[1:])
    else:
        text = sys.stdin.read()
    print(json.dumps({"candidates": extract(text)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
