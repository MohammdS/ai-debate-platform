from __future__ import annotations

from typing import TYPE_CHECKING

from src.sdk.base_client import BaseAIClient
from src.services.base_agent import BaseAgent, DebaterSkill, enforce_word_limit, get_agent_prompt
from src.services.context_compressor import ContextCompressor
from src.services.debate_memory import DebateMemory
from src.services.debater_ipc import DebaterIpcMixin
from src.services.response_cleanup import (
    repeated_word_run,
    strip_debate_labels,
    validate_debate_response,
)
from src.shared.config import ConfigManager
from src.shared.gatekeeper import ApiGatekeeper
from src.skills import SkillContext, SkillSelector, build_skill_pool
from src.skills.fact_safety_filter import FactSafetyFilter
from src.skills.source_challenge_limiter import SourceChallengeLimiter
from src.tools.web_search import WebSearchTool

if TYPE_CHECKING:
    from src.ipc.channel import IpcChannel

_cfg = ConfigManager()
_MAX_WORDS: int = _cfg.get_value("debate", "debater_max_words", 120)
_DEFAULT_POOL: list[str] = [
    "RepetitionGuardSkill", "RebuttalSkill", "ProgressionSkill", "EvidenceSkill",
    "SocraticSkill", "SummarizationSkill", "CitationSkill", "ToneModerationSkill",
]
_fact_safety = FactSafetyFilter()
_STRICT_REWRITE = "Rewrite the response without banned debate clichés. Start directly with the argument."
_ECHO_REWRITE = "Rewrite without echoing the previous response. Use new wording."


class Debater(DebaterIpcMixin, BaseAgent):
    """Competitive AI debater — IPC process loop or direct SDK call."""

    def __init__(self, name: str, stance: str, topic: str,
                 client: BaseAIClient, gatekeeper: ApiGatekeeper,
                 skill: DebaterSkill = DebaterSkill.EVIDENCE_BASED,
                 search_tool: WebSearchTool | None = None,
                 opponent_stance: str = ""):
        super().__init__(name, client, gatekeeper, role="debater")
        self.stance, self.opponent_stance, self.topic, self.skill = stance, opponent_stance, topic, skill
        self.search_tool = search_tool or WebSearchTool()
        self.system_prompt = self._build_system_prompt()
        self.inbox: IpcChannel | None = None
        self.outbox: IpcChannel | None = None
        self._compressor = ContextCompressor()
        self._challenge_limiter = SourceChallengeLimiter()
        self._memory = DebateMemory()
        self._skill_selector = SkillSelector(
            build_skill_pool(_cfg.get_value("skills", "debater_pool", _DEFAULT_POOL)),
            debater_name=self.name,
        )

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
            f"WORD LIMIT: Your response MUST NOT exceed {_MAX_WORDS} words. Be concise.\n"
            f"{stance_directive}\n\n"
            f"RULES:\n{rules}"
        )

    def _build_skill_guidance(self, history: list[dict], round_num: int) -> tuple[str, list[str]]:
        opponent_msg = ""
        for entry in reversed(history):
            if entry.get("role") == "user":
                opponent_msg = entry.get("content", "")
                break
        self._challenge_limiter.record_turn()
        ctx = SkillContext(
            topic=self.topic, stance=self.stance,
            opponent_last_message=opponent_msg, round_num=round_num,
            skill_type=str(self.skill), transcript=history,
            metadata={"allow_source_challenge": self._challenge_limiter.should_allow()},
        )
        results = self._skill_selector.select(ctx)
        for result in results:
            if result.metadata.get("source_challenge"):
                self._challenge_limiter.record_challenge()
        selected_names = [r.skill_name for r in results if r.selected]
        self.logger.info("[%s] r%d skills: %s", self.name, round_num, selected_names or "(none)")
        parts = [r.content for r in results if r.selected and r.content]
        skill_guidance = ("\n\nSKILL GUIDANCE:\n" + "\n\n".join(parts)) if parts else ""
        memory_block = self._memory.get_memory_block(self.name)
        if memory_block:
            skill_guidance = memory_block + ("\n\n" + skill_guidance.strip() if skill_guidance else "")
        return skill_guidance, selected_names

    async def generate(self, messages: list[dict]) -> str:
        """Call the LLM and return a validated response."""
        response = await self.gatekeeper.execute(self.client.generate_response, messages)
        return self._validate_response(response)

    async def get_argument(self, history: list[dict], round_num: int = 0) -> str:
        """Direct SDK call — preserved for tests and backward compatibility."""
        enriched_history = list(history)
        has_web_evidence = False
        if round_num > 0 and self.client.__class__.__name__ != "MockAIClient":
            try:
                results = await self.search_tool.search(
                    f"{self.topic} {self.stance} evidence",
                    topic=self.topic,
                    stance=self.stance,
                    round_num=round_num,
                    seen_urls=self._memory.used_urls,
                )
                if results:
                    self._memory.register_urls([r.url for r in results])
                citation_text = self.search_tool.format_for_prompt(results)
                if citation_text:
                    has_web_evidence = True
                    enriched_history = [{"role": "user", "content": citation_text}] + enriched_history
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("[%s] web search failed (round %d): %s", self.name, round_num, exc)
        skill_guidance, selected_names = self._build_skill_guidance(enriched_history, round_num)
        messages = self._compressor.compress(enriched_history, self.system_prompt, skill_guidance)
        response = await self.generate(messages)
        previous = next((e.get("content", "") for e in reversed(enriched_history) if e.get("role") == "user"), "")
        tail = [{"role": "assistant", "content": response}]
        if validate_debate_response(response):
            response = await self.generate(messages + tail + [{"role": "user", "content": _STRICT_REWRITE}])
        if self.skill != DebaterSkill.EVIDENCE_BASED and repeated_word_run(response, previous):
            response = await self.generate(messages + tail + [{"role": "user", "content": _ECHO_REWRITE}])
        response = _fact_safety.clean(response, has_web_evidence=has_web_evidence)
        response = strip_debate_labels(response)
        response = enforce_word_limit(response, _MAX_WORDS, self.name, self.logger)
        self._memory.record_turn(self.name, response)
        if _cfg.get_value("skills", "log_skills_in_transcript", False) and selected_names:
            response += f"\n\n[Skills: {', '.join(selected_names)}]"
        return response

