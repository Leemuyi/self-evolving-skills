# Review Workflow

Version 4 adds an advisory reviewer for `evolution-decisions.yaml`.

## Purpose

`review_decisions.py` helps triage pending decisions into buckets:

- `suggest_approve`: likely useful, mapped, and low risk.
- `needs_confirmation`: could affect external workflows, credentials, cron, gateway, or skill behavior.
- `review`: potentially useful but needs target/action mapping.
- `reject`: likely transient, noisy, duplicated, identity-file content, or low confidence.

It is advisory only. It does not modify the input decision file unless you explicitly request an annotated copy, and even then it writes a separate file.

## Commands

```bash
cd /opt/dev/self-evolving-skills

python3 scripts/review_decisions.py \
  reports/evolution-decisions.yaml \
  --output reports/decision-review.md \
  --annotated-output reports/evolution-decisions.reviewed.yaml
```

## Review Rules

Suggested rejection triggers:

- transient task status: feed IDs, PR IDs, commit SHAs, “published/done” notes;
- tool/compaction noise;
- raw identity/persona file excerpts already captured elsewhere;
- low value or low confidence.

Needs-confirmation triggers:

- external side effects: publish/send/auth/GitHub/Meyo/cron/gateway/config;
- skill patch or new skill behavior changes;
- credential/security-adjacent terms.

Suggested approval triggers:

- mapped `skill_patch`/`new_skill` candidates with acceptable confidence and low risk;
- durable memory-looking preference with low risk.

## Safe Use

After reading the review report, manually edit `reports/evolution-decisions.yaml`:

1. Leave untrusted items as `pending` or set to `rejected`.
2. For a trusted local append, set `status: approved`.
3. Fill `apply.mode: append_markdown`, `apply.path`, and redacted `apply.content`.
4. Run `apply_decisions.py` without `--apply` first.
5. Only then run with `--apply`.
