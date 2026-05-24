from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult


class RebuttalSkill(BaseSkill):
    name = "rebuttal"
    description = "Identifies key claims in opponent's last message to rebut"

    def can_handle(self, context: SkillContext) -> bool:
        return bool(context.opponent_last_message)

    def run(self, context: SkillContext) -> SkillResult:
        words = context.opponent_last_message.split()
        chunk = len(words) // 3 if len(words) >= 3 else len(words)
        phrases = []
        for i in range(3):
            start = i * chunk
            end = start + chunk
            segment = " ".join(words[start:end]).strip()
            if segment:
                phrases.append(segment)
        key_claims = "; ".join(f'"{p}"' for p in phrases) if phrases else context.opponent_last_message[:80]
        content = (
            f"Opponent claims: {key_claims}. "
            "Counter points to address: challenge each claim with evidence or logic."
        )
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="opponent message is non-empty",
            content=content,
        )
