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
from app.models.product import ProductScore
from app.llm.prompts import SWIPE_CONCLUSION_SYSTEM, SWIPE_CONCLUSION_PROMPT
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
        elif session.phase in (SessionPhase.PRODUCT_RECOMMENDATION, SessionPhase.FETCHING_PRODUCTS):
            # FETCHING_PRODUCTS can linger if a message arrives mid-fetch; treat it
            # the same as PRODUCT_RECOMMENDATION so we never hit 'Unknown session phase'.
            session.phase = SessionPhase.PRODUCT_RECOMMENDATION
            return await self._handle_product_question(message, session)
        else:
            # Fallback: if session is in an unexpected phase, try to recover gracefully
            logger.warning("unexpected_session_phase", phase=session.phase, session_id=session.id)
            session.phase = SessionPhase.PRODUCT_RECOMMENDATION
            return await self._handle_product_question(message, session)

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

        # Enforce minimum turns before allowing product search (unless user explicitly skips)
        min_turns_for_search = 2
        has_enough_turns = session.socratic_turn_count >= min_turns_for_search

        if user_wants_skip and session.socratic_turn_count >= 1:
            # User explicitly wants to skip — allow after at least 1 turn
            session.phase = SessionPhase.FETCHING_PRODUCTS
            return await self._fetch_and_score_products(session)

        if conviction >= self._settings.conviction_threshold and has_enough_turns:
            # High conviction AND enough turns — fetch products
            session.phase = SessionPhase.FETCHING_PRODUCTS
            return await self._fetch_and_score_products(session)

        elif session.socratic_turn_count >= self._settings.max_socratic_turns:
            session.phase = SessionPhase.FETCHING_PRODUCTS
            return await self._fetch_and_score_products(session)
        else:
            # Generate a targeted clarification question — the LLM may include
            # a <widget:type> tag to request an interactive widget alongside it.
            session.phase = SessionPhase.SOCRATIC_FRICTION
            session.socratic_turn_count += 1

            raw_question = await self._socratic.generate_question(
                session.intent_profile,
                session.conversation_history,
                session.socratic_turn_count,
            )

            # Parse and strip any widget tag from the LLM output
            question, widget = self._parse_widget_tag(raw_question, session)

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

        # NOTE: We intentionally do NOT run conviction scoring in decision mode.
        # The shopping-mode conviction scorer has phase gates that block decision
        # conclusions. Decision mode uses turn count + LLM should_conclude instead.

        if not session.initial_statement:
            session.initial_statement = message
            # Pre-fetch facts about mentioned products so LLM doesn't ask outdated questions
            session.decision_facts = await self._socratic.fetch_decision_facts(
                message, session.intent_profile
            )

        session.phase = SessionPhase.SOCRATIC_FRICTION
        session.decision_turn_count += 1
        max_turns = self._settings.decision_max_turns

        logger.info(
            "decision_mode_update",
            session_id=session.id,
            turn=session.decision_turn_count,
        )

        should_conclude = self._should_conclude_decision(message, session)
        if should_conclude:
            return await self._finalize_decision_mode(session)

        turn = await self._socratic.generate_decision_turn(
            session.intent_profile,
            session.conversation_history,
            session.initial_statement,
            session.decision_facts,
            session.decision_turn_count,
            max_turns,
        )
        session.decision_stage = str(turn.get("stage") or "clarify")

        if bool(turn.get("should_conclude")):
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
            conviction_score=session.intent_profile.conviction_score,
            mode=session.mode.value,
            stage=session.decision_stage,
            turn=session.decision_turn_count,
            max_turns=max_turns,
            completed=False,
        )

    def _should_conclude_decision(self, message: str, session: Session) -> bool:
        # Hard cap: always conclude at max turns
        if session.decision_turn_count >= self._settings.decision_max_turns:
            return True

        # Don't conclude too early
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
            "just conclude",
            "wrap up",
            "done",
        ]
        if any(signal in message_lower for signal in exit_signals):
            return True

        # Detect user fatigue: short/repetitive answers signal they're done exploring
        recent_user_msgs = [
            m.content for m in session.conversation_history[-8:]
            if m.role == MessageRole.USER
        ]
        if len(recent_user_msgs) >= 3:
            short_answers = sum(1 for m in recent_user_msgs[-3:] if len(m.split()) <= 8)
            if short_answers >= 3:
                return True

        return False

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

    # ── Widget tag parsing ──────────────────────────────────────────────
    _WIDGET_TAG_RE = re.compile(r'<widget:(budget|brand|category)>', re.IGNORECASE)

    def _parse_widget_tag(
        self, raw_text: str, session: Session
    ) -> tuple[str, WidgetRequest | None]:
        """Strip a <widget:type> tag from LLM output and return (clean_text, widget).

        Each widget type is only shown once per session to avoid repetition.
        """
        match = self._WIDGET_TAG_RE.search(raw_text)
        if not match:
            return raw_text.strip(), None

        widget_type = match.group(1).lower()
        clean_text = self._WIDGET_TAG_RE.sub('', raw_text).strip()
        profile = session.intent_profile

        if widget_type == 'budget':
            if session.asked_budget_widget or profile.constraints.budget_max is not None:
                return clean_text, None
            session.asked_budget_widget = True
            return clean_text, WidgetRequest(
                widget_type='budget_slider',
                label='Set your budget range',
                min_value=5000,
                max_value=200000,
                step=1000,
            )

        if widget_type == 'brand':
            # Only show brand widget if user hasn't already seen it
            # AND hasn't provided brand preferences AND we have enough context
            if session.asked_brand_widget or profile.constraints.brand_preferences or session.socratic_turn_count < 3:
                return clean_text, None
            session.asked_brand_widget = True
            brand_map = {
                'phone': ['Samsung', 'Apple', 'OnePlus', 'Xiaomi', 'Realme', 'Vivo', 'Nothing', 'No preference'],
                'laptop': ['HP', 'Dell', 'Lenovo', 'ASUS', 'Acer', 'Apple', 'MSI', 'No preference'],
                'tv': ['Samsung', 'LG', 'Sony', 'Mi', 'TCL', 'OnePlus', 'No preference'],
                'wearable': ['Apple', 'Samsung', 'Noise', 'Boat', 'Garmin', 'Fitbit', 'No preference'],
            }
            brands = brand_map.get((profile.product_category or '').lower())
            if not brands:
                return clean_text, None
            return clean_text, WidgetRequest(
                widget_type='brand_picker',
                label='Any brand preference? (pick one or more)',
                options=brands,
            )

        if widget_type == 'category':
            if profile.product_category:
                return clean_text, None
            return clean_text, WidgetRequest(
                widget_type='category_picker',
                label='What are you looking for?',
                options=['Phone', 'Laptop', 'Tablet', 'TV', 'Wearable', 'Gaming', 'Appliance'],
            )

        return clean_text, None

    def _deduplicate_and_filter(
        self, scored_products: list[ProductScore], session: Session
    ) -> list[ProductScore]:
        """Deduplicate by model base name, filter out-of-budget and already-seen products."""
        import re

        profile = session.intent_profile
        budget_max = profile.constraints.budget_max
        budget_min = getattr(profile.constraints, "budget_min", 0.0) or 0.0

        # Normalize budget values that might be in 'k' format
        if budget_max and 0 < budget_max < 1000:
            budget_max = budget_max * 1000
        if budget_min and 0 < budget_min < 1000:
            budget_min = budget_min * 1000

        # Common color names to strip
        _COLORS = (
            "black", "white", "blue", "red", "green", "grey", "gray", "gold",
            "silver", "purple", "pink", "orange", "yellow", "aqua", "mint",
            "graphite", "midnight", "starlight", "cream", "lavender", "bronze",
            "titanium", "coral", "teal", "marble", "carbon", "glacier",
            "siachen", "nitro", "sandy", "stellar", "geek", "aquamarine",
            "dark", "light", "jet", "matte", "glossy",
        )

        unique: list[ProductScore] = []
        seen_bases: set[str] = set()
        # Also gather base names from products already in the current deck
        for ps in session.product_deck:
            title = ps.product.title.lower()
            base = re.sub(r'\(.*?\)|\[.*?\]', '', title)
            base = re.sub(r'\b(' + '|'.join(_COLORS) + r')\b', '', base)
            base = re.sub(r'\b(\d+\s*gb|\d+\s*tb|\d+\s*mah|5g|4g|lte|wifi|wi-fi)\b', '', base)
            base = re.sub(r'[^a-z0-9]', '', base)
            if base:
                seen_bases.add(base)

        for ps in scored_products:
            price = ps.product.price.current

            # Strict budget filter
            if budget_max and price > budget_max:
                continue
            if budget_min and price < budget_min:
                continue

            # Skip products already shown in this session
            if ps.product.id in session.all_products_seen:
                continue

            # Normalize title to base model name
            title = ps.product.title.lower()
            base_name = re.sub(r'\(.*?\)|\[.*?\]', '', title)
            base_name = re.sub(r'\b(' + '|'.join(_COLORS) + r')\b', '', base_name)
            base_name = re.sub(r'\b(\d+\s*gb|\d+\s*tb|\d+\s*mah|5g|4g|lte|wifi|wi-fi)\b', '', base_name)
            base_name = re.sub(r'[^a-z0-9]', '', base_name)

            if base_name and base_name in seen_bases:
                continue

            if base_name:
                seen_bases.add(base_name)
            unique.append(ps)

        # Sort by score first, then by rating for review-based tie-breaking
        unique.sort(key=lambda s: (s.total_score, s.product.rating or 0), reverse=True)

        return unique

    async def _fetch_and_score_products(self, session: Session) -> MessageResponse:
        """Fetch products from scrapers, score, and return recommendations."""
        logger.info("fetching_products", session_id=session.id)
        session.progress_steps = []

        try:
            session.progress_steps.append("Generating search queries...")
            
            # If user swiped right on things previously, pass their names to guide the new search
            shortlisted_titles = []
            if hasattr(session, 'all_products_seen'):
                for pid in session.shortlist:
                    if pid in session.all_products_seen:
                        shortlisted_titles.append(session.all_products_seen[pid].product.title)
            
            products = await self._scraper.fetch_products(session.intent_profile, shortlist=shortlisted_titles)
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

            unique_products = self._deduplicate_and_filter(scored_products, session)

            session.product_deck = unique_products
            session.phase = SessionPhase.PRODUCT_RECOMMENDATION
            session.progress_steps.append("Done!")

            # Store all products in history so conclusion can reference them
            for ps in unique_products:
                session.all_products_seen[ps.product.id] = ps

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
        # Detect swipe completion or search-more request
        msg_lower = message.lower()
        finish_signals = [
            "finished shortlisting",
            "done swiping",
            "finished reviewing",
            "that's all",
            "thats all",
            "no more",
        ]
        search_more_signals = [
            "search more products",
            "find more products",
            "search more based",
            "more products based",
            "search more",
            "find more options",
            "different options",
            "other options",
        ]

        # Require the message to actually contain a search/find intent
        # to avoid casual words like "show more" or "no more" triggering re-fetch
        _search_verbs = ("search", "find", "fetch", "get", "show", "look")
        _product_nouns = ("product", "option", "item", "result", "phone", "laptop", "tablet")
        has_search_verb = any(v in msg_lower for v in _search_verbs)
        has_product_noun = any(n in msg_lower for n in _product_nouns)

        if any(signal in msg_lower for signal in search_more_signals) or (has_search_verb and has_product_noun and "more" in msg_lower):
            # User wants more products — re-fetch with refined profile
            session.phase = SessionPhase.FETCHING_PRODUCTS
            return await self._fetch_and_score_products(session)

        if any(signal in msg_lower for signal in finish_signals):
            return await self._generate_swipe_conclusion(session)

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

    async def _generate_swipe_conclusion(self, session: Session) -> MessageResponse:
        """Generate a conclusion with top 3 products after swiping is complete."""
        logger.info("generating_swipe_conclusion", session_id=session.id)

        profile = session.intent_profile
        budget = f"{int(profile.constraints.budget_max):,}" if profile.constraints.budget_max else "Not specified"

        # Build a lookup of ALL products ever seen (deck retains only unswiped ones)
        product_map: dict[str, ProductScore] = {}
        for ps in session.product_deck:
            product_map[ps.product.id] = ps
        # Also check if session stored historical products (added below in handle_swipe)
        if hasattr(session, 'all_products_seen'):
            for pid, ps in session.all_products_seen.items():
                if pid not in product_map:
                    product_map[pid] = ps

        # Build shortlisted and skipped product details using REAL data
        shortlist_details = []
        skip_details = []

        for swipe in session.swipe_history:
            ps = product_map.get(swipe.product_id)
            if ps:
                line = f"- {ps.product.title} (₹{int(ps.product.price.current):,}, Score: {ps.total_score})"
            else:
                line = f"- Product {swipe.product_id[:8]}"

            if swipe.direction == "right":
                shortlist_details.append(line)
            else:
                skip_details.append(f"{line} (reason: {swipe.reason or 'skipped'})")

        shortlisted_text = "\n".join(shortlist_details) if shortlist_details else "None shortlisted"
        skipped_text = "\n".join(skip_details[:10]) if skip_details else "None skipped"

        # Gather ALL products with real data for ranking
        all_candidate_scores: list[ProductScore] = []

        # Shortlisted products first (from swipe history)
        for swipe in session.swipe_history:
            if swipe.direction == "right":
                ps = product_map.get(swipe.product_id)
                if ps:
                    all_candidate_scores.append(ps)

        # Add remaining deck products
        for ps in session.product_deck:
            if ps.product.id not in [s.product.id for s in all_candidate_scores]:
                all_candidate_scores.append(ps)

        # Sort by score descending to get genuine top 3
        all_candidate_scores.sort(key=lambda s: s.total_score, reverse=True)
        top_3 = all_candidate_scores[:3]

        # All products text for LLM context
        all_products_text = "\n".join(
            f"- {ps.product.title} (₹{int(ps.product.price.current):,}, Score: {ps.total_score})"
            for ps in all_candidate_scores[:10]
        ) if all_candidate_scores else "No products available"

        # Swipe patterns
        skip_reasons: dict[str, int] = {}
        for swipe in session.swipe_history:
            if swipe.direction == "left":
                reason = swipe.reason or "not_interested"
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

        patterns = []
        if skip_reasons:
            top_reasons = sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True)
            patterns.append(f"Most common skip reasons: {', '.join(f'{r}({c}x)' for r, c in top_reasons[:3])}")
        patterns.append(f"Total shortlisted: {len(session.shortlist)}")
        patterns.append(f"Total skipped: {len(session.swipe_history) - len(session.shortlist)}")
        swipe_patterns_text = "\n".join(patterns)

        prompt = SWIPE_CONCLUSION_PROMPT.format(
            primary_use_case=profile.primary_use_case or "General use",
            product_category=profile.product_category or "Not specified",
            budget=budget,
            shortlisted_products=shortlisted_text,
            skipped_products=skipped_text,
            all_products=all_products_text,
            swipe_patterns=swipe_patterns_text,
        )

        try:
            result = await self._llm.generate_json(prompt, system=SWIPE_CONCLUSION_SYSTEM, max_tokens=600)
        except Exception as e:
            logger.warning("conclusion_generation_failed", error=str(e))
            result = {}

        # Build conclusion content using REAL product data, NOT LLM-hallucinated names
        conclusion_text = result.get("conclusion", "Based on your preferences, here are our top recommendations.")

        content_parts = [conclusion_text, ""]
        medals = ["🥇", "🥈", "🥉"]
        for i, ps in enumerate(top_3):
            medal = medals[i] if i < 3 else f"#{i+1}"
            price = int(ps.product.price.current)
            score = ps.total_score
            title = ps.product.title
            # Try to get LLM reason for this product, fall back to generic
            llm_reasons = result.get("top_products", [])
            reason = ""
            for lr in llm_reasons:
                if lr.get("rank") == i + 1:
                    reason = lr.get("reason", "")
                    break
            if not reason:
                reason = "Top-ranked based on your preferences and swipe patterns"
            content_parts.append(f"{medal} **{title}** — ₹{price:,} ({score}%)\n{reason}")

        content = "\n".join(content_parts)

        # Use real top 3 ProductScore objects for the conclusion
        conclusion_product_scores = top_3

        session.conversation_history.append(
            ConversationMessage(role=MessageRole.AGENT, content=content)
        )

        return MessageResponse(
            type="conclusion",
            content=content,
            intent_profile=session.intent_profile,
            conviction_score=session.intent_profile.conviction_score,
            conclusion_products=conclusion_product_scores,
            can_search_more=True,
            mode=session.mode.value,
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

        # Store product data BEFORE removing it from deck
        for ps in session.product_deck:
            if ps.product.id == swipe.product_id:
                session.all_products_seen[ps.product.id] = ps
                break

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
                # Pass shortlisted titles to guide re-search
                shortlisted_titles = [
                    session.all_products_seen[pid].product.title
                    for pid in session.shortlist
                    if pid in session.all_products_seen
                ]
                new_products = await self._scraper.fetch_products(
                    session.intent_profile, shortlist=shortlisted_titles
                )
                if new_products:
                    new_scored = await self._scoring.rank_products(new_products, session.intent_profile)
                    # Apply the SAME dedup + price + seen filter as initial fetch
                    new_unique = self._deduplicate_and_filter(new_scored, session)
                    if new_unique:
                        session.product_deck.extend(new_unique)
                        session.product_deck.sort(key=lambda s: s.total_score, reverse=True)
                        for ps in new_unique:
                            session.all_products_seen[ps.product.id] = ps
                        logger.info("deck_refilled", added=len(new_unique))
            except Exception as e:
                logger.warning("deck_refill_failed", error=str(e))

        next_product = session.product_deck[0] if session.product_deck else None

        return SwipeResponse(
            next_product=next_product,
            remaining_count=len(session.product_deck),
            updated_weights=session.intent_profile.scoring_weights,
        )
