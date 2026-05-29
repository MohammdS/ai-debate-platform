from __future__ import annotations

from src.shared.config import ConfigManager
from src.skills.fact_safety_filter import FactSafetyFilter

CFG = ConfigManager()
MAX_WORDS: int = CFG.get_value("debate", "debater_max_words", 120)
DEFAULT_POOL: list[str] = [
    "RepetitionGuardSkill", "RebuttalSkill", "ProgressionSkill", "EvidenceSkill",
    "SocraticSkill", "SummarizationSkill", "CitationSkill", "ToneModerationSkill",
]
FACT_SAFETY = FactSafetyFilter()
STRICT_REWRITE = (
    "Rewrite the response without weak debate clichés. "
    "Do NOT open with 'That claim…', 'That argument…', 'That assessment…', "
    "'That position…', or any variant of '[noun] overlooks/ignores/equates/fails…'. "
    "Instead hit directly with counter-evidence or a sharp counter-fact. "
    "Be blunt and aggressive, but do not invent facts. "
    "State only what is supportable, then explain why it damages the previous point."
)
ECHO_REWRITE = (
    "Rewrite with completely new wording and a sharper attack angle. "
    "Do not repeat the same argument — escalate."
)
