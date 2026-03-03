"""Agent Orchestrator — central coordinator managing the conversation flow."""

from __future__ import annotations
import structlog

from app.llm.base import LLMProvider
from app.agents.intent_mapper import IntentMapperAgent
from app.agents.socratic import SocraticFrictionAgent
from app.agents.scraper import ScraperAgent
from app.scoring.engine import ScoringEngine
from app.models.session import Session, SessionPhase, ConversationMessage, MessageRole, SwipeAction
from app.models.api import MessageResponse, SwipeResponse
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
        # Add user message to history
        session.conversation_history.append(
            ConversationMessage(role=MessageRole.USER, content=message)
        )

        logger.info(
            "processing_message",
            session_id=session.id,
            phase=session.phase.value,
            conviction=session.intent_profile.conviction_score,
        )

        # Route based on current phase
        if session.phase in (SessionPhase.INTENT_MAPPING, SessionPhase.SOCRATIC_FRICTION):
            return await self._handle_conversation_phase(message, session)
        elif session.phase == SessionPhase.PRODUCT_RECOMMENDATION:
            # User asking follow-up about products
            return await self._handle_product_question(message, session)
        else:
            return MessageResponse(type="error", content="Unknown session phase.")

    async def _handle_conversation_phase(self, message: str, session: Session) -> MessageResponse:
        """Handle intent mapping and Socratic friction phases."""
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
        if conviction >= self._settings.conviction_threshold:
            # High conviction — fetch products!
            session.phase = SessionPhase.FETCHING_PRODUCTS
            return await self._fetch_and_score_products(session)
        elif session.socratic_turn_count >= self._settings.max_socratic_turns:
            # Max friction reached — proceed anyway
            session.phase = SessionPhase.FETCHING_PRODUCTS
            return await self._fetch_and_score_products(session)
        else:
            # Generate Socratic question
            session.phase = SessionPhase.SOCRATIC_FRICTION
            session.socratic_turn_count += 1

            question = await self._socratic.generate_question(
                session.intent_profile,
                session.conversation_history,
                session.socratic_turn_count,
            )

            # Add agent response to history
            session.conversation_history.append(
                ConversationMessage(role=MessageRole.AGENT, content=question)
            )

            return MessageResponse(
                type="question",
                content=question,
                intent_profile=session.intent_profile,
                conviction_score=conviction,
            )

    async def _fetch_and_score_products(self, session: Session) -> MessageResponse:
        """Fetch products from scrapers, score, and return recommendations."""
        # Inform user we're searching
        logger.info("fetching_products", session_id=session.id)

        try:
            # Fetch products
            products = await self._scraper.fetch_products(session.intent_profile)

            if not products:
                session.phase = SessionPhase.SOCRATIC_FRICTION
                return MessageResponse(
                    type="info",
                    content="I couldn't find products matching your criteria. Could you broaden your requirements a bit?",
                    intent_profile=session.intent_profile,
                    conviction_score=session.intent_profile.conviction_score,
                )

            # Score and rank
            scored_products = await self._scoring.rank_products(products, session.intent_profile)
            session.product_deck = scored_products
            session.phase = SessionPhase.PRODUCT_RECOMMENDATION

            # Add agent message
            count = len(scored_products)
            msg = f"I found {count} products matching your needs. Here are my top picks — swipe right on ones you like, left to skip!"
            session.conversation_history.append(
                ConversationMessage(role=MessageRole.AGENT, content=msg)
            )

            return MessageResponse(
                type="recommendations",
                content=msg,
                products=scored_products[:12],  # Send top 12
                intent_profile=session.intent_profile,
                conviction_score=session.intent_profile.conviction_score,
            )
        except Exception as e:
            logger.error("product_fetch_failed", error=str(e))
            session.phase = SessionPhase.SOCRATIC_FRICTION
            return MessageResponse(
                type="error",
                content="Something went wrong while searching for products. Let me try a different approach — could you tell me more about what you need?",
                intent_profile=session.intent_profile,
                conviction_score=session.intent_profile.conviction_score,
            )

    async def _handle_product_question(self, message: str, session: Session) -> MessageResponse:
        """Handle follow-up questions about products."""
        # Simple LLM response about products in context
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

        # Find the swiped product
        swiped_product = None
        for ps in session.product_deck:
            if ps.product.id == swipe.product_id:
                swiped_product = ps.product
                break

        if swipe.direction == "right":
            # Add to shortlist
            session.shortlist.append(swipe.product_id)

        if swiped_product:
            # Update weights based on swipe
            session.intent_profile = self._scoring.update_weights_from_swipe(
                swipe.direction,
                swipe.reason,
                swiped_product,
                session.intent_profile,
            )

        # Remove swiped product from deck
        session.product_deck = [
            ps for ps in session.product_deck if ps.product.id != swipe.product_id
        ]

        # Re-score remaining products
        session.product_deck = await self._scoring.rescore_products(
            session.product_deck, session.intent_profile
        )

        next_product = session.product_deck[0] if session.product_deck else None

        return SwipeResponse(
            next_product=next_product,
            remaining_count=len(session.product_deck),
            updated_weights=session.intent_profile.scoring_weights,
        )
