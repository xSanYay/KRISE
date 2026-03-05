"""Weighted Scoring Engine — ranks products based on multi-factor algorithm."""

from __future__ import annotations
import structlog

from app.llm.base import LLMProvider
from app.llm.prompts import PRODUCT_EXPLANATION_PROMPT
from app.models.intent import IntentProfile
from app.models.product import Product, ProductScore

logger = structlog.get_logger()


class ScoringEngine:
    """Multi-factor product scoring and ranking engine."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    async def rank_products(
        self, products: list[Product], intent_profile: IntentProfile
    ) -> list[ProductScore]:
        """Score and rank products based on intent profile."""
        scored = []

        for product in products:
            tech_score = self._calculate_technical_match(product, intent_profile)
            sentiment_score = self._calculate_sentiment_score(product)
            vfm_score = self._calculate_vfm(product, intent_profile)
            availability_score = self._calculate_availability(product)

            weights = intent_profile.scoring_weights
            total = (
                tech_score * weights.get("technical_match", 0.40)
                + sentiment_score * weights.get("sentiment", 0.30)
                + vfm_score * weights.get("value_for_money", 0.20)
                + availability_score * weights.get("availability", 0.10)
            )

            # Deal-breaker check
            if self._has_deal_breakers(product, intent_profile):
                total = 0

            scored.append(ProductScore(
                product=product,
                total_score=round(total, 1),
                technical_match=round(tech_score, 1),
                sentiment_score=round(sentiment_score, 1),
                value_for_money=round(vfm_score, 1),
                availability_score=round(availability_score, 1),
            ))

        # Sort by total score descending
        scored.sort(key=lambda s: s.total_score, reverse=True)

        # Generate explanations for top products
        for ps in scored[:5]:
            ps.explanation = await self._generate_explanation(ps, intent_profile)

        logger.info("scoring_complete", total_products=len(scored))
        return scored

    def _calculate_technical_match(self, product: Product, profile: IntentProfile) -> float:
        """Calculate how well product specs match requirements (0-100)."""
        if not profile.technical_requirements:
            # No specific requirements — give baseline score based on rating
            return (product.rating or 3.5) / 5.0 * 80

        score = 0.0
        total_weight = 0.0

        for req in profile.technical_requirements:
            weight = req.weight
            total_weight += weight

            # Check if product has this spec
            spec_value = product.specifications.get(req.name, "")

            if spec_value:
                # Product has the spec — give full match
                score += 100 * weight
            elif req.required:
                # Required spec missing — penalty
                score += 0
            else:
                # Optional spec missing — partial score
                score += 30 * weight

        if total_weight > 0:
            return (score / total_weight)
        return 50  # Default baseline

    def _calculate_sentiment_score(self, product: Product) -> float:
        """Calculate sentiment score (0-100) from aggregated reviews."""
        sentiment = product.sentiment

        if sentiment.sample_size == 0:
            # No sentiment data — use marketplace rating as proxy
            if product.rating:
                return (product.rating / 5.0) * 80
            return 50  # Neutral

        base_score = sentiment.overall_score * 100

        # Penalty for hidden issues
        issue_penalty = len(sentiment.hidden_issues) * 5
        base_score = max(base_score - issue_penalty, 0)

        return min(base_score, 100)

    def _calculate_vfm(self, product: Product, profile: IntentProfile) -> float:
        """Calculate value-for-money score (0-100)."""
        price = product.price.current
        budget = profile.constraints.budget_max
        if budget is not None and 0 < budget < 1000:
            budget *= 1000  # Handle '25k' parsed as 25

        if not budget:
            # No budget constraint — moderate VFM
            if product.rating:
                return (product.rating / 5.0) * 70
            return 50

        if price <= 0:
            return 0

        # Price-to-budget ratio
        ratio = price / budget

        if ratio <= 0.6:
            vfm = 95  # Well under budget
        elif ratio <= 0.8:
            vfm = 85  # Good value
        elif ratio <= 1.0:
            vfm = 70  # At budget
        elif ratio <= 1.15:
            vfm = 50  # Slightly over budget
        elif ratio <= 1.3:
            vfm = 30  # Over budget
        else:
            vfm = 10  # Way over budget

        # Bonus for discounted products
        if product.price.discount_percent and product.price.discount_percent > 10:
            vfm = min(vfm + 10, 100)

        return vfm

    def _calculate_availability(self, product: Product) -> float:
        """Calculate availability score (0-100)."""
        if product.availability == "in_stock":
            return 80
        elif product.availability == "pre_order":
            return 40
        elif product.availability == "out_of_stock":
            return 0
        return 50  # Unknown

    def _has_deal_breakers(self, product: Product, profile: IntentProfile) -> bool:
        """Check if product hits any deal-breaker criteria."""
        price = product.price.current
        budget = profile.constraints.budget_max
        if budget is not None and 0 < budget < 1000:
            budget *= 1000  # Handle '25k' parsed as 25

        # Way over budget (>50% over)
        if budget and price > budget * 1.5:
            return True

        # Brand aversion
        if profile.constraints.brand_aversions:
            for brand in profile.constraints.brand_aversions:
                if brand.lower() in product.brand.lower():
                    return True

        return False

    async def _generate_explanation(self, ps: ProductScore, profile: IntentProfile) -> str:
        """Generate a 'Why this product?' explanation."""
        specs_str = ", ".join(f"{k}: {v}" for k, v in list(ps.product.specifications.items())[:5])
        budget = str(int(profile.constraints.budget_max)) if profile.constraints.budget_max else "not set"

        prompt = PRODUCT_EXPLANATION_PROMPT.format(
            product_title=ps.product.title,
            price=int(ps.product.price.current),
            specs=specs_str or "Not detailed",
            use_case=profile.primary_use_case,
            budget=budget,
            score=int(ps.total_score),
        )

        try:
            explanation = await self._llm.generate(prompt, max_tokens=100)
            return explanation.strip().strip('"')
        except Exception:
            return f"Scores {int(ps.total_score)}% match for {profile.primary_use_case}."

    def update_weights_from_swipe(
        self,
        direction: str,
        reason: str | None,
        product: Product,
        profile: IntentProfile,
    ) -> IntentProfile:
        """Update scoring weights based on swipe feedback."""
        weights = profile.scoring_weights

        if direction == "left":
            if reason == "too_expensive":
                weights["value_for_money"] = min(weights.get("value_for_money", 0.20) * 1.2, 0.5)
                if profile.constraints.budget_max:
                    profile.constraints.budget_max *= 0.9
            elif reason == "wrong_brand":
                brand = product.brand
                profile.brand_scores[brand] = profile.brand_scores.get(brand, 1.0) * 0.5
            elif reason == "insufficient_specs":
                weights["technical_match"] = min(weights.get("technical_match", 0.40) * 1.15, 0.6)
            elif reason == "poor_reviews":
                weights["sentiment"] = min(weights.get("sentiment", 0.30) * 1.2, 0.5)

        elif direction == "right":
            brand = product.brand
            profile.brand_scores[brand] = profile.brand_scores.get(brand, 1.0) * 1.3

        # Normalize weights to sum to 1
        total = sum(weights.values())
        if total > 0:
            profile.scoring_weights = {k: v / total for k, v in weights.items()}

        return profile

    async def rescore_products(
        self, products: list[ProductScore], profile: IntentProfile
    ) -> list[ProductScore]:
        """Re-score products after weight update (no LLM call — fast)."""
        for ps in products:
            weights = profile.scoring_weights
            ps.total_score = round(
                ps.technical_match * weights.get("technical_match", 0.40)
                + ps.sentiment_score * weights.get("sentiment", 0.30)
                + ps.value_for_money * weights.get("value_for_money", 0.20)
                + ps.availability_score * weights.get("availability", 0.10),
                1,
            )

            # Apply brand scoring
            brand = ps.product.brand
            if brand in profile.brand_scores:
                ps.total_score *= profile.brand_scores[brand]
                ps.total_score = min(ps.total_score, 100)

        products.sort(key=lambda s: s.total_score, reverse=True)
        return products
