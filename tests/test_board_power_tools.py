import logging
import os
from anthropic import Anthropic
from data_sources.tavily_client import K12TavilyClient
from data_sources.board_meetings import BoardMeetingIntelligence
import json, os
from config.product_context import ProductContext
_profile_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'product_profile.json')
AI_TEACHING_TEMPLATE = ProductContext(**json.load(open(_profile_path)))
from config.settings import TAVILY_API_KEY, ANTHROPIC_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_board_intel_power_tools():
    tavily = K12TavilyClient(TAVILY_API_KEY, budget=30)
    anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
    board_intel = BoardMeetingIntelligence(tavily, anthropic)
    
    district_name = "Fairfax County Public Schools"
    state = "VA"
    
    print(f"\n--- Testing Board HOOVER Scan for {district_name} ---")
    print("This will harvest multi-year history and use LocalRAG to filter segments.")
    report = board_intel.full_scan(district_name, state, AI_TEACHING_TEMPLATE)
    
    print(f"\nStatus: {report.status}")
    print(f"Platform: {report.platform}")
    print(f"Board Page URL: {report.board_page_url}")
    print(f"Meetings Analyzed: {report.meetings_analyzed}")
    
    if report.technology_items:
        print("\n--- DETECTED TECHNOLOGY SIGNALS (Hoover Mode) ---")
        for item in report.technology_items:
            print(f"- [{item.meeting_date}] {item.agenda_item} ({item.signal_strength})")
            print(f"  Stage: {item.stage} | Timeline: {item.estimated_purchase_timeline}")
            print(f"  Detail: {item.detail[:100]}...")
            
    if report.leadership_signals:
        print("\n--- LEADERSHIP SENTIMENT (Qualitative Gold) ---")
        for s in report.leadership_signals:
            print(f"- {s.get('leader_name')}: {s.get('sentiment')} on {s.get('topic')}")
            print(f"  {s.get('detail')[:150]}...")

    if report.status == "complete" and not report.technology_items and not report.leadership_signals:
        print("\nNo direct signals or qualitative insights found in the filtered segments.")

if __name__ == "__main__":
    test_board_intel_power_tools()
