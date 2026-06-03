# V5 Tested Approval Workflow

Version 5 hardens the self-evolving skill prototype with regression tests, apply read-back verification, and a chat-friendly approval summary.

## Goals

- Keep extraction and apply separated.
- Prove safety behavior with automated tests before changing implementation.
- Verify append-style apply by reading the target file back after `--apply`.
- Produce a short approval summary that can be pasted into chat for user review.

## Test Suite

Run from the skill root:

```bash
cd /opt/dev/self-evolving-skills
pytest -q
```

Covered behaviors:

- Secret-like assignments are redacted.
- User corrections become memory candidates.
- Skill gaps become skill patch candidates.
- Self-evolution requests become new skill candidates.
- Transient IDs are ignored or kept low-confidence.
- Structural compaction/tool noise is skipped.
- `apply_decisions.py` rejects absolute paths and parent traversal.
- Dry-run does not write files.
- Real append writes a marker and `verify_append()` reads it back.
- Secret-looking apply content is rejected.
- Review triage rejects identity noise, requires confirmation for external side effects, and summarizes approval buckets.

## Apply Verification

`apply_decisions.py --apply` now verifies append operations by checking:

- the target file exists;
- the decision marker exists;
- the expected content exists.

Example output includes:

```text
MODE APPLY
PLANNED
- evo-123: append ... chars -> references/example.md
- evo-123: verify_append=True reason=ok
```

## Approval Summary

`review_decisions.py` supports:

```bash
python3 scripts/review_decisions.py reports/evolution-decisions.yaml \
  --output reports/decision-review.md \
  --annotated-output reports/evolution-decisions.reviewed.yaml \
  --approval-summary-output reports/approval-summary.md
```

The approval summary groups candidates as:

- 建议批准
- 需要确认
- 需要人工审查
- 建议拒绝

It remains advisory only. It does not change decision statuses, patch skills, write memory, create cron jobs, or call external APIs.

## Promotion Boundary

V5 still does not install the skill into `~/.hermes/skills/` and does not create autonomous cron jobs. Promotion requires explicit user confirmation.
