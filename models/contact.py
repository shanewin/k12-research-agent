from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Contact:
    name: str
    title: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    tenure_months: Optional[int] = None
    started_at: Optional[str] = None
    is_new: bool = False  # < 18 months
    previous_org: Optional[str] = None
    previous_org_tech_initiatives: List[str] = field(default_factory=list)
    source: str = "apollo"  # "apollo" or "tavily"
