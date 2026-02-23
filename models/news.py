from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class NewsProblem:
    problem: str
    source: str
    source_url: str
    severity: str               # HIGH, MEDIUM, LOW
    product_relevance: str      # DIRECT, INDIRECT, NONE
    opportunity: str
    recommended_talking_point: str

@dataclass
class LeadershipEvent:
    event: str
    date: str
    source_url: str
    implication: str
    sales_impact: str           # POSITIVE, NEGATIVE, NEUTRAL

@dataclass
class CompetitorMention:
    competitor: str
    context: str
    sentiment: str              # POSITIVE, NEGATIVE, NEUTRAL
    source_url: str
    opportunity: str

@dataclass
class BudgetIndicator:
    indicator: str
    source_url: str
    amount: Optional[float] = None
    implication: str = ""
    timeline: str = ""

@dataclass
class CommunitySentiment:
    technology_attitude: str = "UNKNOWN"    # POSITIVE, MIXED, NEGATIVE, UNKNOWN
    key_concerns: List[str] = field(default_factory=list)
    parent_advocacy: str = ""
    teacher_sentiment: str = ""

@dataclass
class NewsReport:
    status: str = ""
    articles_found: int = 0
    articles_analyzed: int = 0
    district_narrative: str = ""
    problems: List[NewsProblem] = field(default_factory=list)
    leadership_dynamics: List[LeadershipEvent] = field(default_factory=list)
    competitor_mentions: List[CompetitorMention] = field(default_factory=list)
    budget_indicators: List[BudgetIndicator] = field(default_factory=list)
    community_sentiment: CommunitySentiment = field(default_factory=CommunitySentiment)
    overall_signal: str = ""
    key_takeaway: str = ""
    source_urls: List[str] = field(default_factory=list)
    tavily_credits_used: int = 0
