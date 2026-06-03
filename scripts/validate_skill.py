#!/usr/bin/env python3
"""Validate a Hermes-style SKILL.md in a development directory."""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(f"ERROR: PyYAML is required: {exc}", file=sys.stderr)
    sys.exit(2)

MAX_DESCRIPTION_LENGTH = 1024
MAX_SKILL_CONTENT_CHARS = 100_000


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        errors.append("SKILL.md must start with frontmatter delimiter at byte 0")
        return errors
    match = re.search(r"\n---\s*\n", content[3:])
    if not match:
        errors.append("frontmatter must close with a standalone --- line")
        return errors
    fm_text = content[3 : match.start() + 3]
    body = content[match.end() + 3 :]
    try:
        frontmatter = yaml.safe_load(fm_text)
    except Exception as exc:
        errors.append(f"frontmatter YAML parse failed: {exc}")
        return errors
    if not isinstance(frontmatter, dict):
        errors.append("frontmatter must parse as a mapping")
        return errors
    for field in ("name", "description"):
        if not frontmatter.get(field):
            errors.append(f"missing required frontmatter field: {field}")
    description = str(frontmatter.get("description", ""))
    if len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"description too long: {len(description)} > {MAX_DESCRIPTION_LENGTH}")
    if len(content) > MAX_SKILL_CONTENT_CHARS:
        errors.append(f"SKILL.md too large: {len(content)} > {MAX_SKILL_CONTENT_CHARS}")
    if not body.strip():
        errors.append("body must be non-empty")
    required_sections = ["## Overview", "## When to Use", "## Common Pitfalls", "## Verification Checklist"]
    for section in required_sections:
        if section not in body:
            errors.append(f"missing recommended section: {section}")
    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "SKILL.md"
    errors = validate(path)
    if errors:
        print("INVALID", path)
        for err in errors:
            print("-", err)
        return 1
    print("VALID", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
