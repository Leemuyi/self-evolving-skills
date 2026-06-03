# Classification Rules

Use these rules before saving anything from a conversation.

## Destinations

### Memory
Use memory for stable facts that will remain useful across sessions:

- User preferences and corrections.
- Durable environment facts.
- Stable project conventions.
- Repeated behavioral expectations.

Do not store task progress, IDs, feed links, issue numbers, commit SHAs, or temporary state.

### Skill Patch
Patch an existing skill when the session reveals:

- A stale command or wrong API endpoint.
- A missing prerequisite.
- A pitfall with a verified workaround.
- A better verification step.
- A user-preferred workflow for a recurring task class.

### New Skill
Create a new skill proposal when:

- The workflow is reusable across multiple future tasks.
- No existing skill covers it well.
- The procedure needs several ordered steps, pitfalls, and verification.
- There is enough evidence from real usage or explicit user request.

### Project Documentation
Use project docs when the detail is specific to one repository or deployment.

### Ignore
Ignore when the item is:

- One-off status or completion log.
- Likely stale within 7 days.
- A secret or private content excerpt.
- Weakly supported speculation.
- Already covered by an existing memory or skill.

## Decision Tree

```text
Is it secret/private? -> redact or ignore
Is it short-lived? -> ignore
Is it a stable user preference? -> memory
Is it a reusable procedure? -> skill
Does an existing skill cover the domain? -> patch that skill
Is it repo-specific? -> project docs
Otherwise -> proposal only or ignore
```
