"""Socratic Friction Agent — challenges user assumptions to build conviction."""

from __future__ import annotations
import re
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
from app.models.session import ConversationMessage, MessageRole, DecisionOutcome
from app.websearch.search import WebSearcher

logger = structlog.get_logger()

# Brands and model patterns worth searching for
_PRODUCT_PATTERN = re.compile(
    r"\b("
    r"iphone\s*\d*\s*(pro|plus|max|mini)?|"
    r"galaxy\s+[a-z]*\s*\d+\s*(ultra|plus|fe)?|"
    r"pixel\s+\d+\s*(pro|a)?|"
    r"oneplus\s+\d+\s*(pro|r|t)?|"
    r"nothing\s+phone|macbook\s*(pro|air|mini)?|"
    r"apple|samsung|google|oneplus|realme|redmi|xiaomi|motorola|asus|"
    r"dell|hp|lenovo|sony|lg|boat|jbl|bose|dyson|whirlpool|voltas|haier|"
    r"godrej|oppo|vivo|noise|mi\s+\d"
    r")\b",
    re.IGNORECASE,
)


class SocraticFrictionAgent:
    """Generates clarification questions to understand user needs."""

    _DECISION_STAGES = [
        ("discover", "Ask what's pulling them toward each option. Use their words, not spec sheets."),
        ("discover", "Dig into the core tension: price vs feature, ecosystem vs accuracy, etc."),
        ("tradeoff", "Force the user to choose: reference what they said and ask which matters MORE."),
        ("tradeoff", "If they're still torn, frame it as a direct either/or using their own stated priorities."),
        ("decide", "Summarize what they've said and ask: based on all this, which way are you leaning?"),
        ("decide", "If still undecided, give them the final framing and conclude."),
        ("conclude", "Conclude the session with a verdict."),
        ("conclude", "Final conclusion."),
    ]

    def __init__(self, llm: LLMProvider, web_searcher: WebSearcher | None = None):
        self._llm = llm
        self._searcher = web_searcher

    # ------------------------------------------------------------------
    # Web context helpers
    # ------------------------------------------------------------------

    def _detect_search_subject(
        self,
        conversation_history: list[ConversationMessage],
        intent_profile: IntentProfile,
    ) -> str | None:
        """Return a concise search subject if there's something worth verifying."""
        recent_text = " ".join(
            msg.content for msg in conversation_history[-4:]
            if msg.role == MessageRole.USER
        )
        match = _PRODUCT_PATTERN.search(recent_text)
        if match:
            brand_or_model = match.group(0).strip()
            # Tack on the product category for a tighter query
            if intent_profile.product_category:
                return f"{brand_or_model} {intent_profile.product_category}"
            return brand_or_model
        return None

    async def _fetch_web_context(
        self,
        conversation_history: list[ConversationMessage],
        intent_profile: IntentProfile,
    ) -> str:
        """Return a short bullet summary of live web findings, or empty string."""
        if self._searcher is None:
            return ""
        subject = self._detect_search_subject(conversation_history, intent_profile)
        if not subject:
            return ""
        results = await self._searcher.fact_check(subject, max_results=5)
        if not results:
            return ""
        bullets = []
        for r in results[:3]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            line = f"- {title}: {snippet}".strip(" -:")
            if line:
                bullets.append(line)
        if not bullets:
            return ""
        context = "Current web findings:\n" + "\n".join(bullets)
        logger.info("web_context_fetched", subject=subject, hits=len(bullets))
        return context

    async def fetch_decision_facts(
        self,
        initial_statement: str,
        intent_profile: IntentProfile,
    ) -> str:
        """Upfront DDG search for all products named in the initial decision statement.

        Runs once at the start of a Socratic decision session and returns verified
        facts (OS, key specs, price range, known issues) so the LLM never has to
        ask about things it should already know from search results.
        """
        if self._searcher is None:
            return ""

        # Extract all product mentions from the initial statement
        matches = _PRODUCT_PATTERN.findall(initial_statement)
        product_terms = list(dict.fromkeys(m[0] if isinstance(m, tuple) else m for m in matches))

        category = intent_profile.product_category or ""
        if not product_terms:
            # Fall back to category + initial statement keywords
            words = [w for w in initial_statement.split() if len(w) > 4]
            product_terms = words[:3]

        if not product_terms:
            return ""

        # Build a comparison query covering all mentioned products
        query_subject = " vs ".join(product_terms[:3])
        if category:
            query_subject = f"{query_subject} {category}"
        query = f"{query_subject} specs OS features India 2024 2025"

        try:
            results = await self._searcher.fact_check(query_subject, max_results=6)
        except Exception as e:
            logger.warning("decision_facts_fetch_failed", error=str(e))
            return ""

        if not results:
            return ""

        bullets = []
        for r in results[:5]:
            snippet = r.get("snippet", "").strip()
            title = r.get("title", "").strip()
            if snippet:
                bullets.append(f"- {title}: {snippet}")

        if not bullets:
            return ""

        context = f"Verified facts about: {query_subject}\n" + "\n".join(bullets)
        logger.info("decision_facts_fetched", subject=query_subject, hits=len(bullets))
        return context

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

        web_context = await self._fetch_web_context(conversation_history, intent_profile)

        prompt = SOCRATIC_QUESTION_PROMPT.format(
            primary_use_case=intent_profile.primary_use_case,
            product_category=intent_profile.product_category or "Not specified",
            budget=budget,
            requirements=reqs,
            ambiguities=ambiguities,
            conviction_score=f"{intent_profile.conviction_score:.2f}",
            conversation_summary=summary,
            web_context=web_context,
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
        decision_facts: str,
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

        live_context = await self._fetch_web_context(conversation_history, intent_profile)
        web_context = "\n".join([decision_facts, live_context]).strip()

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
            web_context=web_context,
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
