import logging
from typing import Optional
import json
from .tavily_client import K12TavilyClient
from anthropic import Anthropic
from models.district import DistrictProfile
from config.product_context import ProductContext

logger = logging.getLogger(__name__)

class TechProfileDetector:
    def __init__(self, tavily_client: K12TavilyClient, anthropic_client: Anthropic):
        # tavily_client is retained for backwards compatibility or edge cases, 
        # but the primary extraction now uses the ingested bulk corpus.
        self.tavily = tavily_client
        self.anthropic = anthropic_client

    def detect_tech_landscape(self, district_name: str, state: str, profile: DistrictProfile, context: Optional[ProductContext] = None):
        """
        Identify the core technology stack of the district using the massive ingested internal corpus.
        """
        if not profile.corpus:
            logger.warning("No corpus found for tech landscape extraction.")
            return

        logger.info(f"Analyzing {len(profile.corpus)} characters of domain corpus for Tech Landscape...")

        # We constrain the text slightly if it's absurdly large to avoid breaking token limits
        # Haiku handles ~200k tokens (roughly ~800,000 chars), we'll safely limit to 500k chars
        safe_corpus = profile.corpus[:500000]

        prompt = f"""Review the following comprehensive ingested corpus from the {district_name} official website and documents.
Extract the technical landscape and infrastructure details. Focus on identifying their precise systems.

IMPORTANT: When identifying vendors for {context.product_category if context else 'the main product'}, look closely for clues like "Designed by [Agency]", "Powered by [Company]", or "Website by [Agency]" at the bottom of pages, as well as known competitors: {context.direct_competitors if context else 'None'}.

Return ONLY valid JSON in this exact format, substituting null or empty lists if an element is unknown:
{{
  "ecosystem": "Google or Microsoft",
  "sis": "Name of Student Information System",
  "lms": "Name of Learning Management System",
  "one_to_one_program": true/false,
  "incumbent_vendors": ["Vendor A", "Vendor B"]
}}

CORPUS TEXT:
{safe_corpus}
"""
        
        try:
            response = self.anthropic.messages.create(
                model="claude-haiku-4-5",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text
            if "```json" in text:
                text = text.split("```json")[-1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[-1].split("```")[0].strip()
            elif "{" in text and "}" in text:
                text = text[text.find("{"):text.rfind("}") + 1]
            
            data = json.loads(text)
            
            profile.ecosystem = data.get("ecosystem", "Unknown")
            profile.sis = data.get("sis", "Unknown")
            profile.lms = data.get("lms", "Unknown")
            profile.one_to_one_program = bool(data.get("one_to_one_program", False))
            profile.current_vendors = data.get("incumbent_vendors", [])
            logger.info(f"Corpus extraction yielded tech profile: {{'ecosystem': '{profile.ecosystem}', 'sis': '{profile.sis}', 'lms': '{profile.lms}', 'vendors': {profile.current_vendors}}}")
            
        except Exception as e:
            logger.error(f"Claude failed to parse tech landscape from corpus: {e}")
