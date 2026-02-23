import logging
from agent import K12ResearchAgent
from config.templates import AI_TEACHING_TEMPLATE
from output.formatters import OutputFormatter

# Configure logging
logging.basicConfig(level=logging.INFO)

def run_e2e_test():
    # Initialize the agent with the AI Teaching (Kira Learning) context
    agent = K12ResearchAgent(product_context=AI_TEACHING_TEMPLATE, budget=30)
    
    # Research Fairfax County Public Schools (VA)
    # Using small dummy name to test faster if needed, but let's go for it
    try:
        profile = agent.research_district("Fairfax County Public Schools", "VA")
        
        print("\n" + "="*50)
        print("RESEARCH COMPLETE")
        print("="*50)
        print(f"District: {profile.district_name}")
        print(f"ICP Score: {profile.icp_score}")
        print(f"Signal Strength: {profile.signal_strength}")
        print(f"Action: {profile.recommended_action}")
        print(f"Tavily Credits: {profile.tavily_credits_used}")
        print("\nINTELLIGENCE BRIEF:")
        print(OutputFormatter.to_markdown(profile))
        print("="*50)
        
    except Exception as e:
        print(f"E2E Test Failed: {e}")

if __name__ == "__main__":
    run_e2e_test()
