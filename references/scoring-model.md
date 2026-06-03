# Scoring Model

Version 2 adds lightweight ranking so reports are reviewable instead of noisy dumps.

## Scores

### `value_score`

Higher when a line contains strong reuse signals:

- Explicit remember/save/correction language.
- Skill gap language: stale, missing, wrong, pitfall.
- Workflow/evolution/session-scanning requests.
- Verified fixes: tested, validated, `exit_code 0`.
- User-authored message role.

### `risk_score`

Higher when a line may be unsafe or low-quality:

- Credential-like text or auth/token terms.
- Transient identifiers: feed IDs, PR IDs, commit SHAs, event IDs.
- External side-effect verbs: publish/send/delete/auth.
- Very long text blobs.

### `confidence_score`

Computed as value minus part of risk, clamped to 0-100.

Labels:

- `high`: >= 65
- `medium`: >= 40
- `low`: < 40

## Recommendations

- `apply_after_review`: high confidence, low risk. Still requires a separate apply step.
- `ask`: explicit user confirmation required, usually for skill/new-skill or risky items.
- `review`: candidate may be useful but needs human/agent judgment.
- `ignore`: transient or weak item.

## Report Defaults

`scan_recent_sessions.py` defaults to:

```bash
--roles user
--max-candidates 25
--min-confidence 30
```

This is intentionally conservative. Broaden roles only when debugging the extractor or doing a deeper audit.
