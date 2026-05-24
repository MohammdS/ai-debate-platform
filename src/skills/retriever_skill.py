from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

if TYPE_CHECKING:
    from src.rag.rag_service import RAGService

logger = logging.getLogger(__name__)


class RetrieverSkill(BaseSkill):
    """Injects RAG-retrieved evidence passages into debater prompts."""

    name = "retriever"
    description = "Retrieves relevant passages from the knowledge base and requires citations"

    def __init__(self, rag_service: RAGService) -> None:
        self._rag = rag_service

    def can_handle(self, ctx: SkillContext) -> bool:
        return self._rag is not None and self._rag.is_ready()

    def run(self, ctx: SkillContext) -> SkillResult:
        summary = ""
        if len(ctx.transcript) >= 4:
            recent = ctx.transcript[-4:]
            summary = " ".join(e.get("content", "")[:80] for e in recent)

        query = self._rag.build_query(
            ctx.topic, ctx.stance, ctx.opponent_last_message, summary
        )
        chunks = self._rag.retrieve(query)
        if not chunks:
            return SkillResult(self.name, False, "no chunks retrieved", "")

        lines: list[str] = []
        for ch in chunks:
            snippet = ch.content.replace("\n", " ")[:300]
            lines.append(f"[source: {ch.source}] {snippet}")

        evidence_block = (
            "RETRIEVED EVIDENCE (you MUST cite every fact you use as [source: filename]):\n"
            + "\n".join(lines)
        )
        logger.debug("RetrieverSkill injected %d chunk(s)", len(chunks))
        return SkillResult(self.name, True, "evidence injected", evidence_block)
