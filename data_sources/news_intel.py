import json
import logging
from typing import List, Dict
from anthropic import Anthropic
from .tavily_client import K12TavilyClient
from models.news import NewsReport, CommunitySentiment
from config.product_context import ProductContext

logger = logging.getLogger(__name__)

class NewsIntelligence:
    def __init__(self, tavily_client: K12TavilyClient, anthropic_client: Anthropic):
        self.tavily = tavily_client
        self.anthropic = anthropic_client

    def full_scan(self, district_name: str, state: str, product_context: ProductContext) -> NewsReport:
        """
        Complete news intelligence pipeline (18 months).
        """
        # Step 1: Run targeted news searches (9 distinct queries as per blueprint)
        search_results = self.search_district_news(district_name, state, product_context)
        if not search_results:
            return NewsReport(status="no_news_found")
            
        # Step 2: Fetch key articles
        full_articles = self.fetch_key_articles(search_results, max_fetches=5)
        
        # Step 3: Analyze
        analysis = self.analyze_news(full_articles, product_context)
        
        return NewsReport(
            status="complete",
            articles_found=len(search_results),
            articles_analyzed=len(full_articles),
            district_narrative=analysis.get("district_narrative", ""),
            problems=analysis.get("problems_identified", []),
            leadership_dynamics=analysis.get("leadership_dynamics", []),
            competitor_mentions=analysis.get("competitor_mentions", []),
            budget_indicators=analysis.get("budget_indicators", []),
            community_sentiment=CommunitySentiment(**analysis.get("community_sentiment", {})),
            overall_signal=analysis.get("overall_news_signal", "LOW"),
            key_takeaway=analysis.get("key_takeaway", ""),
            source_urls=[r["url"] for r in search_results]
        )

    def search_district_news(self, district_name: str, state: str, product_context: ProductContext) -> List[Dict]:
        queries = [
            f'"{district_name}" {state} news',
            f'"{district_name}" technology OR "digital learning"',
            f'"{district_name}" budget OR funding OR ESSER',
            f'"{district_name}" superintendent OR "school board" hired resigned',
            f'"{district_name}" {" OR ".join(product_context.primary_keywords[:3])}'
        ]
        
        all_results = []
        seen_urls = set()
        for query in queries:
            results = self.tavily.search(query, topic="news", search_depth="basic", max_results=5)
            for r in results.get("results", []):
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)
        return all_results

    def fetch_key_articles(self, search_results: List[Dict], max_fetches: int = 5) -> List[Dict]:
        urls = [r["url"] for r in search_results[:max_fetches]]
        if not urls: return []
        extraction = self.tavily.client.extract(urls=urls)
        return extraction.get("results", [])

    def analyze_news(self, articles: List[Dict], context: ProductContext) -> Dict:
        """
        Claude analyzes news for product-relevant problems and opportunities.
        """
        system_prompt = """You are a K12 EdTech sales intelligence analyst reading local news 
coverage about a school district. Your job is to identify problems, events, and dynamics that 
create opportunities to sell technology solutions."""

        user_prompt = f"""Analyze this news coverage about a school district 
for sales intelligence relevant to {context.product_name}.

ARTICLES:
{json.dumps(articles, indent=2)}

Return ONLY valid JSON as specified in the blueprint schema."""

        try:
            response = self.anthropic.messages.create(
                model="claude-haiku-4-5",
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return json.loads(response.content[0].text)
        except Exception as e:
            logger.error(f"News analysis failed: {e}")
            return {}
