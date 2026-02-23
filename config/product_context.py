from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ProductContext:
    """
    Configure once per EdTech company or product line.
    This shapes every search, analysis, and score the agent produces.
    """
    # === PRODUCT IDENTITY ===
    company_name: str = ""
    product_name: str = ""
    product_category: str = ""  
    product_subcategories: List[str] = field(default_factory=list)
    one_liner: str = ""  # What the product does in one sentence

    # === SEARCH KEYWORDS ===
    primary_keywords: List[str] = field(default_factory=list)
    secondary_keywords: List[str] = field(default_factory=list)

    # === COMPETITORS ===
    direct_competitors: List[str] = field(default_factory=list)
    adjacent_competitors: List[str] = field(default_factory=list)

    # === DECISION MAKER PRIORITY ===
    primary_buyer_titles: List[str] = field(default_factory=list)
    secondary_buyer_titles: List[str] = field(default_factory=list)
    executive_sponsor_titles: List[str] = field(default_factory=list)

    # === BOARD MEETING TRIGGERS ===
    board_agenda_triggers: List[str] = field(default_factory=list)
    board_agenda_anti_triggers: List[str] = field(default_factory=list)

    # === RFP KEYWORDS ===
    rfp_keywords: List[str] = field(default_factory=list)

    # === FUNDING RELEVANCE ===
    relevant_funding_sources: List[str] = field(default_factory=list)

    # === ICP SCORING ADJUSTMENTS ===
    ideal_enrollment_min: int = 2000
    ideal_enrollment_max: int = 100000
    minimum_per_pupil_expenditure: Optional[float] = None
    title_i_preference: Optional[str] = "neutral" # "required", "preferred", "neutral"
    locale_preferences: List[str] = field(default_factory=list)

    # === INTEGRATION DEPENDENCIES ===
    required_integrations: List[str] = field(default_factory=list)
    incompatible_systems: List[str] = field(default_factory=list)

    # === SALES CYCLE CONTEXT ===
    typical_deal_size: str = "" # "under_10k", "10k_50k", "50k_200k", "200k_plus"
    typical_sales_cycle_months: int = 6
    implementation_requirements: List[str] = field(default_factory=list)

    # Weights for scoring (0-1.0)
    firmographic_weight: float = 0.3
    decision_maker_weight: float = 0.2
    signal_weight: float = 0.5
