"""Agent Orchestrator — central coordinator managing the conversation flow."""

from __future__ import annotations
import re
import structlog

from app.llm.base import LLMProvider
from app.llm.factory import make_small_talk_llm
from app.agents.intent_mapper import IntentMapperAgent
from app.agents.socratic import SocraticFrictionAgent
from app.agents.scraper import ScraperAgent
from app.scoring.engine import ScoringEngine
from app.websearch.search import WebSearcher
from app.models.session import Session, SessionMode, SessionPhase, ConversationMessage, MessageRole, SwipeAction
from app.models.api import MessageResponse, SwipeResponse, WidgetRequest
from app.config import get_settings

logger = structlog.get_logger()


class Orchestrator:
    """Central coordinator managing agent lifecycle and session phases."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm
        self._small_talk_llm: LLMProvider | None = None
        self._intent_mapper = IntentMapperAgent(llm)
        self._web_searcher = WebSearcher()
        self._socratic = SocraticFrictionAgent(llm, web_searcher=self._web_searcher)
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
            mode=session.mode.value,
            phase=session.phase.value,
            conviction=session.intent_profile.conviction_score,
        )

        if self._is_small_talk_message(message, session):
            return await self._handle_small_talk(message, session)

        if session.mode == SessionMode.SOCRATIC_DECISION:
            return await self._handle_decision_mode(message, session)

        if session.phase in (SessionPhase.INTENT_MAPPING, SessionPhase.SOCRATIC_FRICTION):
            return await self._handle_conversation_phase(message, session)
        elif session.phase == SessionPhase.PRODUCT_RECOMMENDATION:
            return await self._handle_product_question(message, session)
        else:
            return MessageResponse(type="error", content="Unknown session phase.", mode=session.mode.value)

    def _is_small_talk_message(self, message: str, session: Session) -> bool:
        """Route casual chatter to a lightweight model without interrupting buying flows."""
        if not self._settings.small_talk_enabled:
            return False

        if session.mode != SessionMode.STANDARD:
            return False

        text = (message or "").strip().lower()
        if len(text) < self._settings.small_talk_min_chars:
            return False

        # If user has already moved into product recommendation, prefer contextual answers.
        if session.phase == SessionPhase.PRODUCT_RECOMMENDATION:
            return False

        product_intent_pattern = (
            r"\b(phone|laptop|tablet|tv|camera|headphone|earbuds|budget|under\s+\d|"
            r"price|compare|spec|ram|storage|battery|search|recommend|buy)\b"
        )
        if re.search(product_intent_pattern, text):
            return False

        if len(text.split()) > 24:
            return False

        small_talk_patterns = [
            r"^(hi|hello|hey|yo|namaste|hola)\b",
            r"\b(how are you|how's it going|how do you do|what's up|whats up)\b",
            r"\b(thanks|thank you|cool|awesome|nice|great)\b",
            r"\b(tell me a joke|joke|fun fact|who are you|what can you do)\b",
            r"\b(good morning|good afternoon|good evening|good night)\b",
        ]
        return any(re.search(pattern, text) for pattern in small_talk_patterns)

    async def _handle_small_talk(self, message: str, session: Session) -> MessageResponse:
        """Handle lightweight chatter with a dedicated low-cost Gemini model."""
        if self._small_talk_llm is None:
            self._small_talk_llm = make_small_talk_llm()

        system = (
            "You are a friendly assistant. Keep replies concise (1-3 short sentences), "
            "helpful, and warm. If user asks product-research questions, ask them to share "
            "category and budget in one sentence."
        )

        try:
            if self._small_talk_llm is None:
                raise RuntimeError("Small-talk model is unavailable")
            response = await self._small_talk_llm.generate(message, system=system, max_tokens=180)
        except Exception as exc:
            logger.warning("small_talk_fallback", error=str(exc))
            response = await self._llm.generate(message, system=system, max_tokens=180)

        session.conversation_history.append(
            ConversationMessage(
                role=MessageRole.AGENT,
                content=response,
                metadata={"type": "small_talk"},
            )
        )

        return MessageResponse(
            type="info",
            content=response,
            intent_profile=session.intent_profile,
            conviction_score=session.intent_profile.conviction_score,
            mode=session.mode.value,
        )

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
            # High conviction — fetch products immediately, no extra gating
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
                mode=session.mode.value,
            )

    async def _handle_decision_mode(self, message: str, session: Session) -> MessageResponse:
        """Handle dedicated Socratic decision-coaching mode."""
        if session.decision_complete and session.decision_outcome:
            content = (
                f"**{session.decision_outcome.verdict}**\n\n"
                f"{session.decision_outcome.rationale}\n\n"
                f"Next step: {session.decision_outcome.recommendation}\n"
                f"Alternative: {session.decision_outcome.non_consumer_alternative}"
            )
            return MessageResponse(
                type="info",
                content=content,
                intent_profile=session.intent_profile,
                conviction_score=session.intent_profile.conviction_score,
                mode=session.mode.value,
                stage="conclusion",
                turn=session.decision_turn_count,
                max_turns=self._settings.decision_max_turns,
                completed=True,
                decision_outcome=session.decision_outcome,
            )

        profile = await self._intent_mapper.extract_intent(
            message,
            session.conversation_history,
            session.intent_profile,
        )
        session.intent_profile = profile

        conviction, reasoning = await self._socratic.update_conviction(
            session.conversation_history,
            profile.conviction_score,
            profile.confidence_score,
        )
        session.intent_profile.conviction_score = conviction

        if not session.initial_statement:
            session.initial_statement = message

        session.phase = SessionPhase.SOCRATIC_FRICTION
        session.decision_turn_count += 1
        max_turns = self._settings.decision_max_turns

        logger.info(
            "decision_mode_update",
            session_id=session.id,
            turn=session.decision_turn_count,
            conviction=conviction,
            reasoning=reasoning,
        )

        should_conclude = self._should_conclude_decision(message, session)
        if should_conclude:
            return await self._finalize_decision_mode(session)

        turn = await self._socratic.generate_decision_turn(
            session.intent_profile,
            session.conversation_history,
            session.initial_statement,
            session.decision_turn_count,
            max_turns,
        )
        session.decision_stage = str(turn.get("stage") or "clarify")

        if bool(turn.get("should_conclude")) and session.decision_turn_count >= self._settings.decision_min_turns_before_conclusion:
            return await self._finalize_decision_mode(session)

        question = str(turn.get("question") or "What exactly are you trying to avoid regretting here?")
        session.conversation_history.append(
            ConversationMessage(
                role=MessageRole.AGENT,
                content=question,
                metadata={
                    "mode": session.mode.value,
                    "stage": session.decision_stage,
                    "turn": session.decision_turn_count,
                },
            )
        )

        return MessageResponse(
            type="question",
            content=question,
            intent_profile=session.intent_profile,
            conviction_score=conviction,
            mode=session.mode.value,
            stage=session.decision_stage,
            turn=session.decision_turn_count,
            max_turns=max_turns,
            completed=False,
        )

    def _should_conclude_decision(self, message: str, session: Session) -> bool:
        if session.decision_turn_count >= self._settings.decision_max_turns:
            return True

        if session.decision_turn_count < self._settings.decision_min_turns_before_conclusion:
            return False

        message_lower = message.lower()
        exit_signals = [
            "i've decided",
            "i have decided",
            "that's enough",
            "thats enough",
            "make the call",
            "give me the verdict",
            "i'm clear now",
            "im clear now",
        ]
        if any(signal in message_lower for signal in exit_signals):
            return True

        return session.intent_profile.conviction_score >= self._settings.decision_conclusion_threshold

    async def _finalize_decision_mode(self, session: Session) -> MessageResponse:
        session.decision_complete = True
        session.decision_stage = "conclusion"

        outcome = await self._socratic.finalize_decision(
            session.intent_profile,
            session.conversation_history,
            session.initial_statement,
        )
        session.decision_outcome = outcome

        content = (
            f"**{outcome.verdict}**\n\n"
            f"{outcome.rationale}\n\n"
            f"Next step: {outcome.recommendation}\n"
            f"Alternative: {outcome.non_consumer_alternative}"
        )

        session.conversation_history.append(
            ConversationMessage(
                role=MessageRole.AGENT,
                content=content,
                metadata={
                    "mode": session.mode.value,
                    "stage": session.decision_stage,
                    "turn": session.decision_turn_count,
                    "completed": True,
                },
            )
        )

        return MessageResponse(
            type="info",
            content=content,
            intent_profile=session.intent_profile,
            conviction_score=session.intent_profile.conviction_score,
            mode=session.mode.value,
            stage=session.decision_stage,
            turn=session.decision_turn_count,
            max_turns=self._settings.decision_max_turns,
            completed=True,
            decision_outcome=outcome,
        )

    def _detect_widget(self, session: Session) -> WidgetRequest | None:
        """Detect if a widget would help the user respond faster."""
        profile = session.intent_profile

        # Budget not set yet — show budget slider (only once)
        if profile.constraints.budget_max is None and session.socratic_turn_count >= 1 and not session.asked_budget_widget:
            session.asked_budget_widget = True
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

        # Brands not specified and we have a category — show only once
        if (
            profile.product_category
            and not profile.constraints.brand_preferences
            and not session.asked_brand_widget
            and session.socratic_turn_count >= 2
        ):
            brand_map = {
                "phone": ["Samsung", "Apple", "OnePlus", "Xiaomi", "Realme", "Vivo", "Nothing", "No preference"],
                "laptop": ["HP", "Dell", "Lenovo", "ASUS", "Acer", "Apple", "MSI", "No preference"],
                "tv": ["Samsung", "LG", "Sony", "Mi", "TCL", "OnePlus", "No preference"],
                "wearable": ["Apple", "Samsung", "Noise", "Boat", "Garmin", "Fitbit", "No preference"],
            }
            brands = brand_map.get(profile.product_category.lower(), None)
            if brands:
                session.asked_brand_widget = True
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
                # All scraping layers failed (live sites blocked, DDG rate-limited, LLM also returned nothing)
                # This is extremely unlikely given the LLM fallback, but handle it gracefully
                session.phase = SessionPhase.SOCRATIC_FRICTION
                category = session.intent_profile.product_category or "product"
                question = (
                    f"I wasn't able to pull live listings right now due to a network issue. "
                    f"Could you name one or two specific {category} models you've already looked at? "
                    f"That'll help me give you a direct comparison."
                )
                session.conversation_history.append(
                    ConversationMessage(role=MessageRole.AGENT, content=question)
                )

                return MessageResponse(
                    type="question",
                    content=question,
                    intent_profile=session.intent_profile,
                    conviction_score=session.intent_profile.conviction_score,
                    mode=session.mode.value,
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
                mode=session.mode.value,
            )
        except Exception as e:
            logger.error("product_fetch_failed", error=str(e))
            # Even on exception, try to score whatever partial data may have been gathered
            # and surface a clear error without looping back to questions
            session.phase = SessionPhase.SOCRATIC_FRICTION
            question = (
                "I hit a technical issue fetching live prices. "
                "Could you name one or two specific models you've been considering? "
                "I'll give you a direct comparison based on what I know."
            )
            session.conversation_history.append(
                ConversationMessage(role=MessageRole.AGENT, content=question)
            )
            return MessageResponse(
                type="question",
                content=question,
                intent_profile=session.intent_profile,
                conviction_score=session.intent_profile.conviction_score,
                mode=session.mode.value,
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
