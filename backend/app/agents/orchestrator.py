"""Agent Orchestrator — central coordinator managing the conversation flow."""

from __future__ import annotations
import structlog

from app.llm.base import LLMProvider
from app.agents.intent_mapper import IntentMapperAgent
from app.agents.socratic import SocraticFrictionAgent
from app.agents.scraper import ScraperAgent
from app.scoring.engine import ScoringEngine
from app.models.session import Session, SessionPhase, ConversationMessage, MessageRole, SwipeAction
from app.models.api import MessageResponse, SwipeResponse, WidgetRequest
from app.config import get_settings

logger = structlog.get_logger()


class Orchestrator:
    """Central coordinator managing agent lifecycle and session phases."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm
        self._intent_mapper = IntentMapperAgent(llm)
        self._socratic = SocraticFrictionAgent(llm)
        self._scraper = ScraperAgent(llm)
        self._scoring = ScoringEngine(llm)
        self._settings = get_settings()

    async def process_message(self, message: str, session: Session) -> MessageResponse:
        """Process a user message and return agent response."""
        session.conversation_history.append(
            ConversationMessage(role=MessageRole.USER, content=message)
        )

        logger.info(
            "processing_message",
            session_id=session.id,
            phase=session.phase.value,
            conviction=session.intent_profile.conviction_score,
        )

        if session.phase in (SessionPhase.INTENT_MAPPING, SessionPhase.SOCRATIC_FRICTION):
            return await self._handle_conversation_phase(message, session)
        elif session.phase == SessionPhase.PRODUCT_RECOMMENDATION:
            return await self._handle_product_question(message, session)
        else:
            return MessageResponse(type="error", content="Unknown session phase.")

    async def _handle_conversation_phase(self, message: str, session: Session) -> MessageResponse:
        """Handle intent mapping and clarification phases."""
        # Step 1: Extract/update intent profile
        profile = await self._intent_mapper.extract_intent(
            message,
            session.conversation_history,
            session.intent_profile,
        )
        session.intent_profile = profile

        # Step 2: Update conviction score
        conviction, reasoning = await self._socratic.update_conviction(
            session.conversation_history,
            profile.conviction_score,
            profile.confidence_score,
        )
        session.intent_profile.conviction_score = conviction

        logger.info(
            "conviction_update",
            session_id=session.id,
            conviction=conviction,
            threshold=self._settings.conviction_threshold,
            reasoning=reasoning,
        )

        # Step 3: Decide next action
        # Detect if user wants to skip clarification
        skip_phrases = ["go ahead", "just search", "search now", "find products", "no preference", "doesn't matter", "don't care", "proceed", "skip"]
        user_wants_skip = any(phrase in message.lower() for phrase in skip_phrases)

        if conviction >= self._settings.conviction_threshold or user_wants_skip:
            # Only ask the "before I search" clarification ONCE
            if (
                session.intent_profile.ambiguities
                and not session.asked_pre_search_clarification
                and not user_wants_skip
                and session.socratic_turn_count < self._settings.max_socratic_turns
            ):
                # Ask about remaining clarifications as a batch — but only ONE time
                remaining = session.intent_profile.ambiguities[:3]
                formatted = ", ".join(remaining)
                question = f"Before I search, I'd like to know about: {formatted}. Share any preferences, or say 'go ahead' to search now."

                session.asked_pre_search_clarification = True
                session.phase = SessionPhase.SOCRATIC_FRICTION
                session.socratic_turn_count += 1
                session.intent_profile.conviction_score = conviction

                session.conversation_history.append(
                    ConversationMessage(role=MessageRole.AGENT, content=question)
                )

                return MessageResponse(
                    type="question",
                    content=question,
                    intent_profile=session.intent_profile,
                    conviction_score=conviction,
                )

            # High conviction — fetch products!
            session.phase = SessionPhase.FETCHING_PRODUCTS
            return await self._fetch_and_score_products(session)

        elif session.socratic_turn_count >= self._settings.max_socratic_turns:
            session.phase = SessionPhase.FETCHING_PRODUCTS
            return await self._fetch_and_score_products(session)
        else:
            # Generate a targeted clarification question with optional widget
            session.phase = SessionPhase.SOCRATIC_FRICTION
            session.socratic_turn_count += 1

            question = await self._socratic.generate_question(
                session.intent_profile,
                session.conversation_history,
                session.socratic_turn_count,
            )

            # Detect if we should attach a widget for better UX
            widget = self._detect_widget(session)

            session.conversation_history.append(
                ConversationMessage(role=MessageRole.AGENT, content=question)
            )

            return MessageResponse(
                type="question",
                content=question,
                intent_profile=session.intent_profile,
                conviction_score=conviction,
                widget=widget,
            )

    def _detect_widget(self, session: Session) -> WidgetRequest | None:
        """Detect if a widget would help the user respond faster."""
        profile = session.intent_profile

        # Budget not set yet — show budget slider
        if profile.constraints.budget_max is None and session.socratic_turn_count >= 1:
            return WidgetRequest(
                widget_type="budget_slider",
                label="Set your budget range",
                min_value=5000,
                max_value=200000,
                step=1000,
            )

        # Category not confidently set — show category picker
        if not profile.product_category and session.socratic_turn_count >= 1:
            return WidgetRequest(
                widget_type="category_picker",
                label="What are you looking for?",
                options=["Phone", "Laptop", "Tablet", "TV", "Wearable", "Gaming", "Appliance"],
            )

        # Brands not specified and we have a category
        if profile.product_category and not profile.constraints.brand_preferences and session.socratic_turn_count >= 2:
            brand_map = {
                "phone": ["Samsung", "Apple", "OnePlus", "Xiaomi", "Realme", "Vivo", "Nothing", "No preference"],
                "laptop": ["HP", "Dell", "Lenovo", "ASUS", "Acer", "Apple", "MSI", "No preference"],
                "tv": ["Samsung", "LG", "Sony", "Mi", "TCL", "OnePlus", "No preference"],
                "wearable": ["Apple", "Samsung", "Noise", "Boat", "Garmin", "Fitbit", "No preference"],
            }
            brands = brand_map.get(profile.product_category.lower(), None)
            if brands:
                return WidgetRequest(
                    widget_type="brand_picker",
                    label="Any brand preference? (pick one or more)",
                    options=brands,
                )

        return None

    async def _fetch_and_score_products(self, session: Session) -> MessageResponse:
        """Fetch products from scrapers, score, and return recommendations."""
        logger.info("fetching_products", session_id=session.id)
        session.progress_steps = []

        try:
            session.progress_steps.append("Generating search queries...")
            products = await self._scraper.fetch_products(session.intent_profile)
            session.progress_steps.append(f"Found {len(products)} products")

            if not products:
                # Instead of generic error, ask about specific features to help refine
                session.phase = SessionPhase.SOCRATIC_FRICTION

                # Build a targeted follow-up based on what we know
                category = session.intent_profile.product_category or "product"
                budget = session.intent_profile.constraints.budget_max

                if budget and budget < 1000:
                    budget = budget * 1000  # Fix 25k -> 25000

                suggestions = []
                if not session.intent_profile.constraints.brand_preferences:
                    suggestions.append("preferred brands")
                if not session.intent_profile.technical_requirements:
                    suggestions.append("must-have features (e.g., camera quality, battery life, storage)")
                if budget is None:
                    suggestions.append("budget range")

                if suggestions:
                    question = f"I'm having trouble finding the right {category}s. To narrow down better, could you tell me about: {', '.join(suggestions)}?"
                else:
                    question = f"Let me try different search terms. Could you describe in a few words the most important thing this {category} needs to do well?"

                session.conversation_history.append(
                    ConversationMessage(role=MessageRole.AGENT, content=question)
                )

                return MessageResponse(
                    type="question",
                    content=question,
                    intent_profile=session.intent_profile,
                    conviction_score=session.intent_profile.conviction_score,
                )

            session.progress_steps.append("Scoring and ranking products...")
            scored_products = await self._scoring.rank_products(products, session.intent_profile)
            session.product_deck = scored_products
            session.phase = SessionPhase.PRODUCT_RECOMMENDATION
            session.progress_steps.append("Done!")

            count = len(scored_products)
            msg = f"Found {count} products matching your needs. Swipe right to shortlist, left to skip."
            session.conversation_history.append(
                ConversationMessage(role=MessageRole.AGENT, content=msg)
            )

            return MessageResponse(
                type="recommendations",
                content=msg,
                products=scored_products[:12],
                intent_profile=session.intent_profile,
                conviction_score=session.intent_profile.conviction_score,
            )
        except Exception as e:
            logger.error("product_fetch_failed", error=str(e))
            session.phase = SessionPhase.SOCRATIC_FRICTION

            question = "I had trouble searching right now. Could you describe in different words what you're looking for? For example, mention the brand or specific model you have in mind."
            session.conversation_history.append(
                ConversationMessage(role=MessageRole.AGENT, content=question)
            )

            return MessageResponse(
                type="question",
                content=question,
                intent_profile=session.intent_profile,
                conviction_score=session.intent_profile.conviction_score,
            )

    async def _handle_product_question(self, message: str, session: Session) -> MessageResponse:
        """Handle follow-up questions about products."""
        products_context = "\n".join(
            f"- {ps.product.title} (₹{int(ps.product.price.current)}, Score: {ps.total_score})"
            for ps in session.product_deck[:5]
        )

        prompt = f"""The user asked about products. Here are the top recommendations:
{products_context}

User's use case: {session.intent_profile.primary_use_case}
User question: "{message}"

Give a helpful, concise answer."""

        response = await self._llm.generate(prompt, max_tokens=300)

        session.conversation_history.append(
            ConversationMessage(role=MessageRole.AGENT, content=response)
        )

        return MessageResponse(
            type="info",
            content=response,
            intent_profile=session.intent_profile,
            products=session.product_deck[:12],
            conviction_score=session.intent_profile.conviction_score,
        )

    async def handle_swipe(self, session: Session, swipe: SwipeAction) -> SwipeResponse:
        """Process a swipe action and re-rank products."""
        session.swipe_history.append(swipe)

        swiped_product = None
        for ps in session.product_deck:
            if ps.product.id == swipe.product_id:
                swiped_product = ps.product
                break

        if swipe.direction == "right":
            session.shortlist.append(swipe.product_id)

        if swiped_product:
            session.intent_profile = self._scoring.update_weights_from_swipe(
                swipe.direction,
                swipe.reason,
                swiped_product,
                session.intent_profile,
            )

        session.product_deck = [
            ps for ps in session.product_deck if ps.product.id != swipe.product_id
        ]

        session.product_deck = await self._scoring.rescore_products(
            session.product_deck, session.intent_profile
        )

        # If deck is running low, trigger background re-fetch
        if len(session.product_deck) <= 3:
            logger.info("deck_low_refetching", remaining=len(session.product_deck))
            try:
                new_products = await self._scraper.fetch_products(session.intent_profile)
                existing_titles = {ps.product.title.lower()[:50] for ps in session.product_deck}
                new_unique = [p for p in new_products if p.title.lower()[:50] not in existing_titles]
                if new_unique:
                    new_scored = await self._scoring.rank_products(new_unique, session.intent_profile)
                    session.product_deck.extend(new_scored)
                    session.product_deck.sort(key=lambda s: s.total_score, reverse=True)
                    logger.info("deck_refilled", added=len(new_scored))
            except Exception as e:
                logger.warning("deck_refill_failed", error=str(e))

        next_product = session.product_deck[0] if session.product_deck else None

        return SwipeResponse(
            next_product=next_product,
            remaining_count=len(session.product_deck),
            updated_weights=session.intent_profile.scoring_weights,
        )
