import json
import logging
from typing import List, Dict
from anthropic import Anthropic
from dataclasses import asdict
from data_sources.tavily_client import K12TavilyClient
from models.signal import Signal
from config.product_context import ProductContext

logger = logging.getLogger(__name__)

# Use a stable model name
CLAUDE_MODEL = "claude-haiku-4-5"

class SignalDetector:
    def __init__(self, tavily_client: K12TavilyClient, anthropic_client: Anthropic):
        self.tavily = tavily_client
        self.claude = anthropic_client

    def detect_signals(self, district_name: str, state: str, context: ProductContext, initial_data: Dict) -> List[Signal]:
        """
        High-fidelity agentic loop:
        1. Claude analyzes initial data (NCES, Apollo, Tech Profile).
        2. Claude decides on 2-3 deep-dive follow-up searches.
        3. Run follow-ups.
        4. Synthesize final signals.
        """
        # Step 1: Claude analyzes and decides follow-ups
        # Strip massive text corpus from initial data to save tokens
        clean_initial_data = dict(initial_data)
        if "corpus" in clean_initial_data:
            clean_initial_data["corpus"] = "[REDACTED TO SAVE TOKENS]"
        prompt = f"""You are researching {district_name}, {state} for an EdTech company that sells:
PRODUCT: {context.product_name}
CATEGORY: {context.product_category}
WHAT IT DOES: {context.one_liner}
KEY COMPETITORS: {context.direct_competitors}

INITIAL DATA:
{json.dumps(clean_initial_data, indent=2)}

Decide on 3 follow-up search queries that would reveal whether this district is a high-quality lead.
Prioritize:
- Who currently provides their {context.product_category} (The Incumbent)?
- RFP searches for {context.product_category}
- Leadership background (tenure/lineage of key buyers)
- Specific budget allocations

Return ONLY valid JSON array of strings: ["query1", "query2", "query3"]"""

        response = self.claude.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            follow_up_queries = json.loads(response.content[0].text)
        except:
            follow_up_queries = [f'"{district_name}" {context.product_category} RFP']

        # Step 2: Run follow-ups
        follow_up_results = []
        for query in follow_up_queries:
            results = self.tavily.search(query, search_depth="advanced")
            follow_up_results.append({"query": query, "results": results})

        # Step 3: Final Synthesis of signals
        synthesis_prompt = f"""Based on the following search results, identify the top 5 buying signals for {context.product_name} 
        in {district_name}.
        
        RESULTS:
        {json.dumps(follow_up_results, indent=2)}
        
        Return ONLY valid JSON:
        [
          {{
            "signal_type": "...",
            "strength": "HIGH/MEDIUM/LOW",
            "title": "...",
            "detail": "...",
            "source_url": "...",
            "relevance_note": "..."
          }}
        ]"""

        final_response = self.claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": synthesis_prompt}]
        )
        
        try:
            content = final_response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            signal_data = json.loads(content)
            return [Signal(**s) for s in signal_data]
        except Exception as e:
            logger.error(f"Signal synthesis failed: {e}")
            return []
