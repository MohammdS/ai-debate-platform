import logging

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

# Higher number = lower priority (will be dropped first when over cap).
# Argument-driving skills (rebuttal, progression, evidence/socratic) are
# kept; support skills (citation, tone_moderation) are deprioritised so
# they never crowd out substantive guidance.
_PRIORITY: dict[str, int] = {
    "rebuttal":          1,
    "progression":       2,
    "evidence":          3,
    "socratic":          3,
    "repetition_guard":  4,
    "summarization":     5,
    "citation":          6,
    "tone_moderation":   7,
}
_DEFAULT_MAX_SKILLS = 3


class SkillSelector:
    def __init__(self, skills: list[BaseSkill], debater_name: str = "unknown",
                 max_skills: int = _DEFAULT_MAX_SKILLS):
        self._skills = skills
        self._debater_name = debater_name
        self._max_skills = max_skills
        self._logger = logging.getLogger(f"skill_selector.{debater_name}")

    def select(self, context: SkillContext) -> list[SkillResult]:
        """Run all applicable skills; return at most max_skills selected results.

        Skills are ranked by _PRIORITY so argument-driving skills are always
        kept and support skills (citation, tone) are dropped first when the cap
        is reached.  Skills that return selected=False are preserved in the
        result list but do not count against the cap.
        """
        raw: list[SkillResult] = []
        for skill in self._skills:
            if skill.can_handle(context):
                result = skill.run(context)
                raw.append(result)
                level = logging.INFO if result.selected else logging.DEBUG
                self._logger.log(level, "[skill_selector] '%s': %s", skill.name, result.reason)
            else:
                raw.append(SkillResult(skill_name=skill.name, selected=False,
                                       reason="not applicable", content=""))

        # Apply cap: sort selected results by priority, deselect the excess.
        selected = [r for r in raw if r.selected]
        selected.sort(key=lambda r: _PRIORITY.get(r.skill_name, 99))
        for r in selected[self._max_skills:]:
            r.selected = False
            self._logger.debug("[skill_selector] '%s' deselected (cap=%d)", r.skill_name, self._max_skills)

        return raw
