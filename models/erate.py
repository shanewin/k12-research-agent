from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ErateFundingRequest:
    funding_year: int
    application_number: str
    frn: str                        # Funding Request Number
    ben: str                        # Billed Entity Number
    organization_name: str
    service_type: str               # Category 1 or Category 2
    product_service_description: str
    vendor_name: str
    total_cost: float
    funding_commitment_request: float
    status: str                     # e.g., Funded, Pending, Denied
    form_type: str                  # Form 470 or Form 471

@dataclass
class ErateReport:
    status: str = ""                # complete, not_found, failed
    ben: Optional[str] = None
    total_funding_recent: float = 0.0
    active_rfps_count: int = 0      # Derived from Form 470s
    pending_requests_count: int = 0
    funding_history: List[ErateFundingRequest] = field(default_factory=list)
    key_vendors: List[str] = field(default_factory=list)
    summary: str = ""
