#!/usr/bin/env python3
"""Read recent Hermes sessions and generate a self-evolution candidate report.

Default behavior is read-only: it opens ~/.hermes/state.db in SQLite immutable
mode when possible, extracts candidate signals, redacts sensitive strings, and
prints a Markdown report. It never modifies memory, skills, sessions, or cron.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time

sys.dont_write_bytecode = True
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make sibling import work when executed as a script.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from extract_candidates import extract, redact  # noqa: E402

DEFAULT_DB = Path.home() / ".hermes" / "state.db"
DEFAULT_REPORT_DIR = Path("reports")
ROLE_ALLOWLIST = {"user", "assistant", "tool"}


def open_readonly_db(path: Path) -> sqlite3.Connection:
    """Open SQLite DB read-only; prefer immutable mode to avoid side effects."""
    uri = f"file:{path}?mode=ro&immutable=1"
    try:
        con = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def ts_to_iso(ts: float | int | None) -> str:
    if not ts:
        return "unknown"
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()


def short(text: str | None, limit: int = 320) -> str:
    text = redact(text or "").replace("\r", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def load_recent_messages(con: sqlite3.Connection, hours: int, limit_messages: int, roles: set[str]) -> list[sqlite3.Row]:
    since = time.time() - hours * 3600
    placeholders = ",".join("?" for _ in roles)
    sql = f"""
        SELECT
          m.id AS message_id,
          m.session_id,
          m.role,
          m.content,
          m.tool_name,
          m.timestamp,
          s.title,
          s.source
        FROM messages m
        JOIN sessions s ON s.id = m.session_id
        WHERE m.timestamp >= ?
          AND m.active = 1
          AND m.role IN ({placeholders})
          AND COALESCE(m.content, '') != ''
        ORDER BY m.timestamp DESC, m.id DESC
        LIMIT ?
    """
    rows = con.execute(sql, [since, *sorted(roles), limit_messages]).fetchall()
    return list(reversed(rows))


def enrich_candidates(rows: list[sqlite3.Row], max_candidates: int = 80) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        content = row["content"] or ""
        # Extract line-level candidates, then add session metadata.
        for candidate in extract(content, role=str(row["role"]), source="session_db"):
            summary = candidate.get("summary", "")
            normalized_summary = " ".join(summary.lower().split())[:220]
            key = (candidate.get("candidate_type", ""), normalized_summary)
            if key in seen:
                continue
            seen.add(key)
            candidate = dict(candidate)
            candidate["session"] = {
                "id": row["session_id"],
                "title": row["title"] or "untitled",
                "source": row["source"],
                "message_id": row["message_id"],
                "role": row["role"],
                "timestamp": ts_to_iso(row["timestamp"]),
            }
            candidate["evidence"]["details"] = short(candidate["evidence"].get("details", ""), 500)
            enriched.append(candidate)
    enriched.sort(key=lambda c: (c.get("confidence_score", 0), c.get("value_score", 0), -c.get("risk_score", 0)), reverse=True)
    return enriched[:max_candidates]


def markdown_report(candidates: list[dict[str, Any]], rows: list[sqlite3.Row], hours: int) -> str:
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in candidates:
        by_type[c.get("candidate_type", "unknown")].append(c)

    session_ids = sorted({str(r["session_id"]) for r in rows})
    role_counts = Counter(str(r["role"]) for r in rows)
    lines: list[str] = []
    lines.append("# Skill Evolution Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Scope: last {hours} hours")
    lines.append(f"Sources reviewed: {len(rows)} messages across {len(session_ids)} sessions")
    lines.append(f"Roles: {dict(role_counts)}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    if candidates:
        confidence_counts = Counter(str(c.get("confidence", "unknown")) for c in candidates)
        recommendation_counts = Counter(str(c.get("recommendation", "unknown")) for c in candidates)
        lines.append(f"Found {len(candidates)} ranked candidate signals. All items are proposals only; no memory or skill files were modified.")
        lines.append(f"Confidence: {dict(confidence_counts)}")
        lines.append(f"Recommendations: {dict(recommendation_counts)}")
    else:
        lines.append("No candidate signals found. No action recommended.")
    lines.append("")

    section_order = [
        ("memory", "## Memory Candidates"),
        ("skill_patch", "## Skill Patch Candidates"),
        ("new_skill", "## New Skill Candidates"),
        ("project_doc", "## Project Documentation Candidates"),
        ("ignore", "## Ignored Items"),
    ]
    for candidate_type, title in section_order:
        lines.append(title)
        lines.append("")
        items = by_type.get(candidate_type, [])
        if not items:
            lines.append("_None._")
            lines.append("")
            continue
        for idx, c in enumerate(items, 1):
            session = c.get("session", {})
            signals = ", ".join(c.get("evidence", {}).get("signals", []))
            lines.append(f"### {idx}. {short(c.get('summary', ''), 180)}")
            lines.append(f"- Evidence: {short(c.get('evidence', {}).get('details', ''), 300)}")
            lines.append(f"- Signals: {signals or 'unknown'}")
            lines.append(f"- Target hint: `{c.get('target') or 'unmapped'}`")
            lines.append(f"- Scores: value={c.get('value_score')}, risk={c.get('risk_score')}, confidence={c.get('confidence')} ({c.get('confidence_score')})")
            lines.append(f"- Recommendation: {c.get('recommendation')} / confirmation={c.get('confirmation', 'recommended')}")
            lines.append(f"- Session: `{session.get('id')}` / {short(session.get('title', ''), 80)}")
            lines.append(f"- Message: role=`{session.get('role')}`, id=`{session.get('message_id')}`, time=`{session.get('timestamp')}`")
            lines.append("")
    lines.append("## Recommended Next Actions")
    lines.append("")
    if by_type.get("skill_patch"):
        lines.append("1. Review skill patch candidates manually and map each to an existing target skill before applying.")
    if by_type.get("memory"):
        lines.append("2. Save only durable user preferences/environment facts to memory; ignore task progress.")
    if not candidates:
        lines.append("1. No action needed.")
    lines.append("")
    lines.append("## Safety Notes")
    lines.append("")
    lines.append("- This report was generated in read-only mode from the Hermes session database.")
    lines.append("- Candidate text is passed through a redactor; still review before publishing or saving.")
    lines.append("- Applying any candidate is a separate explicit step.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate self-evolving skill candidates from recent Hermes sessions.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Path to Hermes state.db")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours")
    parser.add_argument("--limit-messages", type=int, default=1000, help="Max recent messages to scan")
    parser.add_argument("--roles", default="user", help="Comma-separated roles to scan; default is user-only to reduce assistant/tool false positives")
    parser.add_argument("--max-candidates", type=int, default=25, help="Maximum candidates to include after de-duplication/ranking")
    parser.add_argument("--min-confidence", type=int, default=30, help="Drop candidates below this confidence score")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    parser.add_argument("--output", type=Path, help="Optional output report path")
    args = parser.parse_args()

    roles = {r.strip() for r in args.roles.split(",") if r.strip()}
    invalid = roles - ROLE_ALLOWLIST
    if invalid:
        parser.error(f"invalid roles: {sorted(invalid)}")
    if not args.db.exists():
        parser.error(f"database not found: {args.db}")

    con = open_readonly_db(args.db)
    rows = load_recent_messages(con, args.hours, args.limit_messages, roles)
    candidates = enrich_candidates(rows, max_candidates=args.max_candidates)
    candidates = [c for c in candidates if int(c.get("confidence_score", 0)) >= args.min_confidence]

    if args.json:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope_hours": args.hours,
            "messages_reviewed": len(rows),
            "sessions_reviewed": len({r["session_id"] for r in rows}),
            "candidates": candidates,
        }
        output = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        output = markdown_report(candidates, rows, args.hours)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
        print(f"WROTE {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
