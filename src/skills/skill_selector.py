import logging

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult


class SkillSelector:
    def __init__(self, skills: list[BaseSkill]):
        self._skills = skills
        self._logger = logging.getLogger("skill_selector")

    def select(self, context: SkillContext) -> list[SkillResult]:
        """Run all applicable skills, log selections, return SkillResult list.

        A skill's own ``selected`` field is respected — if a skill's
        ``can_handle`` returns True but its ``run`` decides there is nothing
        useful to contribute (e.g. RetrieverSkill when no chunks are found),
        it may return ``selected=False`` and that result is preserved.
        """
        results = []
        for skill in self._skills:
            if skill.can_handle(context):
                result = skill.run(context)
                if result.selected:
                    self._logger.info(
                        "[skill_selector] selected '%s': %s", skill.name, result.reason
                    )
                else:
                    self._logger.debug(
                        "[skill_selector] skill '%s' ran but produced no output: %s",
                        skill.name, result.reason,
                    )
                results.append(result)
            else:
                results.append(SkillResult(
                    skill_name=skill.name,
                    selected=False,
                    reason="not applicable",
                    content="",
                ))
        return results
