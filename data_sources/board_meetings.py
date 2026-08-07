import json
import logging
from typing import List, Optional, Dict
from anthropic import Anthropic
from .tavily_client import K12TavilyClient
from models.board_meeting import BoardMeetingReport, BoardMeetingItem, VendorMention, BudgetItem
from config.product_context import ProductContext
from .board_portal_handlers import PortalRegistry
from analysis.local_rag import LocalRAG

logger = logging.getLogger(__name__)

class BoardMeetingIntelligence:
    def __init__(self, tavily_client: K12TavilyClient, anthropic_client: Anthropic):
        self.tavily = tavily_client
        self.anthropic = anthropic_client
        self.registry = PortalRegistry(tavily_client, anthropic_client)

    def full_scan(self, district_name: str, state: str, product_context: ProductContext) -> BoardMeetingReport:
        """
        Run the complete board meeting intelligence pipeline.
        Upgraded to "Hoover" Mode (Multi-year, Portal-aware, RAG-lite).
        """
        # Step 1: Find the board page
        board_page_url = self.discover_board_page(district_name, state)
        if not board_page_url:
            return BoardMeetingReport(status="board_page_not_found")
            
        logger.info(f"Hoover Mode: Board portal identified: {board_page_url}")
        
        # Step 2: Use Portal Registry to get the right harvester
        handler = self.registry.get_handler(board_page_url)
        agendas = handler.harvest_agendas(board_page_url, district_name, months_back=24)
        
        if not agendas:
            # Fallback: Try a very specific search if the portal extraction failed
            agendas = self._fallback_agenda_search(district_name, state)
            
        if not agendas:
            return BoardMeetingReport(status="no_agendas_found", board_page_url=board_page_url)
            
        logger.info(f"Harvested {len(agendas)} meetings. Starting extraction...")

        # Step 3: Deep Extraction
        agenda_urls = [a.get("url") for a in agendas if a.get("url")]
        # Extract up to 20 for thoroughness in multi-year mode
        contents = self.extract_agenda_content(agenda_urls[:20])
        
        # Step 4: Local RAG Filtering & Claude analysis
        analysis = self.analyze_agendas(contents, product_context)
        
        # Package report
        report = BoardMeetingReport(
            status="complete",
            board_page_url=board_page_url,
            platform=handler.__class__.__name__.replace("Handler", "").lower(),
            meetings_analyzed=len(contents),
            technology_items=analysis.get("technology_items", []),
            budget_items=analysis.get("budget_items", []),
            vendor_mentions=analysis.get("vendor_mentions", []),
            leadership_signals=analysis.get("leadership_signals", []),
            timeline_summary=analysis.get("timeline_summary", ""),
            overall_signal_strength=analysis.get("overall_signal_strength", "UNKNOWN")
        )
        return report

    # Pre-computed CA board-platform map (ported from an earlier client engagement):
    # 904 districts -> platform + direct portal URL. Skips discovery searches.
    _platform_map = None

    @classmethod
    def _load_platform_map(cls) -> Dict:
        if cls._platform_map is None:
            import os
            path = os.path.join(os.path.dirname(__file__), "..", "data", "board_platform_map.json")
            try:
                with open(path) as f:
                    cls._platform_map = json.load(f)
                logger.info(f"Loaded board platform map ({len(cls._platform_map)} districts)")
            except Exception as e:
                logger.warning(f"Board platform map unavailable: {e}")
                cls._platform_map = {}
        return cls._platform_map

    def _lookup_platform_map(self, district_name: str, state: str) -> Optional[str]:
        """Return a direct board-portal URL from the pre-computed CA map, if known."""
        if state.upper() != "CA":
            return None
        from data_sources.local_funding import LocalFundingData
        row = LocalFundingData.lookup(district_name=district_name, state=state)
        if not row:
            return None
        entry = self._load_platform_map().get((row.get("ncesid") or "").strip())
        if not entry:
            return None
        platform = entry.get("platform")
        url = None
        if platform == "boarddocs":
            url = entry.get("boarddocs_url")
        elif platform == "simbli":
            url = self._normalize_simbli_url(entry.get("simbli_url"))
        elif platform == "self_hosted":
            pages = entry.get("board_pages") or []
            url = pages[0] if pages else None
        if url:
            url = url.strip().rstrip("\\")
            if not url.startswith("http"):
                url = f"https://{url}"
        if url:
            logger.info(f"Board platform map hit: {district_name} -> {platform} ({url})")
        return url

    @staticmethod
    def _normalize_simbli_url(url: Optional[str]) -> Optional[str]:
        """Map entries often point at Simbli's policy pages; rewrite to the
        meetings listing, which is what the harvester actually needs."""
        if not url:
            return None
        import re
        m = re.search(r"[?&]s=(\d+)", url, re.IGNORECASE)
        if m:
            return f"https://simbli.eboardsolutions.com/SB_Meetings/SB_MeetingListing.aspx?S={m.group(1)}"
        return url

    def discover_board_page(self, district_name: str, state: str) -> Optional[str]:
        """
        Powerful discovery using multi-step search and site mapping.
        Checks the pre-computed CA platform map first (no API calls).
        """
        mapped = self._lookup_platform_map(district_name, state)
        if mapped:
            return mapped

        # Strategy A: Targeted Search
        query = f'"{district_name}" {state} board meeting agenda minutes site:.org OR site:.us OR site:.gov OR site:.edu'
        results = self.tavily.search(query, search_depth="advanced", max_results=15)
        
        board_urls = []
        if results and results.get("results"):
            for res in results["results"]:
                url = res.get("url", "").lower()
                # Skip known "spam" or unofficial domains if possible
                if any(x in url for x in ["sleepinfairfax", "wordpress", "blogspot"]):
                    continue
                    
                # Prioritize high-confidence portals
                if any(x in url for x in ["boarddocs.com", "eboardsolutions.com", "simbli"]):
                    return res.get("url")
                if any(x in url for x in ["board", "agenda", "meeting", "minutes"]):
                    board_urls.append(res.get("url"))
        
        if board_urls:
            return board_urls[0]

        # Strategy B: Site Mapping (The "Power Tool")
        # Find the main domain first
        domain_query = f'"{district_name}" {state} official school district website'
        domain_results = self.tavily.search(domain_query, max_results=3)
        if domain_results and domain_results.get("results"):
            domain = domain_results["results"][0].get("url")
            # Ensure it's not a news site
            if ".edu" in domain or ".org" in domain or ".us" in domain:
                logger.info(f"Mapping district domain for board links: {domain}")
                try:
                    map_results = self.tavily.client.map(url=domain)
                    for url in map_results.get("results", []):
                        if "board" in url.lower() and ("meeting" in url.lower() or "agenda" in url.lower()):
                            return url
                except Exception as e:
                    logger.error(f"Tavily map failed: {e}")
                    
        return None

    def get_recent_agendas(self, board_page_url: str, district_name: str) -> List[Dict]:
        """
        Enhanced extraction using Claude to find links within dynamic content.
        """
        # Special handling for BoardDocs
        if "boarddocs.com" in board_page_url.lower():
            return self._handle_boarddocs(board_page_url, district_name)

        extraction = self.tavily.client.extract(urls=[board_page_url])
        results = extraction.get("results", [])
        if not results: return []
        
        raw_content = results[0].get("raw_content", "")
        if not raw_content: return []

        prompt = f"""From the following content of a school board meeting page, 
        extract a list of the 5 most recent board meeting dates and their direct links 
        to agendas or minutes.
        
        CONTENT:
        {raw_content[:8000]}
        
        Return ONLY valid JSON:
        [{{"date": "YYYY-MM-DD", "title": "...", "url": "..."}}]"""
        
        response = self.anthropic.messages.create(
            model="claude-haiku-4-5",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        try:
            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception:
            return []

    def _handle_boarddocs(self, url: str, district_name: str) -> List[Dict]:
        """
        BoardDocs specific logic. Since it's JS-heavy, we often need to 
        guess the direct URL or use a targeted search for the meeting list.
        """
        logger.info(f"Specialized handling for BoardDocs: {url}")
        # BoardDocs often fails simple extraction. We run a very targeted search for the links.
        query = f'site:boarddocs.com "{district_name}" meeting agenda 2024 2025'
        search = self.tavily.search(query, search_depth="advanced", max_results=10)
        
        agendas = []
        if search and search.get("results"):
            for res in search["results"]:
                # BoardDocs agenda URLs look like: .../Board.nsf/goto?open&id=...
                if "nsf" in res["url"].lower():
                    agendas.append({
                        "date": "Detected via search",
                        "title": res.get("title", "Meeting"),
                        "url": res["url"]
                    })
        return agendas[:5]

    def _fallback_agenda_search(self, district_name: str, state: str) -> List[Dict]:
        """
        The "Hail Mary" search if portal discovery fails.
        """
        logger.info("Running fallback agenda search...")
        query = f'filetype:pdf "{district_name}" {state} "board meeting" agenda 2025'
        results = self.tavily.search(query, search_depth="basic", max_results=5)
        
        agendas = []
        if results and results.get("results"):
            for res in results["results"]:
                agendas.append({
                    "date": "2025 (approx)",
                    "title": res.get("title", "PDF Agenda"),
                    "url": res["url"]
                })
        return agendas

    def extract_agenda_content(self, agenda_urls: List[str]) -> List[Dict]:
        if not agenda_urls: return []
        extraction_results = self.tavily.client.extract(urls=agenda_urls[:10])
        extracted = []
        for res in extraction_results.get("results", []):
            extracted.append({
                "url": res["url"],
                "content": res.get("raw_content", "")
            })
        return extracted

    def analyze_agendas(self, contents: List[Dict], context: ProductContext) -> Dict:
        """
        Deep analysis using Claude with domain expertise.
        Optimized with LocalRAG for multi-year document sets.
        """
        if not contents:
            return {"technology_items": [], "overall_signal_strength": "LOW"}

        # Initialize LocalRAG with product specific keywords
        keywords = context.primary_keywords + context.secondary_keywords + context.rfp_keywords + [context.product_category]
        rag = LocalRAG(keywords=keywords)
        
        # Get highly relevant context segments (RAG Filter)
        rag_context = rag.get_context_for_claude(
            documents=contents,
            product_category=context.product_category,
            max_tokens_approx=15000 # Stay within Haiku/Sonnet limits
        )

        system_prompt = """You are a K12 EdTech sales intelligence analyst 
who specializes in reading school board minutes and agendas to identify qualitative leadership intent.

You understand that while RFPs are transactional, the MINUTES of a meeting are the true gold mine of intent.
You are looking for the 'Why' and 'When' before the 'What'.

PRIORITIZE THESE QUALITATIVE SIGNALS:
1. LEADERSHIP SENTIMENT: How does the Superintendent or Board President feel about current technology? Look for words like 'disappointed', 'inefficient', 'excited', 'transformative'.
2. PAIN POINTS: What challenges is the district facing? (e.g., 'chronic absenteeism', 'math proficiency decline', 'teacher burnout'). These are the root causes of future purchases.
3. PILOT INTEREST: Discussions about testing new solutions or 'seeing what else is out there'.
4. STRATEGIC SHIFTS: Are they moving away from a specific philosophy or incumbent vendor?
5. UNMET NEEDS: Direct mentions of things the district 'wishes' they had.

TIMING CLUES (Look for these in minutes):
- 'Superintendent recommends evaluation' = 6-9 months from purchase.
- 'Board consensus to move forward with pilot' = 3-6 months from purchase.
- 'Committee report on platform refresh' = 2-4 months from purchase.
"""

        user_prompt = f"""Analyze these school board meeting segments (extracted via RAG) 
for qualitative insights and technology intent relevant to {context.product_category}.

RELEVANT SEGMENTS:
{rag_context}

For each insight, classify it as a 'Signal' (Discussion/Intent) or a 'Transaction' (RFP/Contract).
Provide the source URL for every insight.

Return ONLY valid JSON:
{{
  "technology_items": [
    {{
      "meeting_date": "YYYY-MM-DD",
      "agenda_item": "...",
      "category": "SIGNAL/TRANSACTION", 
      "signal_strength": "HIGH/MEDIUM/LOW",
      "stage": "discussion/evaluation/action",
      "estimated_purchase_timeline": "...",
      "detail": "Include a quote or specific mention of sentiment/pain point...",
      "relevance_to_product": "...",
      "recommended_action": "..."
    }}
  ],
  "budget_items": [],
  "vendor_mentions": [],
  "leadership_signals": [
    {{
       "leader_name": "...",
       "sentiment": "positive/negative/neutral",
       "topic": "...",
       "detail": "..."
    }}
  ],
  "timeline_summary": "...",
  "overall_signal_strength": "HIGH/MEDIUM/LOW"
}}"""

        try:
            response = self.anthropic.messages.create(
                model="claude-haiku-4-5",
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            
            # Robust Defensive Casting
            def safe_cast(cls, items):
                if not items: return []
                fields = cls.__dataclass_fields__
                casted = []
                for item in items:
                    try:
                        valid_item = {}
                        for f_name, f_type in fields.items():
                            # If key exists, take it. Otherwise, look for defaults or use None.
                            if f_name in item:
                                valid_item[f_name] = item[f_name]
                            else:
                                if f_type.default is not f_type.default_factory: # Has default
                                    valid_item[f_name] = f_type.default
                                else:
                                    valid_item[f_name] = None if "Optional" in str(f_type) else ""
                        casted.append(cls(**valid_item))
                    except Exception as e:
                        logger.warning(f"Failed to cast {cls.__name__}: {e}")
                return casted

            return {
                "technology_items": safe_cast(BoardMeetingItem, data.get("technology_items", [])),
                "budget_items": safe_cast(BudgetItem, data.get("budget_items", [])),
                "vendor_mentions": safe_cast(VendorMention, data.get("vendor_mentions", [])),
                "leadership_signals": data.get("leadership_signals", []),
                "timeline_summary": data.get("timeline_summary", ""),
                "overall_signal_strength": data.get("overall_signal_strength", "UNKNOWN")
            }
        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"technology_items": [], "overall_signal_strength": "UNKNOWN"}
