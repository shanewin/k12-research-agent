from dataclasses import dataclass, field
from typing import List

@dataclass
class BuyingProfile:
    style: str                      # Innovator, Value Seeker, Incumbent Loyalist, Support Oriented, Unknown
    confidence: str                 # HIGH, MEDIUM, LOW
    justification: str              # Narrative explaining why this style was chosen
    procurement_velocity: str       # FAST, MODERATE, SLOW
    price_sensitivity_score: int    # 0-100 (100 is highly sensitive)
    vendor_loyalty_score: int       # 0-100 (100 is highly loyal)
    key_procurement_findings: List[str] = field(default_factory=list)
    recommended_sales_strategy: str = ""
