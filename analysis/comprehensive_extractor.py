import json
import logging
from anthropic import Anthropic
from models.district import DistrictProfile
from config.product_context import ProductContext

logger = logging.getLogger(__name__)

class ComprehensiveExtractor:
    def __init__(self, anthropic_client: Anthropic):
        self.anthropic = anthropic_client

    def extract_all_data_points(self, profile: DistrictProfile, context: ProductContext):
        if not profile.corpus:
            logger.warning("No corpus available for comprehensive extraction.")
            return

        logger.info("Executing comprehensive LLM extraction against district corpus...")

        # Limit to 500k chars for safety
        safe_corpus = profile.corpus[:500000]

        prompt = f"""You are a relentless K12 Research Analyst.
Your goal is to parse the attached scraped website and document corpus for {profile.district_name}, {profile.state} and extract as many data points as possible out of the '80+ target data points' we track.

PRODUCT CONTEXT (Keep this in mind for relevance):
Category: {context.product_category}

Extract all available information into a massive JSON object mapped to the following categories. If a specific point is not found in the text, omit it or use null. Do not hallucinate data that isn't in the corpus.

CATEGORIES TO EXTRACT:
1. Executive Leadership (Names, titles, emails of Superintendent, IT Director, Academics, etc.)
2. Strategic Goals (Mission statement, current 3-5 year strategic plan highlights)
3. Budget & Funding (Mentions of ESSER, Title I, general fund sizes, bond measures)
4. Current Incumbent & Tech Stack (IDENTIFY WHO CURRENTLY PROVIDES THEIR {context.product_category}. Also list LMS, SIS, devices used).
5. Pain Points (Challenges mentioned in board minutes or letters to parents)
6. Department Details (HR, Special Ed, Curriculum frameworks)

Return ONLY valid JSON in this structural format:
{{
  "leadership": [{{"name": "...", "title": "..."}}],
  "strategic_goals": ["...", "..."],
  "budget_signals": ["...", "..."],
  "incumbents_and_tech_stack": ["Current {context.product_category} provider is [X]", "..."],
  "pain_points": ["...", "..."],
  "department_notes": {{"HR": "...", "SpecialEd": "..."}}
}}

CORPUS TEXT:
{safe_corpus}
"""
        try:
            response = self.anthropic.messages.create(
                model="claude-haiku-4-5",
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text
            if response.stop_reason == "max_tokens":
                logger.warning("Comprehensive extraction hit max_tokens; output may be truncated")
            if "```json" in text:
                text = text.split("```json")[-1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[-1].split("```")[0].strip()
            elif "{" in text and "}" in text:
                text = text[text.find("{"):text.rfind("}") + 1]
                
            data = json.loads(text)
            
            # Merge this massive dataset into the district's metadata 
            profile.metadata["comprehensive_extraction"] = data
            logger.info("Successfully extracted deep data points from the internal corpus.")
            
        except Exception as e:
            logger.error(f"Comprehensive extraction failed: {e}")
