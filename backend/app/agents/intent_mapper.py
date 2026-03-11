"""Intent Mapper Agent — translates user goals into technical specs."""

from __future__ import annotations
import structlog

from app.llm.base import LLMProvider
from app.llm.prompts import (
    INTENT_EXTRACTION_SYSTEM,
    INTENT_EXTRACTION_PROMPT,
)
from app.models.intent import IntentProfile, TechnicalRequirement, Constraint
from app.models.session import ConversationMessage

logger = structlog.get_logger()


class IntentMapperAgent:
    """Extracts structured intent profiles from natural language."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    async def extract_intent(
        self,
        user_message: str,
        conversation_history: list[ConversationMessage] | None = None,
        existing_profile: IntentProfile | None = None,
    ) -> IntentProfile:
        """Extract or update intent profile from user message."""
        # Build conversation context
        context = ""
        if conversation_history:
            context = "\n".join(
                f"{msg.role.value}: {msg.content}" for msg in conversation_history[-6:]
            )
        if not context:
            context = "(No prior conversation)"

        prompt = INTENT_EXTRACTION_PROMPT.format(
            user_message=user_message,
            conversation_context=context,
        )

        result = await self._llm.generate_json(prompt, system=INTENT_EXTRACTION_SYSTEM)

        if "error" in result:
            logger.error("intent_extraction_failed", error=result["error"])
            # Return existing profile or minimal profile
            if existing_profile:
                return existing_profile
            return IntentProfile(
                primary_use_case="general",
                confidence_score=0.3,
                ambiguities=["Failed to parse user intent — needs clarification"],
            )

        # Build profile from LLM response
        profile = self._build_profile(result, existing_profile)

        logger.info(
            "intent_extracted",
            use_case=profile.primary_use_case,
            category=profile.product_category,
            confidence=profile.confidence_score,
            num_requirements=len(profile.technical_requirements),
        )

        return profile

    def _build_profile(
        self, data: dict, existing: IntentProfile | None = None
    ) -> IntentProfile:
        """Build IntentProfile from LLM JSON output, merging with existing if available."""
        # Parse technical requirements
        tech_reqs = []
        for req in (data.get("technical_requirements") or []):
            if isinstance(req, dict):
                tech_reqs.append(TechnicalRequirement(
                    name=req.get("name") or "",
                    min_value=str(req.get("min_value", "")) if req.get("min_value") else None,
                    weight=float(req.get("weight") or 0.5),
                    required=bool(req.get("required") or False),
                ))

        # Parse constraints
        constraints_data = data.get("constraints") or {}
        constraints = Constraint(
            budget_max=constraints_data.get("budget_max"),
            budget_flexible=constraints_data.get("budget_flexible") if constraints_data.get("budget_flexible") is not None else True,
            brand_preferences=constraints_data.get("brand_preferences") or [],
            brand_aversions=constraints_data.get("brand_aversions") or [],
        )

        confidence = float(data.get("confidence_score") or 0.5)

        profile = IntentProfile(
            primary_use_case=data.get("primary_use_case") or "general",
            secondary_use_cases=data.get("secondary_use_cases") or [],
            product_category=data.get("product_category") or "",
            technical_requirements=tech_reqs,
            constraints=constraints,
            deal_breakers=data.get("deal_breakers") or [],
            nice_to_haves=data.get("nice_to_haves") or [],
            ambiguities=data.get("ambiguities") or [],
            confidence_score=confidence,
            conviction_score=min(confidence, 0.6),  # Start lower than confidence
        )

        # Merge with existing profile if available
        if existing:
            profile.scoring_weights = existing.scoring_weights
            profile.brand_scores = existing.brand_scores
            # Keep higher conviction if existing was higher
            if existing.conviction_score > profile.conviction_score:
                profile.conviction_score = existing.conviction_score

        # Filter out ambiguities that are already resolved
        profile.ambiguities = self._filter_resolved_ambiguities(profile)

        return profile

    @staticmethod
    def _filter_resolved_ambiguities(profile: IntentProfile) -> list[str]:
        """Remove ambiguities for fields that already have values."""
        resolved_keywords: list[tuple[bool, list[str]]] = [
            (
                profile.constraints.budget_max is not None,
                ["budget", "price", "cost", "spend", "afford", "range"],
            ),
            (
                bool(profile.product_category),
                ["category", "type of product", "looking for", "phone or laptop"],
            ),
            (
                bool(profile.constraints.brand_preferences),
                ["brand", "manufacturer", "prefer.*brand"],
            ),
            (
                bool(profile.primary_use_case and profile.primary_use_case != "general"),
                ["use case", "purpose", "primary use", "main use"],
            ),
        ]

        filtered: list[str] = []
        for ambiguity in profile.ambiguities:
            amb_lower = ambiguity.lower()
            skip = False
            for is_resolved, keywords in resolved_keywords:
                if is_resolved and any(kw in amb_lower for kw in keywords):
                    skip = True
                    break
            if not skip:
                filtered.append(ambiguity)

        # If category, use case, and budget are all known, keep only truly critical items
        core_known = (
            bool(profile.product_category)
            and bool(profile.primary_use_case and profile.primary_use_case != "general")
            and profile.constraints.budget_max is not None
        )
        if core_known:
            # Only keep ambiguities that are genuinely blocking (max 1)
            filtered = filtered[:1]

        return filtered
