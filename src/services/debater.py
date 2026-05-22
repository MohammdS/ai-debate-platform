from __future__ import annotations

from typing import TYPE_CHECKING

from src.ipc.message import DebateMessage, MessageType
from src.sdk.base_client import BaseAIClient
from src.services.base_agent import (
    BaseAgent,
    DebaterSkill,
    enforce_word_limit,
    get_agent_prompt,
    get_skill_instruction,
)
from src.shared.config import ConfigManager
from src.shared.gatekeeper import ApiGatekeeper
from src.tools.web_search import WebSearchTool

if TYPE_CHECKING:
    from src.ipc.channel import IpcChannel

_cfg = ConfigManager()
_MAX_WORDS: int = _cfg.get_value("debate", "debater_max_words", 120)


class Debater(BaseAgent):
    """
    Competitive AI debater — runs as an IPC process loop or direct SDK call.
    Each debater is assigned a unique DebaterSkill that shapes their rhetoric,
    ensuring genuine contradiction beyond just opposing stances.
    """

    def __init__(self, name: str, stance: str, topic: str,
                 client: BaseAIClient, gatekeeper: ApiGatekeeper,
                 skill: DebaterSkill = DebaterSkill.EVIDENCE_BASED,
                 search_tool: WebSearchTool | None = None,
                 opponent_stance: str = ""):
        super().__init__(name, client, gatekeeper)
        self.stance = stance
        self.opponent_stance = opponent_stance
        self.topic = topic
        self.skill = skill
        self.search_tool = search_tool or WebSearchTool()
        self.system_prompt = self._build_system_prompt()
        # IPC channels — assigned by DebateOrchestrator before run()
        self.inbox:  IpcChannel | None = None
        self.outbox: IpcChannel | None = None

    def _build_system_prompt(self) -> str:
        role_key = "pro" if self.skill == DebaterSkill.EVIDENCE_BASED else "contra"
        role_label = role_key.upper()
        agent_cfg = get_agent_prompt(role_key)
        skill_instruction = get_skill_instruction(self.skill)

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
            f"ROLE: {role_label} debater in a formal debate.\n"
            f"TOPIC: {self.topic}\n"
            f"{stance_directive}\n\n"
            f"{skill_instruction}\n\n"
            f"RULES:\n{rules}"
        )

    async def get_argument(self, history: list[dict], round_num: int = 0) -> str:
        """
        Direct SDK call — preserved for tests and backward compatibility.
        Enriches the prompt with live web search results every other round.
        """
        enriched_history = list(history)
        if round_num % 2 == 0:
            query = f"{self.topic} {self.stance} evidence"
            results = await self.search_tool.search(query)
            citation_text = self.search_tool.format_for_prompt(results)
            if citation_text:
                enriched_history = [
                    {"role": "user", "content": citation_text}
                ] + enriched_history

        messages = [{"role": "system", "content": self.system_prompt}] + enriched_history
        response = await self.gatekeeper.execute(self.client.generate_response, messages)
        return enforce_word_limit(response, _MAX_WORDS, self.name, self.logger)

    async def run(self) -> None:
        """
        IPC process loop.
        Blocks on inbox.receive(). On RELAY: generates argument, sends ARGUMENT
        to outbox. On SHUTDOWN: exits cleanly.
        Each debater owns its own private history — no shared state.
        """
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
                    msg_type=MessageType.ARGUMENT,
                    sender=self.name,
                    receiver="judge",
                    payload=argument,
                    round_num=msg.round_num,
                )
                await self.outbox.send(reply)
                self.logger.info(f"[{self.name}] sent ARGUMENT round {msg.round_num}")
