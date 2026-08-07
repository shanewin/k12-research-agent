import logging
import datetime
import os
from typing import List
from config.product_context import ProductContext
from data_sources.tavily_client import K12TavilyClient
from urllib.parse import urlparse
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class SiteDiscoveryAgent:
    def __init__(self, tavily_client: K12TavilyClient):
        self.tavily = tavily_client
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
    def generate_target_urls(self, domain: str, context: ProductContext) -> List[str]:
        logger.info(f"Executing Agentic Site Discovery for {domain}...")
        
        current_year = datetime.datetime.now().year
        
        requirements = [
            f"Board Meeting Minutes or Agendas ({current_year-2} to {current_year})",
            f"District Strategic Plan",
            f"Annual Approved Budget ({current_year-2} to {current_year})",
            f"Active RFPs, Open Bids, or Vendor Solicitations",
            f"District Administration Directory / Staff Directory",
            f"News or Superintendent Announcements ({current_year-2} to {current_year})"
        ]
        
        if context.primary_buyer_titles:
            requirements.append(f"Pages related to these roles: {', '.join([t for t in context.primary_buyer_titles if t.strip()])}")
        if context.rfp_keywords:
            requirements.append(f"Pages related to these topics: {', '.join([t for t in context.rfp_keywords if t.strip()])}")
        if context.direct_competitors:
            requirements.append(f"Pages mentioning these competitors: {', '.join([c for c in context.direct_competitors if c.strip()])}")
        
        requirements.append(f"Evidence indicating who currently provides their {context.product_category} (The Incumbent Vendor)")

        req_str = "\n- ".join(requirements)
        
        lens_desc = context.product_name or "Educational Technology"
        system_prompt = f"""You are an expert intelligence analyst mapping out a school district website ({domain}). 
Your overarching mission is to conduct a signal intelligence search through the specific research lens of: {lens_desc}.
 
CRITICAL TIME CONSTRAINT: You are ONLY looking for information within a strict 2-year window from today ({current_year-2} to {current_year}). Disregard any documents older than {current_year-2}.

Your goal is to find the exact, highly-relevant URLs for the following required documents/pages:

- {req_str}

You MUST use the `search_site` tool to run highly-targeted queries against the domain. 
Remember to use `site:{domain}` in every query snippet. Use `filetype:pdf` when searching for budgets or plans if helpful.

***CRITICAL QUERY RULE***: DO NOT append specific years (e.g. '2024') to your search queries. Searching for `"strategic plan" 2024` will cause the search engine to fail. Search broadly for `"strategic plan"` and evaluate the date by reading the returned snippets instead.

PROCESS:
1. Execute concurrent searches using `search_site` immediately.
2. Read the snippets returned by the tool. Check the snippets carefully for dates (e.g., 2024, 2025).
3. If a snippet looks exactly like a document you need AND it appears recent, you MUST explicitly call `save_relevant_url` to save it to the download queue.
4. You MUST manually save every single URL you want. They are NOT saved automatically when you search.
5. Keep searching and saving until you have exhausted search variations for ALL required items.

When you believe you have found and saved all the necessary URLs, you can output 'DONE'.
"""
        messages = [
            {"role": "user", "content": "Begin your targeted search mapping. Keep using the search tool until you have thoroughly looked for everything."}
        ]
        
        tools = [
            {
                "name": "search_site",
                "description": "Searches the web. YOU MUST structure queries like `site:domain.com your keywords`.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The exact search query to execute on Tavily"},
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "save_relevant_url",
                "description": "Save a highly-relevant, recent URL to the final download queue.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The exact URL to save"},
                        "reasoning": {"type": "string", "description": "Why this is relevant (e.g., 2025 Board Minutes)"}
                    },
                    "required": ["url", "reasoning"]
                }
            }
        ]

        master_urls = set()
        loops = 0
        max_loops = 15 # Allow enough loops if rate limited
        
        while loops < max_loops:
            loops += 1
            logger.info(f"Agentic Discovery Loop {loops}/{max_loops}...")
            
            response = self.anthropic.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1000,
                system=system_prompt,
                messages=messages,
                tools=tools,
                temperature=0.2
            )
            
            messages.append({"role": "assistant", "content": response.content})
            
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use" and block.name == "search_site":
                        query = block.input["query"]
                        logger.info(f"Claude Executing Search: {query}")
                        try:
                            res = self.tavily.search(query, search_depth="advanced", max_results=5)
                            condensed = []
                            for r in res.get('results', []):
                                if isinstance(r, dict):
                                    url = r.get('url', '')
                                    if domain in urlparse(url).netloc:
                                        condensed.append(f"URL: {url}\nSnippet: {r.get('content', '')}")
                            
                            tool_match_output = "\n\n".join(condensed) if condensed else "No results found on this domain."
                        except Exception as e:
                            tool_match_output = f"Search failed: {e}"
                            
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_match_output
                        })
                    
                    elif block.type == "tool_use" and block.name == "save_relevant_url":
                        url = block.input["url"]
                        reason = block.input.get("reasoning", "")
                        logger.info(f"Claude Saving URL: {url} -> {reason}")
                        master_urls.add(url)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"URL saved to queue."
                        })
                
                messages.append({"role": "user", "content": tool_results})
            else:
                logger.info("Agent finished its mapping process.")
                break
                
        logger.info(f"Agentic discovery complete. Discovered {len(master_urls)} total URLs during its search process.")
        return list(master_urls)
