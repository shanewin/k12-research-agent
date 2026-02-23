from dataclasses import dataclass, field
from typing import List, Optional, Dict
from .contact import Contact
from .signal import Signal
from .board_meeting import BoardMeetingReport
from .news import NewsReport
from .erate import ErateReport
from .buying_profile import BuyingProfile

@dataclass
class DistrictProfile:
    # A: District Firmographics (NCES API)
    district_name: str
    state: str
    nces_id: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    total_enrollment: Optional[int] = None
    number_of_schools: Optional[int] = None
    grade_span: Optional[str] = None
    locale_type: Optional[str] = None
    title_i_eligible: Optional[bool] = None
    free_reduced_lunch_pct: Optional[float] = None
    
    # Financials
    total_revenue: Optional[float] = None
    total_expenditures: Optional[float] = None
    per_pupil_expenditure: Optional[float] = None
    rev_fed_total: Optional[float] = None
    rev_state_total: Optional[float] = None
    rev_local_total: Optional[float] = None
    
    # Demographics
    enrollment_white_pct: Optional[float] = None
    enrollment_black_pct: Optional[float] = None
    enrollment_hispanic_pct: Optional[float] = None
    enrollment_asian_pct: Optional[float] = None
    ell_pct: Optional[float] = None
    sped_pct: Optional[float] = None

    # B: Decision Makers (Apollo + Tavily)
    contacts: List[Contact] = field(default_factory=list)
    
    # C: Technology Profile (Tavily)
    website_url: Optional[str] = None
    ecosystem: str = "Unknown" # Google vs Microsoft
    one_to_one_program: bool = False
    sis: str = "Unknown"
    lms: str = "Unknown"
    tech_plan_url: Optional[str] = None
    e_rate_participation: bool = False
    current_vendors: List[str] = field(default_factory=list)
    
    # D: Buying Signals (Agentic Loop)
    signals: List[Signal] = field(default_factory=list)
    
    # E: Financial / Funding Signals
    esser_allocation_total: Optional[float] = None
    esser_remaining: Optional[float] = None
    esser_deadline_status: str = "Unknown"
    bond_measures: List[str] = field(default_factory=list)
    
    # F: CRM Data (Optional)
    crm_data: Dict = field(default_factory=dict)
    
    # Intelligence Output
    board_meeting_report: Optional[BoardMeetingReport] = None
    news_report: Optional[NewsReport] = None
    erate_report: Optional[ErateReport] = None
    buying_profile: Optional[BuyingProfile] = None
    intelligence_brief: Optional[str] = None
    
    # Scoring & Status
    icp_score: int = 0
    signal_strength: str = "LOW" # LOW, MEDIUM, HIGH
    recommended_action: str = "MONITOR"
    tavily_credits_used: int = 0
    metadata: Dict = field(default_factory=dict)
    corpus: str = ""
