from anthropic import Anthropic
from models.district import DistrictProfile
from config.product_context import ProductContext
import logging

logger = logging.getLogger(__name__)

class SynthesisEngine:
    def __init__(self, anthropic_client: Anthropic):
        self.claude = anthropic_client

    def generate_brief(self, profile: DistrictProfile, context: ProductContext) -> str:
        """
        Synthesize all data into a final intelligence brief.
        Uses Claude with K12 domain expertise prompt.
        """
        prompt = self._build_synthesis_prompt(profile, context)
        
        try:
            response = self.claude.messages.create(
                model="claude-haiku-4-5",
                max_tokens=4096,
                system="You are an expert K12 EdTech sales consultant. Synthesize the provided data into a punchy, actionable intelligence brief.",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error generating brief: {e}")
            return "Failed to generate intelligence brief."

    def _build_synthesis_prompt(self, profile: DistrictProfile, context: ProductContext) -> str:
        # Categorize contacts for higher-fidelity synthesis
        new_hires = [c for c in profile.contacts if c.is_new]
        tenured = [c for c in profile.contacts if not c.is_new]
        
        leadership_summary = "ADMINISTRATIVE TRANSITIONS (LAST 24 MONTHS):\n"
        if new_hires:
            for c in new_hires:
                leadership_summary += f"- {c.name} ({c.title}) | Started: {c.started_at or 'Recently'} | Prev Org: {c.previous_org or 'Unknown'}\n"
        else:
            leadership_summary += "- No major administrative transitions detected in the last 24 months.\n"
            
        leadership_summary += "\nTENURED LEADERSHIP:\n"
        for c in tenured[:10]: # Cap at 10 for tenure
            leadership_summary += f"- {c.name} ({c.title}) [Verified: {c.source}]\n"
        
        # Format board/news highlights
        board_highlights = "None found"
        if profile.board_meeting_report:
            report = profile.board_meeting_report
            signals = []
            if report.technology_items:
                signals.append(f"Found {len(report.technology_items)} tech signals/RFPs.")
            if report.leadership_signals:
                signals.append(f"Detected {len(report.leadership_signals)} leadership sentiment markers.")
            
            board_highlights = "\n".join(signals) if signals else "Scan complete, no direct signals found."
            board_highlights += f"\nTimeline: {report.timeline_summary or 'No specific timeline found.'}"
            
            # Format qualitative signals for Claude
            qual_str = "\n".join([f"- {s.get('leader_name', 'Leader')}: {s.get('sentiment')} on {s.get('topic')} ({s.get('detail')})" for s in report.leadership_signals])
            if qual_str:
                board_highlights += f"\nQualitative Sentiments:\n{qual_str}"
            
        news_highlights = "None found"
        if profile.news_report:
            news_highlights = profile.news_report.district_narrative
            
        erate_summary = "None found"
        if profile.erate_report:
            erate_summary = f"{profile.erate_report.summary} Key Vendors: {', '.join(profile.erate_report.key_vendors)}"
            
        buying_profile_summary = "Not analyzed"
        if profile.buying_profile:
            buying_profile_summary = f"Style: {profile.buying_profile.style} | Confidence: {profile.buying_profile.confidence}\nJustification: {profile.buying_profile.justification}\nStrategy: {profile.buying_profile.recommended_sales_strategy}"
            
        rev_fed = f"${profile.rev_fed_total:,.0f}" if profile.rev_fed_total is not None else "N/A"
        rev_state = f"${profile.rev_state_total:,.0f}" if profile.rev_state_total is not None else "N/A"
        rev_local = f"${profile.rev_local_total:,.0f}" if profile.rev_local_total is not None else "N/A"

        comprehensive_data = "Not found"
        if "comprehensive_extraction" in profile.metadata:
            import json
            comprehensive_data = json.dumps(profile.metadata["comprehensive_extraction"], indent=2)
        
        scraped_urls = profile.metadata.get("scraped_urls", [])
        source_links_section = ""
        urls_to_list = scraped_urls[:15]
        for i, url in enumerate(urls_to_list):
            source_links_section += f"[{i+1}] {url}\n"
        
        if profile.board_meeting_report and profile.board_meeting_report.board_page_url:
            source_links_section += f"[{len(urls_to_list)+1}] {profile.board_meeting_report.board_page_url} (Board Portal)\n"
            
        if not source_links_section:
            source_links_section = "No specific URLs tracked."
            
        return f"""
        Generate a high-impact K12 Intelligence Brief for {profile.district_name}, {profile.state}.
        
        THE COMPANY AND PRODUCT:
        Company: {context.company_name}
        Product: {context.product_name}
        Category: {context.product_category}
        Description: {context.one_liner}
        Competitors: {', '.join(context.direct_competitors)}
        Typical deal size: {context.typical_deal_size}
        
        DISTRICT DATA (NCES):
        Enrollment: {profile.total_enrollment}
        Per-Pupil Expenditure: ${profile.per_pupil_expenditure or 'N/A'}
        Revenue: Fed {rev_fed} | State {rev_state} | Local {rev_local}
        Locale: {profile.locale_type}
        
        TECH LANDSCAPE:
        Ecosystem: {profile.ecosystem}
        SIS: {profile.sis} | LMS: {profile.lms}
        1:1 Program: {profile.one_to_one_program}
        
        E-RATE & FUNDING (USAC):
        {erate_summary}
        
        DISTRICT BUYING PROFILE:
        {buying_profile_summary}
        
        DECISION MAKERS & TURNOVER:
        {leadership_summary}
        
        DEEP CORPUS INTELLIGENCE (FROM STRATEGIC PLANS, BUDGETS, RFPs):
        {comprehensive_data}
        
        BOARD MEETING INTELLIGENCE (The Strategic 'WHY'):
        {board_highlights}
        
        NEWS INTELLIGENCE:
        {news_highlights}
        
        ICP SCORE: {profile.icp_score}/100
        RECOMMENDED ACTION: {profile.recommended_action}
        
        SOURCE LINKS DISCOVERED:
        {source_links_section}
        
        TOTAL CONTEXT AVAILABLE: 80+ Data Points.
        
        **CRITICAL INSTRUCTION ON TONE:** 
        You are an elite, dry, aggressive CIA intelligence analyst briefing a top-tier cybersecurity sniper.
        ABSOLUTELY ZERO FLUFF. ZERO generic ChatGPT sales phrases.
        NEVER say things like "presents a unique opportunity" or "in today's digital landscape".
        Just hard facts, numbers, dates, and names. 
        **CRITICAL:** YOU MUST USE INLINE CITATIONS. Every single fact or tech architecture MUST be cited using the exact matching bracket [1] or [2] from the SOURCE LINKS DISCOVERED. NEVER cite multiple documents at once, and NEVER invent a citation if the fact is missing.
        
        Structure the brief ONLY using markdown bullet points for these headers:
        
        # 1. Actionable Snapshot
        Provide a 1-2 sentence extremely dry summary of the absolute most critical intelligence found. NEVER mention 'evaluating' or 'potential interest' or 'timelines' unless you have a specific date and document to prove it. Provide ONLY facts. If no actionable intelligence was found, state exactly: 'No direct product intent discovered in the scanned corpus.' Do not attach citations if no intelligence was found.
        
        # 2. Targeted Decision Makers
        Only list specific administrators and their titles from the DECISION MAKERS & TURNOVER section above. Do not write filler text. If you don't see a specific person listed there, state "No specific contact found for this role."
        
        # 3. Verified Buying Signals
        Specify dates, topics, names found from Board Meetings or DEEP CORPUS INTELLIGENCE. If you don't have hard data for {context.product_category}, explicitly state "No hard signals detected for this product category" and DO NOT infer it from unrelated things (like economic development). NEVER hallucinate filler text. A school district NEVER "lacks a formal website" or "lacks an SIS"; if you don't know the vendor, say "Vendor unknown, highly vulnerable to displacement."
        
        # 4. Tech Landscape & Tech Risk
        Present the SIS, LMS, and Product Incumbent as a strict markdown bulleted list (one per line). If a vendor is not explicitly named in a specific source document, state "Vendor unknown, highly vulnerable to displacement." and DO NOT provide a citation bracket for it. Note competitive roadblocks like {', '.join(context.direct_competitors) if context.direct_competitors else 'unknown'}.
        
        # 5. Procurement Strategy
        How does their {profile.buying_profile.style if profile.buying_profile else 'unknown'} buying profile affect the tactical sales play? (1-2 sentences. Hard tactical advice. NO FLUFF!)

        # 7. Verified Source Documents
        Output the EXACT block of text provided in the "SOURCE LINKS DISCOVERED" section above, preserving the [1], [2] formatting identically.

        **FINAL WARNING:**
        If the final output contains typical AI conversational filler or generic sales-bro paragraphs, you will fail the mission. BULLETS FAST FACTS DRY TONE ONLY.
        """
