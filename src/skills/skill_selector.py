import logging

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

# Skills in this set always run and do not count against the competitive cap.
_ALWAYS_RUN: set[str] = {"tone_moderation", "repetition_guard"}
_DEFAULT_MAX_SKILLS = 3


class SkillSelector:
    def __init__(self, skills: list[BaseSkill], debater_name: str = "unknown",
                 max_skills: int = _DEFAULT_MAX_SKILLS):
        self._skills = skills
        self._debater_name = debater_name
        self._max_skills = max_skills
        self._logger = logging.getLogger(f"skill_selector.{debater_name}")

    def select(self, context: SkillContext) -> list[SkillResult]:
        """Run all applicable skills; return results with at most max_skills competitive
        selections plus any always-run skills (e.g. tone_moderation).

        Skills are ranked by their dynamic score so the most contextually relevant
        guidance is kept.  Always-run skills bypass the cap entirely.
        """
        raw: list[SkillResult] = []
        candidates: list[tuple[float, SkillResult]] = []

        for skill in self._skills:
            if skill.name in _ALWAYS_RUN:
                result = skill.run(context)
                raw.append(result)
                self._logger.info("[skill_selector] '%s' (always-run): %s", skill.name, result.reason)
            else:
                s = skill.score(context)
                if s > 0.0:
                    result = skill.run(context)
                    raw.append(result)
                    candidates.append((s, result))
                    self._logger.info(
                        "[skill_selector] '%s' score=%.2f: %s", skill.name, s, result.reason
                    )
                else:
                    raw.append(SkillResult(skill_name=skill.name, selected=False,
                                           reason="score=0.0", content=""))
                    self._logger.debug("[skill_selector] '%s' skipped (score=0.0)", skill.name)

        # Keep top-scoring competitive skills; deselect the rest.
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        for _, r in candidates[self._max_skills:]:
            r.selected = False
            self._logger.debug(
                "[skill_selector] '%s' deselected (cap=%d)", r.skill_name, self._max_skills
            )

        return raw
