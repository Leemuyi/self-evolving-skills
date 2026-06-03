# Candidate Schema

Use this schema for extracted evolution candidates.

```yaml
id: evo-YYYYMMDD-NN
candidate_type: memory | skill_patch | new_skill | project_doc | ignore
target: skill-name-or-path-or-memory
summary: one sentence
evidence:
  source: current_session | session_search | tool_output | user_correction | skill_gap
  details: redacted concise evidence
proposed_change: markdown or diff summary
value:
  frequency: low | medium | high
  failure_reduction: low | medium | high
  user_burden_reduction: low | medium | high
  verification_strength: weak | moderate | strong
risk:
  privacy: low | medium | high
  behavior_drift: low | medium | high
  external_side_effect: none | possible | direct
  maintenance_cost: low | medium | high
confirmation: none | recommended | required
verification_plan:
  - check 1
  - check 2
status: proposed | approved | applied | rejected | ignored
```

Keep candidates small. One candidate should map to one coherent patch or decision.
