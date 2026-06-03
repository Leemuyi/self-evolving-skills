import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import apply_decisions  # noqa: E402


def test_resolve_allowed_rejects_absolute_path():
    try:
        apply_decisions.resolve_allowed("/tmp/evil.md")
    except ValueError as exc:
        assert "relative" in str(exc)
    else:
        raise AssertionError("absolute path was accepted")


def test_resolve_allowed_rejects_parent_traversal():
    try:
        apply_decisions.resolve_allowed("references/../evil.md")
    except ValueError as exc:
        assert "relative" in str(exc) or "stay under" in str(exc)
    else:
        raise AssertionError("parent traversal was accepted")


def test_append_markdown_dry_run_does_not_write(tmp_path):
    target = tmp_path / "note.md"

    message = apply_decisions.append_markdown(target, "## Note\nhello", "evo-test", apply=False)

    assert "append" in message
    assert not target.exists()


def test_append_markdown_apply_writes_marker_and_verify_finds_it(tmp_path):
    target = tmp_path / "note.md"

    apply_decisions.append_markdown(target, "## Note\nhello", "evo-test", apply=True)
    result = apply_decisions.verify_append(target, "evo-test", "## Note\nhello")

    assert result["ok"] is True
    assert "evo-test" in target.read_text(encoding="utf-8")


def test_append_markdown_rejects_secret_content(tmp_path):
    target = tmp_path / "note.md"

    try:
        apply_decisions.append_markdown(target, "token=abcdef1234567890", "evo-test", apply=True)
    except ValueError as exc:
        assert "secret" in str(exc)
    else:
        raise AssertionError("secret content was accepted")
