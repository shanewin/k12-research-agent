from tavily import TavilyClient
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class K12TavilyClient:
    def __init__(self, api_key: str, budget: int = 500):
        self.client = TavilyClient(api_key=api_key)
        self.budget = budget
        self.credits_used = 0

    def search(self, query: str, **kwargs) -> Dict:
        """
        Execute a search if budget allows.
        """
        cost = 2 if kwargs.get("search_depth") == "advanced" else 1
        if self.credits_used + cost > self.budget:
            logger.warning(f"Tavily budget exhausted: {self.credits_used}/{self.budget}")
            return {"results": []}
        
        try:
            result = self.client.search(query, **kwargs)
            self.credits_used += cost
            return result
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return {"results": []}

    def extract(self, urls: List[str]) -> Dict:
        """
        Extract content from URLs.
        """
        cost = max(1, len(urls) // 5)
        if self.credits_used + cost > self.budget:
            logger.warning(f"Tavily budget exhausted (extract): {self.credits_used}/{self.budget}")
            return {"results": []}
        
        try:
            result = self.client.extract(urls=urls)
            self.credits_used += cost
            return result
        except Exception as e:
            logger.error(f"Tavily extract error: {e}")
            return {"results": []}

    def search_district(self, district_name: str, query_type: str) -> Optional[Dict]:
        """
        Pre-built K12-specific searches.
        """
        queries = {
            "board_meetings": f'"{district_name}" board meeting agenda 2025 2026',
            "rfps": f'"{district_name}" RFP "request for proposal" technology',
            "leadership": f'"{district_name}" superintendent appointed hired new 2024 2025',
            "funding": f'"{district_name}" ESSER "federal funding" grant technology',
            "tech_initiatives": f'"{district_name}" technology plan "digital learning" "1:1"',
            "job_postings": f'"{district_name}" hiring "instructional technology" "digital learning"',
            "sis": f'"{district_name}" "PowerSchool" OR "Infinite Campus" OR "Skyward"',
            "lms": f'"{district_name}" "Canvas" OR "Schoology" OR "Google Classroom"',
            "devices": f'"{district_name}" "Google Workspace" OR Chromebook OR "Microsoft 365" OR iPad',
        }
        
        if query_type not in queries:
            logger.error(f"Unknown query type: {query_type}")
            return None
            
        return self.search(queries[query_type], search_depth="advanced", max_results=5)
