from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class BoardMeetingItem:
    meeting_date: str
    agenda_item: str
    category: str           # platform_evaluation, hardware_refresh, budget, policy, etc.
    signal_strength: str    # HIGH, MEDIUM, LOW
    stage: str              # info, committee, evaluation, action, approved
    estimated_purchase_timeline: str
    detail: str
    relevance_to_product: str
    recommended_action: str

@dataclass
class VendorMention:
    meeting_date: str
    vendor_name: str
    context: str
    implication: str         # "active competitor", "incumbent", "being replaced"

@dataclass
class BudgetItem:
    meeting_date: str
    description: str
    amount: Optional[float] = None
    fiscal_year: str = ""

@dataclass
class BoardMeetingReport:
    status: str = ""                        # complete, not_found, no_agendas, failed
    board_page_url: str = ""
    platform: str = ""                      # boarddocs, custom, simbli, unknown
    meetings_analyzed: int = 0
    technology_items: List[BoardMeetingItem] = field(default_factory=list)
    budget_items: List[BudgetItem] = field(default_factory=list)
    vendor_mentions: List[VendorMention] = field(default_factory=list)
    leadership_signals: List[dict] = field(default_factory=list)
    timeline_summary: str = ""
    overall_signal_strength: str = ""
    tavily_credits_used: int = 0
