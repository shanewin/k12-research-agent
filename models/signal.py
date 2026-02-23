from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Signal:
    signal_type: str        # board_agenda_tech, news_problem, leadership, rfp, etc.
    strength: str           # HIGH, MEDIUM, LOW
    title: str
    detail: str
    source_url: Optional[str] = None
    date_detected: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    relevance_note: Optional[str] = None
