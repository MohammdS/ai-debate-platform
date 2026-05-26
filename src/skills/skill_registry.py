"""Registry mapping skill class-name strings to BaseSkill classes.

Usage
-----
    from src.skills.skill_registry import build_skill_pool
    pool = build_skill_pool(["RebuttalSkill", "EvidenceSkill"])

To register a new skill, simply add it to SKILL_REGISTRY — no other
file needs to change for the registry to pick it up.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.skills.citation_skill import CitationSkill
from src.skills.evidence_skill import EvidenceSkill
from src.skills.judge_evaluation_skill import JudgeEvaluationSkill
from src.skills.progression_skill import ProgressionSkill
from src.skills.rebuttal_skill import RebuttalSkill
from src.skills.repetition_guard_skill import RepetitionGuardSkill
from src.skills.socratic_skill import SocraticSkill
from src.skills.summarization_skill import SummarizationSkill
from src.skills.tone_moderation_skill import ToneModerationSkill

if TYPE_CHECKING:
    from src.skills.base_skill import BaseSkill

_log = logging.getLogger(__name__)

# Map config-friendly class name strings → concrete skill classes.
# Edit this dict (and add the import above) to register a new skill.
SKILL_REGISTRY: dict[str, type[BaseSkill]] = {
    "CitationSkill":        CitationSkill,
    "EvidenceSkill":        EvidenceSkill,
    "JudgeEvaluationSkill": JudgeEvaluationSkill,
    "ProgressionSkill":     ProgressionSkill,
    "RebuttalSkill":        RebuttalSkill,
    "RepetitionGuardSkill": RepetitionGuardSkill,
    "SocraticSkill":        SocraticSkill,
    "SummarizationSkill":   SummarizationSkill,
    "ToneModerationSkill":  ToneModerationSkill,
}


def build_skill_pool(names: list[str]) -> list[BaseSkill]:
    """Instantiate skills by class name in the given order.

    Unknown names emit a WARNING and are skipped so a single typo in
    setup.json does not crash the entire debate.
    """
    pool: list[BaseSkill] = []
    for name in names:
        cls = SKILL_REGISTRY.get(name)
        if cls is None:
            _log.warning("[skill_registry] unknown skill %r — skipping", name)
            continue
        pool.append(cls())
    if not pool:
        _log.warning(
            "[skill_registry] debater_pool resolved to an empty list; "
            "debaters will run without skill guidance"
        )
    return pool
