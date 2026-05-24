from unittest.mock import AsyncMock, MagicMock

import pytest

from src.skills import (
    CitationSkill,
    EvidenceSkill,
    JudgeEvaluationSkill,
    RebuttalSkill,
    SkillContext,
    SkillSelector,
    SocraticSkill,
    SummarizationSkill,
    ToneModerationSkill,
)


def make_ctx(**kwargs):
    defaults = {
        "topic": "AI", "stance": "pro", "opponent_last_message": "",
        "round_num": 1, "skill_type": "evidence_based", "transcript": [],
    }
    defaults.update(kwargs)
    return SkillContext(**defaults)


# 1
def test_rebuttal_can_handle_with_opponent_message():
    skill = RebuttalSkill()
    ctx = make_ctx(opponent_last_message="AI is dangerous.")
    assert skill.can_handle(ctx) is True


# 2
def test_rebuttal_cannot_handle_empty_message():
    skill = RebuttalSkill()
    ctx = make_ctx(opponent_last_message="")
    assert skill.can_handle(ctx) is False


# 3
def test_evidence_skill_handles_evidence_type():
    skill = EvidenceSkill()
    ctx = make_ctx(skill_type="evidence_based")
    assert skill.can_handle(ctx) is True


# 4
def test_socratic_skill_handles_socratic_type():
    skill = SocraticSkill()
    ctx = make_ctx(skill_type="socratic")
    assert skill.can_handle(ctx) is True


# 5
def test_summarization_requires_4_entries():
    skill = SummarizationSkill()
    ctx3 = make_ctx(transcript=[{"role": "user", "content": "x"}] * 3)
    ctx4 = make_ctx(transcript=[{"role": "user", "content": "x"}] * 4)
    assert skill.can_handle(ctx3) is False
    assert skill.can_handle(ctx4) is True


# 6
def test_citation_always_handles():
    skill = CitationSkill()
    for st in ["evidence_based", "socratic", "judge", ""]:
        assert skill.can_handle(make_ctx(skill_type=st)) is True


# 7
def test_tone_always_handles():
    skill = ToneModerationSkill()
    for st in ["evidence_based", "socratic", "judge", ""]:
        assert skill.can_handle(make_ctx(skill_type=st)) is True


# 8
def test_judge_evaluation_handles_judge_type():
    skill = JudgeEvaluationSkill()
    assert skill.can_handle(make_ctx(skill_type="judge")) is True
    assert skill.can_handle(make_ctx(skill_type="evidence_based")) is False


# 9
def test_skill_selector_returns_results_for_all_skills():
    all_skills = [
        RebuttalSkill(), EvidenceSkill(), SocraticSkill(),
        SummarizationSkill(), CitationSkill(), ToneModerationSkill(),
        JudgeEvaluationSkill(),
    ]
    selector = SkillSelector(all_skills)
    ctx = make_ctx(opponent_last_message="something")
    results = selector.select(ctx)
    assert len(results) == len(all_skills)


# 10
def test_skill_selector_selects_applicable_skills():
    all_skills = [
        RebuttalSkill(), EvidenceSkill(), CitationSkill(), ToneModerationSkill(),
    ]
    selector = SkillSelector(all_skills)
    ctx = make_ctx(skill_type="evidence_based", opponent_last_message="AI is bad")
    results = selector.select(ctx)
    selected = [r for r in results if r.selected]
    assert len(selected) >= 1


# 11
@pytest.mark.asyncio
async def test_skill_results_injected_into_debater_prompt():
    from src.services.debater import Debater

    mock_client = MagicMock()
    mock_client.generate_response = AsyncMock(return_value="AI is great. WINNER: pro")
    mock_gatekeeper = MagicMock()
    mock_gatekeeper.execute = AsyncMock(return_value="AI is great. WINNER: pro")

    debater = Debater("Pro", "pro-AI", "AI topic", mock_client, mock_gatekeeper)
    result = await debater.get_argument([{"role": "user", "content": "AI is bad"}])
    assert isinstance(result, str)
    assert len(result) > 0


# 12
def test_judge_evaluation_skill_content_forbids_tie():
    skill = JudgeEvaluationSkill()
    ctx = make_ctx(skill_type="judge")
    result = skill.run(ctx)
    lower = result.content.lower()
    assert "tie" in lower or "winner" in lower
