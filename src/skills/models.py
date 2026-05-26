from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillContext:
    topic: str
    stance: str
    opponent_last_message: str
    round_num: int
    skill_type: str          # "evidence_based", "socratic", "judge", etc.
    transcript: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    skill_name: str
    selected: bool
    reason: str
    content: str             # text to inject into the prompt
    metadata: dict[str, Any] = field(default_factory=dict)
