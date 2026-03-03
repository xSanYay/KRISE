"""Socratic Friction Agent — challenges user assumptions to build conviction."""

from __future__ import annotations
import structlog

from app.llm.base import LLMProvider
from app.llm.prompts import (
    SOCRATIC_QUESTION_SYSTEM,
    SOCRATIC_QUESTION_PROMPT,
    CONVICTION_UPDATE_SYSTEM,
    CONVICTION_UPDATE_PROMPT,
)
from app.models.intent import IntentProfile
from app.models.session import ConversationMessage

logger = structlog.get_logger()


class SocraticFrictionAgent:
    """Generates devil's advocate questions to test user conviction."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    async def generate_question(
        self,
        intent_profile: IntentProfile,
        conversation_history: list[ConversationMessage],
        turn_number: int = 1,
    ) -> str:
        """Generate a Socratic friction question based on current intent."""
        # Summarize conversation
        summary = "\n".join(
            f"{msg.role.value}: {msg.content}" for msg in conversation_history[-8:]
        ) or "(First interaction)"

        # Build requirements string
        reqs = ", ".join(
            f"{r.name} (weight: {r.weight})" for r in intent_profile.technical_requirements[:5]
        ) or "Not yet identified"

        budget = f"₹{int(intent_profile.constraints.budget_max):,}" if intent_profile.constraints.budget_max else "Not specified"

        # Build ambiguities string
        ambiguities = ", ".join(intent_profile.ambiguities[:3]) if intent_profile.ambiguities else "None identified"

        prompt = SOCRATIC_QUESTION_PROMPT.format(
            primary_use_case=intent_profile.primary_use_case,
            product_category=intent_profile.product_category or "Not specified",
            budget=budget,
            requirements=reqs,
            ambiguities=ambiguities,
            conviction_score=f"{intent_profile.conviction_score:.2f}",
            conversation_summary=summary,
            turn_number=turn_number,
        )

        question = await self._llm.generate(prompt, system=SOCRATIC_QUESTION_SYSTEM, max_tokens=300)

        logger.info(
            "socratic_question_generated",
            turn=turn_number,
            conviction=intent_profile.conviction_score,
        )

        return question.strip().strip('"')

    async def update_conviction(
        self,
        conversation_history: list[ConversationMessage],
        current_conviction: float,
        confidence: float,
    ) -> tuple[float, str]:
        """Update conviction score based on conversation progress."""
        conv_text = "\n".join(
            f"{msg.role.value}: {msg.content}" for msg in conversation_history[-10:]
        )

        prompt = CONVICTION_UPDATE_PROMPT.format(
            conversation=conv_text,
            current_conviction=f"{current_conviction:.2f}",
            confidence=f"{confidence:.2f}",
        )

        result = await self._llm.generate_json(prompt, system=CONVICTION_UPDATE_SYSTEM, max_tokens=200)

        new_score = float(result.get("conviction_score", current_conviction))
        reasoning = result.get("reasoning", "")

        # Clamp between 0 and 1
        new_score = max(0.0, min(1.0, new_score))

        logger.info(
            "conviction_updated",
            old=current_conviction,
            new=new_score,
            reasoning=reasoning,
        )

        return new_score, reasoning
