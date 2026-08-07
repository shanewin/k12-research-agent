from models.district import DistrictProfile
from config.product_context import ProductContext
import logging

logger = logging.getLogger(__name__)

class ScoringEngine:
    def calculate_score(self, profile: DistrictProfile, ctx: ProductContext) -> int:
        score = 0
        
        # 1. Firmographic Fit (0-30 points)
        enrollment = profile.total_enrollment or 0
        if ctx.ideal_enrollment_min <= enrollment <= ctx.ideal_enrollment_max:
            score += 20
        elif enrollment > 0:
            score += 5
            
        if profile.per_pupil_expenditure and ctx.minimum_per_pupil_expenditure:
            if profile.per_pupil_expenditure < ctx.minimum_per_pupil_expenditure:
                score -= 10
            else:
                score += 10
        
        # 2. Decision Maker & Turnover Logic (0-25 points)
        leadership_boost = 0
        for c in profile.contacts:
            # Title match boost
            if any(title.lower() in c.title.lower() for title in ctx.primary_buyer_titles):
                leadership_boost = max(leadership_boost, 10)
                
            # Turnover/Job Change Boost (24-month window)
            if c.is_new:
                if "superintendent" in c.title.lower():
                    leadership_boost = max(leadership_boost, 20) # High-value transition
                else:
                    leadership_boost = max(leadership_boost, 15) # Cabinet transition
                    
        score += leadership_boost

        # 3. News-based boosts (Blueprint Phase 7 scoring logic)
        if profile.news_report and profile.news_report.status == "complete":
            # Direct product-relevant problems
            direct_problems = [p for p in profile.news_report.problems if p.product_relevance == "DIRECT"]
            score += min(15, len(direct_problems) * 8)
            
            # Negative competitor sentiment
            negative_comp = [m for m in profile.news_report.competitor_mentions if m.sentiment == "NEGATIVE"]
            score += min(10, len(negative_comp) * 5)
            
            # Big budget indicators
            big_budget = [b for b in profile.news_report.budget_indicators if b.amount and b.amount > 1000000]
            score += min(10, len(big_budget) * 5)

        # 4. Board Meeting signals
        if profile.board_meeting_report and profile.board_meeting_report.status == "complete":
            high_signals = [item for item in profile.board_meeting_report.technology_items if item.signal_strength == "HIGH"]
            score += min(15, len(high_signals) * 10)

        # 5. Integration compatibility
        if ctx.required_integrations:
            if any(req.lower() in (profile.ecosystem + profile.lms + profile.sis).lower() for req in ctx.required_integrations):
                score += 10
            else:
                score -= 10

        # 6. Funding fit (0-30 points) — from the local funding dataset's
        # target-profile engine. A district matching multiple ICP profiles has
        # both the need and the money, regardless of what live scraping found.
        score += self.funding_fit_points(
            (profile.metadata or {}).get("funding_profile"),
            profile.title_i_eligible,
            ctx.title_i_preference,
        )

        return min(100, max(0, score))

    @staticmethod
    def funding_fit_points(funding_profile: dict, title_i_eligible, title_i_preference) -> int:
        """Score the funding/ICP fit. Shared with the post-hoc rescore script."""
        points = 0
        fp = funding_profile or {}
        try:
            profile_count = int(fp.get("profile_count") or 0)
        except (TypeError, ValueError):
            profile_count = 0
        points += min(25, profile_count * 5)  # 5+ ICP profiles -> full 25
        if title_i_eligible and title_i_preference in ("preferred", "required"):
            points += 5
        return points

    def get_signal_strength(self, score: int) -> str:
        if score >= 75: return "HIGH"
        if score >= 40: return "MEDIUM"
        return "LOW"
        
    def get_recommended_action(self, score: int) -> str:
        if score >= 85: return "PURSUE AGGRESSIVELY"
        if score >= 60: return "PURSUE"
        if score >= 30: return "NURTURE"
        return "MONITOR"
