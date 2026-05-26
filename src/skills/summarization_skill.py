from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_DEFAULT_MIN_ENTRIES = 4
_DEFAULT_SNIPPET_CHARS = 80
_DEFAULT_HEADER = "Recent debate summary:"


class SummarizationSkill(BaseSkill):
    name = "summarization"
    description = "Summarizes the debate so far for context"

    def score(self, context: SkillContext) -> float:
        cfg = self._get_config()
        min_entries = cfg.get("min_transcript_entries", _DEFAULT_MIN_ENTRIES)
        if len(context.transcript) < min_entries:
            return 0.0
        s = 0.35
        if len(context.transcript) >= 8:
            s += 0.12
        if len(context.transcript) >= 12:
            s += 0.08
        if context.round_num >= 5:
            s += 0.05
        if context.skill_type == "judge":
            s += 0.20
        return min(0.62, s)

    def run(self, context: SkillContext) -> SkillResult:
        cfg = self._get_config()
        min_entries = cfg.get("min_transcript_entries", _DEFAULT_MIN_ENTRIES)
        snippet_chars = cfg.get("snippet_chars", _DEFAULT_SNIPPET_CHARS)
        header = cfg.get("header", _DEFAULT_HEADER)
        lines = []
        for entry in context.transcript[-min_entries:]:
            name = entry.get("name", entry.get("role", "Unknown"))
            text = entry.get("content", "")[:snippet_chars]
            lines.append(f"{name}: {text}")
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason=f"transcript has >= {min_entries} entries",
            content=header + "\n" + "\n".join(lines),
        )
