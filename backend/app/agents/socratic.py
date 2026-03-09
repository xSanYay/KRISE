"""Socratic Friction Agent — challenges user assumptions to build conviction."""

from __future__ import annotations
import structlog

from app.llm.base import LLMProvider
from app.llm.prompts import (
    SOCRATIC_QUESTION_SYSTEM,
    SOCRATIC_QUESTION_PROMPT,
    CONVICTION_UPDATE_SYSTEM,
    CONVICTION_UPDATE_PROMPT,
    DECISION_SOCRATIC_SYSTEM,
    DECISION_SOCRATIC_TURN_PROMPT,
    DECISION_CONCLUSION_PROMPT,
)
from app.models.intent import IntentProfile
from app.models.session import ConversationMessage, DecisionOutcome

logger = structlog.get_logger()


class SocraticFrictionAgent:
    """Generates clarification questions to understand user needs."""

    _DECISION_STAGES = [
        ("opening", "Clarify the actual decision and force the user to explain why one option is pulling them."),
        ("clarify", "Tighten the real use case, constraints, and must-have outcomes."),
        ("challenge", "Stress-test whether the user is chasing features they will not use."),
        ("tradeoff", "Force a direct tradeoff between convenience, performance, battery, price, or ecosystem."),
        ("suggest", "Offer a sharper framing of the decision, then probe whether it actually matches their priorities."),
        ("clarify", "Resolve contradictions or vague priorities that still remain."),
        ("challenge", "Check whether identity, hype, or fear of missing out is distorting the choice."),
        ("tradeoff", "Make them choose what they are explicitly willing to lose."),
        ("suggest", "Test a narrowed recommendation or wait strategy before final verdict."),
        ("conclude", "Prepare to conclude with a verdict and next step."),
    ]

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
            conversation_summary=summary
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

    async def generate_decision_turn(
        self,
        intent_profile: IntentProfile,
        conversation_history: list[ConversationMessage],
        initial_statement: str,
        turn_number: int,
        max_turns: int,
    ) -> dict[str, str | bool]:
        """Generate the next question for dedicated decision mode."""
        stage, stage_goal = self._decision_stage(turn_number)
        summary = "\n".join(
            f"{msg.role.value}: {msg.content}" for msg in conversation_history[-10:]
        ) or "(First interaction)"

        budget = (
            f"₹{int(intent_profile.constraints.budget_max):,}"
            if intent_profile.constraints.budget_max
            else "Not specified"
        )
        brand_preferences = ", ".join(intent_profile.constraints.brand_preferences) or "None specified"
        ambiguities = ", ".join(intent_profile.ambiguities[:4]) or "None identified"

        prompt = DECISION_SOCRATIC_TURN_PROMPT.format(
            turn_number=turn_number,
            max_turns=max_turns,
            stage=stage,
            stage_goal=stage_goal,
            initial_statement=initial_statement or "Not provided",
            primary_use_case=intent_profile.primary_use_case or "Not yet clear",
            product_category=intent_profile.product_category or "Not specified",
            budget=budget,
            brand_preferences=brand_preferences,
            ambiguities=ambiguities,
            conviction_score=f"{intent_profile.conviction_score:.2f}",
            conversation_summary=summary,
        )

        result = await self._llm.generate_json(
            prompt,
            system=DECISION_SOCRATIC_SYSTEM,
            max_tokens=250,
        )

        question = str(result.get("question") or "What real problem are you solving with this purchase, and what happens if you do nothing for a week?")
        should_conclude = bool(result.get("should_conclude", False))

        logger.info("decision_turn_generated", stage=stage, turn=turn_number)

        return {
            "question": question.strip().strip('"'),
            "stage": str(result.get("stage") or stage),
            "reasoning": str(result.get("reasoning") or ""),
            "should_conclude": should_conclude,
        }

    async def finalize_decision(
        self,
        intent_profile: IntentProfile,
        conversation_history: list[ConversationMessage],
        initial_statement: str,
    ) -> DecisionOutcome:
        """Generate the final decision verdict for dedicated mode."""
        summary = "\n".join(
            f"{msg.role.value}: {msg.content}" for msg in conversation_history[-14:]
        ) or "(No conversation)"
        budget = (
            f"₹{int(intent_profile.constraints.budget_max):,}"
            if intent_profile.constraints.budget_max
            else "Not specified"
        )
        brand_preferences = ", ".join(intent_profile.constraints.brand_preferences) or "None specified"

        prompt = DECISION_CONCLUSION_PROMPT.format(
            initial_statement=initial_statement or "Not provided",
            conversation_summary=summary,
            primary_use_case=intent_profile.primary_use_case or "Not yet clear",
            product_category=intent_profile.product_category or "Not specified",
            budget=budget,
            brand_preferences=brand_preferences,
            conviction_score=f"{intent_profile.conviction_score:.2f}",
        )

        result = await self._llm.generate_json(
            prompt,
            system=DECISION_SOCRATIC_SYSTEM,
            max_tokens=500,
        )

        verdict = str(result.get("verdict") or "Probably No")
        if verdict not in {"Hard No", "Probably No", "Weak Yes", "Strong Yes"}:
            verdict = "Probably No"

        outcome = DecisionOutcome(
            verdict=verdict,
            rationale=str(result.get("rationale") or "Your reasoning is still too soft to justify buying with confidence."),
            recommendation=str(result.get("recommendation") or "Wait 72 hours, then restate the decision in one sentence and check if the tradeoff still feels worth it."),
            non_consumer_alternative=str(result.get("non_consumer_alternative") or "Delay the purchase and test whether your current setup can cover the need for one more week."),
            key_tradeoffs=[str(item) for item in (result.get("key_tradeoffs") or [])[:4]],
        )

        logger.info("decision_finalized", verdict=outcome.verdict)

        return outcome

    def _decision_stage(self, turn_number: int) -> tuple[str, str]:
        index = max(0, min(turn_number - 1, len(self._DECISION_STAGES) - 1))
        return self._DECISION_STAGES[index]
