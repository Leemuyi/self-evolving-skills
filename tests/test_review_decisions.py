import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import review_decisions  # noqa: E402


def decision(summary, candidate_type="skill_patch", target="self-evolving-skills", confidence=50, risk=0, value=50):
    return {
        "id": "evo-test",
        "candidate_type": candidate_type,
        "target": target,
        "summary": summary,
        "evidence": {"details": summary},
        "scores": {"confidence_score": confidence, "risk": risk, "value": value},
    }


def test_rejects_identity_content():
    result = review_decisions.review_one(decision("记住你只是客人。", candidate_type="memory", target="unmapped"))

    assert result["bucket"] == "reject"
    assert result["suggested_status"] == "rejected"


def test_suggests_approval_for_mapped_low_risk_skill_patch():
    result = review_decisions.review_one(decision("skill 缺少验证步骤，需要补充", target="hermes-agent-skill-authoring"))

    assert result["bucket"] == "suggest_approve"
    assert result["suggested_status"] == "pending"


def test_external_side_effect_needs_confirmation():
    result = review_decisions.review_one(decision("给 cron 自动发布内容增加流程", target="self-evolving-skills", confidence=45))

    assert result["bucket"] == "needs_confirmation"


def test_approval_summary_groups_review_results():
    doc = {
        "decisions": [
            {**decision("skill 缺少验证步骤", target="hermes-agent-skill-authoring"), "id": "a"},
            {**decision("记住你只是客人", candidate_type="memory", target="unmapped"), "id": "b"},
        ]
    }
    reviews = {str(d["id"]): review_decisions.review_one(d) for d in doc["decisions"]}

    summary = review_decisions.approval_summary(doc, reviews)

    assert "建议批准" in summary
    assert "建议拒绝" in summary
    assert "hermes-agent-skill-authoring" in summary
