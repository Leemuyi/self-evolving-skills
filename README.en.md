# Self-Evolving Skills

`self-evolving-skills` is a prototype Hermes skill for **safely turning real conversation experience into reviewable skill-evolution proposals**. It does not directly “rewrite itself”. Its core design is to split session evidence into candidates, generate reviewable decisions, triage them automatically, and only perform constrained local append operations after explicit approval.

```text
session evidence
  -> candidate extraction
  -> decision YAML
  -> advisory review
  -> explicit approval
  -> constrained dry-run/apply
  -> read-back verification
```

This repository is a development tree. The default local path is:

```text
/opt/dev/self-evolving-skills
```

> Safety posture: by default it only generates reports and proposals. It does not write memory, install skills, create cron jobs, call external APIs, or publish/send content.

中文版本：[`README.zh-CN.md`](README.zh-CN.md)

---

## Core Capabilities

| Capability | Script / File | Description |
|---|---|---|
| Skill definition | `SKILL.md` | Defines the self-evolution workflow, confirmation policy, usage boundaries, and one-shot recipes. |
| Candidate extraction | `scripts/extract_candidates.py` | Extracts candidate lines from text and detects signals such as user corrections, skill gaps, verified fixes, and preferences. |
| Session scanning | `scripts/scan_recent_sessions.py` | Read-only scan of Hermes `state.db`, producing Markdown or JSON candidate reports. |
| Decision generation | `scripts/generate_decisions.py` | Converts candidate JSON into a review queue YAML with default `pending` status. |
| Decision review | `scripts/review_decisions.py` | Performs advisory triage over decision YAML and outputs a review report, annotated YAML, and a Chinese approval summary. |
| Constrained apply | `scripts/apply_decisions.py` | Applies only `approved + append_markdown` decisions as constrained local appends; dry-run by default. |
| Skill validation | `scripts/validate_skill.py` | Validates `SKILL.md` frontmatter, body, and recommended sections. |
| Reference rules | `references/*.md` | Classification rules, safety policy, scoring model, session scanning workflow, and approval workflow. |
| Templates | `templates/*.md` | Templates for evolution reports, skill patch proposals, and new skill proposals. |
| Regression tests | `tests/*.py` | Covers redaction, classification, review buckets, path boundaries, dry-run/apply behavior, and verification. |

---

## When to Use

Use this project when:

- A user explicitly says “remember this workflow”, “turn this into a skill”, or “do not do this again”.
- A complex task contains a reusable failure → fix → verification chain.
- An existing skill exposes stale commands, missing prerequisites, or missing pitfall notes.
- Similar debugging, deployment, publishing, or review workflows repeat across recent sessions.
- You need to decide whether an item belongs in memory, a skill patch, a new skill proposal, project docs, or nowhere.

Do not use it to:

- Store short-lived progress, PR/issue/feed/job IDs, commit SHAs, or one-off outputs.
- Collect or write tokens, API keys, cookies, private keys, Authorization headers, or full private third-party messages.
- Modify Hermes configuration, security policy, cron jobs, gateway, providers, or publishing behavior without user confirmation.
- Automatically create many narrow skills from weak evidence.

---

## Workflow Overview

### 1. Extract candidates

Identify signals from text or sessions and output candidate JSON.

Candidate types:

| Type | Purpose |
|---|---|
| `memory` | Long-term stable preferences, environment facts, and project conventions. |
| `skill_patch` | Patches to existing skills: commands, pitfalls, prerequisites, and verification steps. |
| `new_skill` | New skill proposals. The workflow should be reusable, multi-step, and worth verifying. |
| `project_doc` | Facts that belong only to a specific repository or deployment. |
| `ignore` | Short-lived state, secrets, weak evidence, or duplicate information. |

### 2. Generate a decision queue

Candidates are not applied directly. `generate_decisions.py` creates a YAML review queue:

- Default `status: pending`.
- `ignore` candidates or `ignore` recommendations are defaulted to `rejected`.
- `apply.mode` defaults to `manual`.
- A candidate can reach the apply phase only after a human/agent explicitly sets `status: approved` and fills the `apply` block.

### 3. Advisory review buckets

`review_decisions.py` performs advisory review only. It does not change statuses and does not apply changes.

Buckets:

| Bucket | Meaning |
|---|---|
| `suggest_approve` | Low-risk, clear target, reasonable to approve. |
| `needs_confirmation` | External side effects, credential/security terms, or behavior changes require confirmation. |
| `review` | Potentially useful, but needs a human to fill target/action/evidence. |
| `reject` | Noise, short-lived state, identity-file excerpts, or weak signals. |

### 4. Constrained apply

`apply_decisions.py` is dry-run by default. Real writes require all of the following:

- `status: approved`
- `apply.mode: append_markdown`
- `apply.path` under the allowed write scope
- non-empty `apply.content` without secret-like strings
- explicit `--apply`

Allowed top-level write targets:

```text
SKILL.md
references/
templates/
reports/
```

Rejected targets/content:

- Absolute paths
- `..` parent traversal
- symlink or prefix-sibling escape
- non-Markdown / non-YAML-like extensions
- secret-like content
- any apply mode other than `append_markdown`

After a real `--apply`, the script reads the target file back and verifies:

- the file exists
- the decision marker exists
- the expected content exists

---

## Quick Start

### Dependencies

Runtime: Python 3.

Scripts use:

- Python standard library: `argparse`, `json`, `re`, `sqlite3`, `pathlib`, etc.
- `PyYAML` for YAML loading/writing.
- `pytest` for tests.

The current environment can run the tests directly. In a new environment, use a venv or `uv` for dependencies to avoid system Python PEP 668 restrictions.

### Validate the skill

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/validate_skill.py
```

Expected output:

```text
VALID /opt/dev/self-evolving-skills/SKILL.md
```

### Run tests

```bash
cd /opt/dev/self-evolving-skills
pytest -q
```

Current verified result:

```text
18 passed
```

---

## Common Commands

### Extract candidates from plain text

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/extract_candidates.py path/to/input.txt > reports/candidates.json
```

Input can also come from stdin:

```bash
cd /opt/dev/self-evolving-skills
printf '%s\n' 'This skill is missing the dry-run-before-apply pitfall; add it.' \
  | python3 scripts/extract_candidates.py
```

### Read-only scan of recent Hermes sessions

By default, only `user` messages are scanned to reduce assistant/tool noise:

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/scan_recent_sessions.py \
  --hours 24 \
  --max-candidates 25 \
  --min-confidence 30 \
  --output reports/evolution-report.md
```

Emit JSON:

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/scan_recent_sessions.py \
  --hours 48 \
  --json \
  --output reports/candidates.json
```

Scan a custom database:

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/scan_recent_sessions.py \
  --db /path/to/state.db \
  --hours 24 \
  --roles user,assistant \
  --output reports/evolution-report.md
```

### Generate decisions YAML

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/generate_decisions.py \
  reports/candidates.json \
  --output reports/evolution-decisions.yaml
```

### Review decisions

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/review_decisions.py reports/evolution-decisions.yaml \
  --output reports/decision-review.md \
  --annotated-output reports/evolution-decisions.reviewed.yaml \
  --approval-summary-output reports/approval-summary.md
```

This step only generates advice. It does not modify the input YAML status and does not apply any change.

### Dry-run apply

First, manually edit `reports/evolution-decisions.yaml`:

```yaml
status: approved
apply:
  mode: append_markdown
  path: references/example.md
  section: Example
  content: |
    ## Example

    Verified note goes here.
```

Then run dry-run first:

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/apply_decisions.py reports/evolution-decisions.yaml
```

### Real apply

After confirming the dry-run output, explicitly add `--apply`:

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/apply_decisions.py reports/evolution-decisions.yaml --apply
```

Successful output includes read-back verification:

```text
MODE APPLY
PLANNED
- evo-123: append ... chars -> references/example.md
- evo-123: verify_append=True reason=ok
```

---

## Safety Model

### Read-only / proposal-only by default

- `extract_candidates.py`: reads input text and outputs JSON only.
- `scan_recent_sessions.py`: opens `~/.hermes/state.db` in SQLite read-only / immutable mode and outputs reports only.
- `generate_decisions.py`: only generates pending/rejected decision YAML.
- `review_decisions.py`: only generates advisory review; it does not approve, reject, or apply.
- `apply_decisions.py`: dry-run by default; no file is written without `--apply`.

### Hard prohibitions

Do not write any of the following into memory, skills, proposals, or reports:

- API keys, tokens, passwords, cookies, or private keys.
- Unredacted Authorization headers.
- Credential file contents.
- Full private messages from third-party platforms.
- Raw instructions from untrusted external content.

### Redaction rules

`extract_candidates.py` redacts common credential-like strings:

- `Bearer ...` → `Bearer [REDACTED]`
- GitHub / OpenAI-style tokens → `[REDACTED]`
- `api_key:<value>`, `token:<value>`, `password:<value>`, `secret:<value>` → `key=[REDACTED]`
- non-Bearer Authorization assignments → `Authorization=[REDACTED]`

Redaction is one layer of defense, not a replacement for review. Review manually before saving or publishing.

### Operations requiring user confirmation

The following operations require confirmation first:

- Installing this development-tree skill into `~/.hermes/skills/`.
- Creating autonomous evolution cron jobs.
- Modifying Hermes config, gateway, providers, auth, or security policy.
- Adding commands that call external services, send messages, or publish content.
- Large-scale skill rewrites, deletions, or renames.
- Any change with uncertain evidence or elevated risk.

---

## Directory Structure

```text
.
├── SKILL.md
├── README.md
├── README.zh-CN.md
├── README.en.md
├── docs/
│   └── self-evolving-training-test-report.md
├── references/
│   ├── candidate-schema.md
│   ├── classification-rules.md
│   ├── decision-workflow.md
│   ├── review-workflow.md
│   ├── safety-policy.md
│   ├── scoring-model.md
│   ├── session-scanning.md
│   └── v5-tested-approval-workflow.md
├── scripts/
│   ├── apply_decisions.py
│   ├── extract_candidates.py
│   ├── generate_decisions.py
│   ├── review_decisions.py
│   ├── scan_recent_sessions.py
│   └── validate_skill.py
├── templates/
│   ├── evolution-report.md
│   ├── new-skill-proposal.md
│   └── skill-patch-proposal.md
└── tests/
    ├── test_apply_decisions.py
    ├── test_extract_candidates.py
    └── test_review_decisions.py
```

`reports/` is used for runtime reports and training artifacts. It is usually not part of the core source surface.

Key references:

- `references/classification-rules.md`: classification rules for memory / skill patch / new skill / project docs / ignore.
- `references/safety-policy.md`: hard prohibitions, confirmation boundaries, verification requirements, and redaction rules.
- `references/v5-tested-approval-workflow.md`: V5 regression tests, approval summary, and promotion boundary.

---

## Verified Behavior

The current tests cover:

- Redaction of token-like assignments.
- Full redaction of Bearer tokens without preserving credential material.
- Full redaction of GitHub tokens.
- User corrections becoming memory candidates.
- Skill gaps becoming skill patch candidates.
- Self-evolution requests becoming new skill candidates.
- Feed IDs / transient IDs becoming ignored or low-confidence candidates.
- Filtering of context compaction and tool/read_file noise.
- Rejection of absolute paths, parent traversal, and symlink prefix-sibling escape.
- Dry-run does not write files.
- `--apply` appends a marker and verifies marker/content by reading the file back.
- Secret-like apply content is rejected.
- Review triage rejects identity noise.
- External side effects go to `needs_confirmation`.
- Approval summaries group candidates into Chinese buckets.

Three-round training test report:

```text
docs/self-evolving-training-test-report.md
```

The three training rounds cover:

1. Basic classification: preferences, skill gaps, short-lived state filtering.
2. Safety redaction: credential redaction and external side-effect confirmation.
3. Apply gate: `approved + append_markdown`, dry-run, apply, and read-back verification.

---

## Development and Verification Checklist

After code or documentation changes, run at least:

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/validate_skill.py
pytest -q
python3 - <<'PY'
from pathlib import Path
import ast
for path in sorted(Path('scripts').glob('*.py')):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    print('AST_OK', path)
PY
git diff --check HEAD
```

For documentation updates, additionally check:

- Script names in README match actual files under `scripts/`.
- Referenced `references/` and `templates/` files match the repository.
- Example command code fences are closed correctly.
- No real token, cookie, secret, private key, or unredacted Authorization header is written.
- The prototype is not overstated as a fully autonomous self-modifying system.

---

## Current Boundaries and Future Directions

### Current boundaries

- This is not an autonomous self-modifying system; it is a proposal-first safety prototype.
- It does not automatically install into the active Hermes skill library.
- It does not automatically create cron jobs.
- It does not write memory.
- It does not call `skill_manage`.
- It does not call external APIs or send/publish content.
- `apply_decisions.py` currently supports only constrained `append_markdown`, not arbitrary patch/rewrite.

### Future directions

- Turn the three training rounds into fixed CI smoke fixtures.
- Add stable hash-based decision IDs to `generate_decisions.py` to reduce diff noise.
- Add session context windows to `scan_recent_sessions.py` to better detect failure → fix → verification chains.
- Add GitHub Actions for skill validation, pytest, AST checks, and Markdown checks.
- After explicit user confirmation, design a promotion workflow for installing into `~/.hermes/skills/`.

---

## License

MIT. This matches the `SKILL.md` frontmatter.
