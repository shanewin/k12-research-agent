import os
# Set these BEFORE any other imports that might use them
os.environ["LINKEDIN_RAPIDAPI_KEY"] = "6eaa82a592msh98f423a090697e5p17d847jsn644c5fa297bd"
os.environ["LINKEDIN_RAPIDAPI_HOST"] = "fresh-linkedin-profile-data.p.rapidapi.com"

import logging
import json
from dotenv import load_dotenv
from data_sources.leadership import LeadershipIntelligence
from data_sources.tavily_client import K12TavilyClient
import json, os
from config.product_context import ProductContext
_profile_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'product_profile.json')
AI_TEACHING_TEMPLATE = ProductContext(**json.load(open(_profile_path)))
from anthropic import Anthropic

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_leadership_pivot():
    load_dotenv()
    
    # Use the keys from .env (User should have added them)
    tavily_key = os.getenv("TAVILY_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    # Note: These are hardcoded in the script for the test IF not in .env
    # define('RAPIDAPI_KEY', '6eaa82a592msh98f423a090697e5p17d847jsn644c5fa297bd');
    # define('RAPIDAPI_HOST', 'fresh-linkedin-profile-data.p.rapidapi.com');
    os.environ["LINKEDIN_RAPIDAPI_KEY"] = "6eaa82a592msh98f423a090697e5p17d847jsn644c5fa297bd"
    
    if not tavily_key or not anthropic_key:
        print("Error: TAVILY_API_KEY or ANTHROPIC_API_KEY not found in .env")
        return

    tavily = K12TavilyClient(tavily_key)
    anthropic = Anthropic(api_key=anthropic_key)
    intelligence = LeadershipIntelligence(tavily, anthropic)
    
    # Test with Fairfax County (A well-known large district)
    district = "Fairfax County Public Schools"
    state = "VA"
    
    print(f"\n--- Testing Leadership Pivot: {district} ---")
    contacts = intelligence.get_leadership_changes(district, state, AI_TEACHING_TEMPLATE)
    
    print(f"\nFound {len(contacts)} verified leadership records:")
    for c in contacts:
        status = "NEW HIRE" if c.is_new else "TENURED"
        print(f"- {c.name} ({c.title}) [{status}]")
        print(f"  Tenure: {c.tenure_months} months (Started: {c.started_at})")
        print(f"  Previous Org: {c.previous_org}")
        print(f"  LinkedIn: {c.linkedin_url}")
        print(f"  Source: {c.source}\n")

if __name__ == "__main__":
    test_leadership_pivot()
