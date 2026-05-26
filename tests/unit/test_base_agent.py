from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.base_agent import BaseAgent, DebaterSkill
from src.services.debater import Debater
from src.services.judge import Judge

# --- DebaterSkill enum ---

def test_skill_enum_values():
    assert DebaterSkill.EVIDENCE_BASED == "evidence_based"
    assert DebaterSkill.SOCRATIC == "socratic"


def test_skill_enum_has_all_variants():
    values = {s.value for s in DebaterSkill}
    assert {"evidence_based", "socratic", "storytelling", "logical_fallacy"} == values


# --- BaseAgent is abstract ---

def test_base_agent_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseAgent("x", MagicMock(), MagicMock())  # type: ignore[abstract]


# --- Debater inherits BaseAgent ---

def test_debater_is_base_agent():
    d = Debater("Pro", "yes", "topic", MagicMock(), MagicMock())
    assert isinstance(d, BaseAgent)


def test_debater_default_skill_is_evidence_based():
    d = Debater("Pro", "yes", "topic", MagicMock(), MagicMock())
    assert d.skill == DebaterSkill.EVIDENCE_BASED


def test_debater_skill_shapes_system_prompt():
    d_evidence = Debater("Pro", "yes", "topic", MagicMock(), MagicMock(),
                         skill=DebaterSkill.EVIDENCE_BASED)
    d_socratic  = Debater("Contra", "no", "topic", MagicMock(), MagicMock(),
                          skill=DebaterSkill.SOCRATIC)
    assert "pro" in d_evidence.system_prompt.lower()
    assert "contra" in d_socratic.system_prompt.lower()
    assert d_evidence.system_prompt != d_socratic.system_prompt


def test_pro_contra_skills_differ():
    pro    = Debater("Pro",    "yes", "topic", MagicMock(), MagicMock(),
                     skill=DebaterSkill.EVIDENCE_BASED)
    contra = Debater("Contra", "no",  "topic", MagicMock(), MagicMock(),
                     skill=DebaterSkill.SOCRATIC)
    assert pro.skill != contra.skill


# --- Judge inherits BaseAgent ---

def test_judge_is_base_agent():
    j = Judge(MagicMock(), MagicMock())
    assert isinstance(j, BaseAgent)


def test_judge_system_prompt_forbids_tie():
    j = Judge(MagicMock(), MagicMock())
    assert "tie" in j.system_prompt.lower() or "winner" in j.system_prompt.lower()


# --- generate() on Debater ---

@pytest.mark.asyncio
async def test_debater_generate_returns_non_empty_string():
    """debater.generate() must return a non-empty string."""
    mock_client = MagicMock()
    mock_client.generate_response = AsyncMock(return_value="A solid argument.")
    mock_gatekeeper = MagicMock()
    mock_gatekeeper.execute = AsyncMock(return_value="A solid argument.")

    d = Debater("Pro", "yes", "AI topic", mock_client, mock_gatekeeper)
    messages = d._build_messages("Make your opening argument.")
    result = await d.generate(messages)
    assert isinstance(result, str)
    assert len(result.strip()) > 0


# --- Judge winner validation ---

@pytest.mark.asyncio
async def test_judge_evaluate_raises_when_no_winner():
    """evaluate() must raise ValueError when response lacks WINNER: <side>."""
    mock_client = MagicMock()
    mock_gatekeeper = MagicMock()
    mock_gatekeeper.execute = AsyncMock(return_value="Both sides argued well. No clear outcome.")

    j = Judge(mock_client, mock_gatekeeper)
    with pytest.raises(ValueError, match="Judge must declare a winner"):
        await j.evaluate([{"role": "user", "content": "Argument text"}])


@pytest.mark.asyncio
async def test_judge_evaluate_succeeds_with_valid_winner():
    """evaluate() must return the verdict string when a valid winner is declared."""
    mock_client = MagicMock()
    mock_gatekeeper = MagicMock()
    verdict_text = "SCORES\nPro: 80 | Contra: 70\nWINNER: Pro\nREASONING: Pro had better evidence."
    mock_gatekeeper.execute = AsyncMock(return_value=verdict_text)

    j = Judge(mock_client, mock_gatekeeper)
    result = await j.evaluate([{"role": "user", "content": "Argument text"}])
    assert "WINNER" in result.upper()
    assert isinstance(result, str)
