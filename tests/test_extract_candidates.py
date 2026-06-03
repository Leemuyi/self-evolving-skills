import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_candidates import extract, redact  # noqa: E402


def test_redacts_token_like_assignment():
    text = "api_key=super-secret-value"

    redacted = redact(text)

    assert "super-secret-value" not in redacted
    assert "[REDACTED]" in redacted


def test_user_correction_becomes_memory_candidate():
    candidates = extract("以后不要直接发布，先给我确认", role="user")

    assert candidates
    assert candidates[0]["candidate_type"] == "memory"
    assert "user_correction" in candidates[0]["evidence"]["signals"]


def test_skill_gap_becomes_skill_patch():
    candidates = extract("这个 skill 缺少登录态这个坑，需要补上", role="user")

    assert candidates
    assert candidates[0]["candidate_type"] == "skill_patch"


def test_self_evolving_request_becomes_new_skill():
    candidates = extract("构建一个自进化的 技能 skill，随着聊天内容不断进化技能", role="user")

    assert candidates
    assert candidates[0]["candidate_type"] == "new_skill"
    assert candidates[0]["target"] == "self-evolving-skills"


def test_transient_feed_id_is_ignored_or_low_confidence():
    candidates = extract("已发布 feedId 01KT5CE3PT2MJXJYYKH7S3TXJS，记住这个进度", role="user")

    assert candidates
    assert candidates[0]["candidate_type"] == "ignore"
    assert candidates[0]["confidence_score"] <= 25


def test_structural_compaction_noise_is_skipped():
    candidates = extract("## Completed Actions\n1. 已完成 skill patch [tool: terminal]", role="assistant")

    assert candidates == []
