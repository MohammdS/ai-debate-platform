from unittest.mock import MagicMock

import pytest

from src.services.base_agent import BaseAgent, DebaterSkill, get_skill_instruction
from src.services.debater import Debater
from src.services.judge import Judge

# --- DebaterSkill enum ---

def test_skill_enum_values():
    assert DebaterSkill.EVIDENCE_BASED == "evidence_based"
    assert DebaterSkill.SOCRATIC == "socratic"


def test_each_skill_has_instructions():
    for skill in [DebaterSkill.EVIDENCE_BASED, DebaterSkill.SOCRATIC,
                  DebaterSkill.STORYTELLING, DebaterSkill.LOGICAL_FALLACY]:
        instruction = get_skill_instruction(skill)
        assert len(instruction) > 20


def test_skill_instructions_are_distinct():
    instructions = [get_skill_instruction(s) for s in DebaterSkill]
    assert len(set(instructions)) == len(instructions)


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
    assert "EVIDENCE" in d_evidence.system_prompt
    assert "SOCRATIC" in d_socratic.system_prompt
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
