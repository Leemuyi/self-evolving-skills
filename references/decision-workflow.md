# Decision Workflow

Version 3 adds a review queue between candidate reports and any file changes.

## Flow

```bash
cd /opt/dev/self-evolving-skills

# 1. Generate ranked candidates as JSON
python3 scripts/scan_recent_sessions.py \
  --hours 48 \
  --limit-messages 800 \
  --max-candidates 25 \
  --min-confidence 30 \
  --json \
  --output reports/candidates-v3.json

# 2. Convert candidates into a reviewable decision file
python3 scripts/generate_decisions.py \
  reports/candidates-v3.json \
  --output reports/evolution-decisions.yaml

# 3. Review/edit reports/evolution-decisions.yaml
#    Keep unwanted items rejected/pending.
#    For safe local append, set:
#      status: approved
#      apply.mode: append_markdown
#      apply.path: references/<file>.md
#      apply.content: |
#        ...redacted markdown...

# 4. Dry-run application
python3 scripts/apply_decisions.py reports/evolution-decisions.yaml

# 5. Apply only after review
python3 scripts/apply_decisions.py reports/evolution-decisions.yaml --apply
```

## Decision Status

- `pending`: extracted but not reviewed.
- `approved`: may be applied if `apply.mode` is supported.
- `rejected`: intentionally ignored.
- `applied`: already applied manually or by script.

## Supported Apply Mode

For safety, v3 only supports:

```yaml
apply:
  mode: append_markdown
  path: references/some-file.md
  content: |
    ## New note
    Redacted, reviewable Markdown.
```

Allowed paths are constrained to this dev skill tree:

- `SKILL.md`
- `references/*`
- `templates/*`
- `reports/*`

The script rejects absolute paths, `..`, unsupported extensions, and secret-looking content.

## Non-goals

v3 does not:

- write Hermes memory;
- call `skill_manage`;
- install the skill into `~/.hermes/skills/`;
- create cron jobs;
- publish/send external content;
- apply arbitrary diffs.

Those require a later explicit promotion step.
