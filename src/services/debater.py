from __future__ import annotations

from typing import TYPE_CHECKING

from src.ipc.message import DebateMessage, MessageType
from src.sdk.base_client import BaseAIClient
from src.services.base_agent import (
    BaseAgent,
    DebaterSkill,
    enforce_word_limit,
    get_agent_prompt,
)
from src.shared.config import ConfigManager
from src.shared.gatekeeper import ApiGatekeeper
from src.skills import (
    CitationSkill,
    EvidenceSkill,
    RebuttalSkill,
    RetrieverSkill,
    SkillContext,
    SkillSelector,
    SocraticSkill,
    SummarizationSkill,
    ToneModerationSkill,
)
from src.tools.web_search import WebSearchTool

if TYPE_CHECKING:
    from src.ipc.channel import IpcChannel
    from src.rag.rag_service import RAGService

_cfg = ConfigManager()
_MAX_WORDS: int = _cfg.get_value("debate", "debater_max_words", 120)

_DEFAULT_SKILLS = [
    RebuttalSkill(), EvidenceSkill(), SocraticSkill(),
    SummarizationSkill(), CitationSkill(), ToneModerationSkill(),
]


class Debater(BaseAgent):
    """Competitive AI debater — IPC process loop or direct SDK call."""

    def __init__(self, name: str, stance: str, topic: str,
                 client: BaseAIClient, gatekeeper: ApiGatekeeper,
                 skill: DebaterSkill = DebaterSkill.EVIDENCE_BASED,
                 search_tool: WebSearchTool | None = None,
                 opponent_stance: str = "",
                 rag_service: RAGService | None = None):
        super().__init__(name, client, gatekeeper, role="debater")
        self.stance = stance
        self.opponent_stance = opponent_stance
        self.topic = topic
        self.skill = skill
        self.search_tool = search_tool or WebSearchTool()
        self.system_prompt = self._build_system_prompt()
        self.inbox:  IpcChannel | None = None
        self.outbox: IpcChannel | None = None
        extra = [RetrieverSkill(rag_service)] if rag_service is not None else []
        self._skill_selector = SkillSelector(_DEFAULT_SKILLS + extra)

    def _build_system_prompt(self) -> str:
        role_key = "pro" if self.skill == DebaterSkill.EVIDENCE_BASED else "contra"
        agent_cfg = get_agent_prompt(role_key)
        stance_directive = (
            agent_cfg.get("stance_directive", "")
            .replace("{stance}", self.stance)
            .replace("{opponent_stance}", self.opponent_stance)
        )
        rules = "\n".join(
            f"- {r}".replace("{stance}", self.stance).replace("{opponent_stance}", self.opponent_stance)
            for r in agent_cfg.get("rules", [])
        )
        return (
            f"ROLE: {role_key.upper()} debater in a formal debate.\n"
            f"TOPIC: {self.topic}\n"
            f"{stance_directive}\n\n"
            f"RULES:\n{rules}"
        )

    def _build_skill_guidance(self, history: list[dict], round_num: int) -> str:
        opponent_msg = ""
        for entry in reversed(history):
            if entry.get("role") == "user":
                opponent_msg = entry.get("content", "")
                break
        ctx = SkillContext(
            topic=self.topic, stance=self.stance,
            opponent_last_message=opponent_msg, round_num=round_num,
            skill_type=str(self.skill), transcript=history,
        )
        results = self._skill_selector.select(ctx)
        parts = [r.content for r in results if r.selected and r.content]
        if not parts:
            return ""
        # Use a blank-line separator so multiline blocks (e.g. evidence passages)
        # are not corrupted by a leading "- " that only attaches to the first line.
        return "\n\nSKILL GUIDANCE:\n" + "\n\n".join(parts)

    async def generate(self, messages: list[dict]) -> str:
        """Call the LLM and return a validated response."""
        response = await self.gatekeeper.execute(self.client.generate_response, messages)
        return self._validate_response(response)

    async def get_argument(self, history: list[dict], round_num: int = 0) -> str:
        """Direct SDK call — preserved for tests and backward compatibility."""
        enriched_history = list(history)
        if round_num % 2 == 0:
            query = f"{self.topic} {self.stance} evidence"
            results = await self.search_tool.search(query)
            citation_text = self.search_tool.format_for_prompt(results)
            if citation_text:
                enriched_history = [{"role": "user", "content": citation_text}] + enriched_history
        skill_guidance = self._build_skill_guidance(enriched_history, round_num)
        messages = [{"role": "system", "content": self.system_prompt}] + enriched_history
        if skill_guidance:
            messages.append({"role": "user", "content": skill_guidance})
        response = await self.generate(messages)
        return enforce_word_limit(response, _MAX_WORDS, self.name, self.logger)

    async def run(self) -> None:
        """IPC process loop — blocks on inbox, responds to RELAY and SHUTDOWN."""
        assert self.inbox and self.outbox, f"{self.name}: channels must be set before run()"
        history: list[dict] = []
        self.logger.info(f"[{self.name}] IPC process started (skill={self.skill})")
        while True:
            try:
                msg = await self.inbox.receive()
            except TimeoutError:
                self.logger.warning(f"[{self.name}] inbox timeout — exiting")
                break
            if msg.msg_type == MessageType.SHUTDOWN:
                self.logger.info(f"[{self.name}] received SHUTDOWN — exiting")
                break
            if msg.msg_type == MessageType.RELAY:
                if msg.payload:
                    history.append({"role": "user", "content": msg.payload})
                self.logger.info(f"[{self.name}] generating argument for round {msg.round_num}")
                argument = await self.get_argument(history, round_num=msg.round_num)
                history.append({"role": "assistant", "content": argument})
                reply = DebateMessage(
                    msg_type=MessageType.ARGUMENT, sender=self.name,
                    receiver="judge", payload=argument, round_num=msg.round_num,
                )
                await self.outbox.send(reply)
                self.logger.info(f"[{self.name}] sent ARGUMENT round {msg.round_num}")
