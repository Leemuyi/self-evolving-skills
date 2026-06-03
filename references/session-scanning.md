# Session Scanning

`scan_recent_sessions.py` is the first closed-loop helper for this development skill.

## Purpose

Generate a proposal-only evolution report from recent Hermes session history.

It is intentionally read-only:

- Opens `~/.hermes/state.db` with SQLite `mode=ro&immutable=1` when available.
- Reads `sessions` and `messages` tables.
- Scans only selected roles. Default is `user` to reduce false positives from assistant summaries and tool output; pass `--roles user,assistant,tool` for broader review.
- Runs text through the redactor in `extract_candidates.py`.
- Filters structural noise such as compaction headings, `read_file` line numbers, tool-summary bullets, and identity-file snippets.
- Scores each candidate with `value_score`, `risk_score`, `confidence_score`, `confidence`, and `recommendation`.
- De-duplicates candidates by normalized summary, ranks by confidence/value/risk, and caps output with `--max-candidates`.
- Drops low-confidence candidates with `--min-confidence`.
- Writes only the report path explicitly passed by `--output`.
- Does not call `memory`, `skill_manage`, `cronjob`, or external APIs.

## Example

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/scan_recent_sessions.py --hours 24 --max-candidates 25 --min-confidence 30 --output reports/evolution-report.md
```

JSON mode:

```bash
python3 scripts/scan_recent_sessions.py --hours 6 --json
```

## Review Flow

1. Read the generated report.
2. Discard weak or short-lived items.
3. Map each `skill_patch` candidate to a concrete target skill.
4. Ask for confirmation when required by `references/safety-policy.md`.
5. Apply patches separately and verify with `validate_skill.py` or `skill_view`.

## Known Limitations

- The extractor is heuristic and conservative; it is meant to feed an agent review, not decide autonomously.
- It can produce false positives from quoted text or summarized content.
- Redaction is best-effort; review before posting or saving any report externally.
- It does not yet cluster duplicate candidates across sessions beyond exact summary/session matches.
