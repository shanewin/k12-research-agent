import logging
import json
from abc import ABC, abstractmethod
from typing import List, Dict
from anthropic import Anthropic
from .tavily_client import K12TavilyClient

logger = logging.getLogger(__name__)

class PortalHandler(ABC):
    def __init__(self, tavily: K12TavilyClient, anthropic: Anthropic):
        self.tavily = tavily
        self.anthropic = anthropic

    @abstractmethod
    def harvest_agendas(self, url: str, district_name: str, months_back: int = 24) -> List[Dict]:
        """Retrieve agenda links for the specified time period."""
        pass

def _lookback_years(months_back: int) -> List[int]:
    """Calendar years covered by the lookback window, most recent first."""
    from datetime import date
    today = date.today()
    start_year = (today.year * 12 + today.month - 1 - months_back) // 12
    return list(range(today.year, start_year - 1, -1))


class BoardDocsHandler(PortalHandler):
    def harvest_agendas(self, url: str, district_name: str, months_back: int = 24) -> List[Dict]:
        logger.info(f"Hoovering BoardDocs for {district_name} (Lookback: {months_back} months)")
        # BoardDocs often needs targeted search to find "old" meetings because JS navigation is hard to automate
        # We search year by year to be thorough
        all_agendas = []
        years = _lookback_years(months_back)
        
        for year in years:
            # Search for BOTH agendas and minutes (minutes have the qualitative notes)
            query = f'site:boarddocs.com "{district_name}" (agenda OR minutes) {year}'
            search = self.tavily.search(query, search_depth="advanced", max_results=20)
            if search and search.get("results"):
                for res in search["results"]:
                    if "nsf" in res["url"].lower():
                        all_agendas.append({
                            "date": f"{year}-??-??",
                            "title": res.get("title", "Meeting"),
                            "url": res["url"]
                        })
        
        # Deduplicate by URL
        unique_agendas = {a["url"]: a for a in all_agendas}.values()
        return list(unique_agendas)

class CustomHandler(PortalHandler):
    def harvest_agendas(self, url: str, district_name: str, months_back: int = 24) -> List[Dict]:
        logger.info(f"Custom/Generic harvesting for {url}")
        # Use Tavily extract to find links, then Claude to filter by date
        extraction = self.tavily.client.extract(urls=[url])
        raw_content = extraction.get("results", [{}])[0].get("raw_content", "")
        
        if not raw_content: return []

        prompt = f"""From the following content of a school board meeting page, 
        extract ALL agenda links from the last {months_back} months.
        
        CONTENT:
        {raw_content[:15000]}
        
        Return ONLY valid JSON:
        [{{"date": "YYYY-MM-DD", "title": "...", "url": "..."}}]"""
        
        response = self.anthropic.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        try:
            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception:
            return []

class SimbliHandler(CustomHandler):
    def harvest_agendas(self, url: str, district_name: str, months_back: int = 24) -> List[Dict]:
        logger.info(f"Simbli scanning for {district_name}")
        # The meetings-listing page is server-rendered — extract it directly first
        agendas = super().harvest_agendas(url, district_name, months_back)
        if agendas:
            return agendas
        # Fallback: search the Simbli domain across the lookback window
        results = []
        for year in _lookback_years(months_back)[:2]:
            query = f'site:eboardsolutions.com "{district_name}" (agenda OR minutes) {year}'
            search = self.tavily.search(query, search_depth="advanced", max_results=10)
            for r in (search or {}).get("results", []):
                if "meeting" in r["url"].lower() or "agenda" in r["url"].lower():
                    results.append({"url": r["url"], "title": r.get("title", "Meeting")})
        return list({a["url"]: a for a in results}.values())


class PortalRegistry:
    def __init__(self, tavily: K12TavilyClient, anthropic: Anthropic):
        self.tavily = tavily
        self.anthropic = anthropic
        self.handlers = {
            "boarddocs.com": BoardDocsHandler,
            "eboardsolutions.com": SimbliHandler,
            "simbli.com": SimbliHandler,
        }

    def get_handler(self, url: str) -> PortalHandler:
        url_lower = url.lower()
        for domain, handler_class in self.handlers.items():
            if domain in url_lower:
                return handler_class(self.tavily, self.anthropic)
        return CustomHandler(self.tavily, self.anthropic)
