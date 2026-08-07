import json
from anthropic import Anthropic
from models.district import DistrictProfile
from models.buying_profile import BuyingProfile
from config.product_context import ProductContext

class BuyingProfileAnalyzer:
    """
    Analyzes historical data (Board records, E-Rate, RFPs) to determine a district's buying behavior.
    """
    
    def __init__(self, anthropic_client: Anthropic):
        self.client = anthropic_client

    def analyze(self, profile: DistrictProfile, context: ProductContext) -> BuyingProfile:
        board_items = []
        vendor_mentions = []
        if profile.board_meeting_report:
            board_items = [item.agenda_item for item in profile.board_meeting_report.technology_items]
            vendor_mentions = [f"{v.vendor_name} ({v.implication})" for v in profile.board_meeting_report.vendor_mentions]
        
        erate_data = []
        if profile.erate_report:
            for req in profile.erate_report.funding_history:
                erate_data.append(f"{req.funding_year}: {req.form_type} for {req.product_service_description} - Status: {req.status} (Vendor: {req.vendor_name})")
        
        prompt = f"""
        You are an expert K12 Sales Strategist. Your goal is to analyze the following data for '{profile.district_name}' 
        to determine their "Buying Profile" and "Procurement Behavior."

        PRODUCT CONTEXT:
        - Product: {context.product_name}
        - Category: {context.product_category}
        - One-liner: {context.one_liner}

        DATA TO ANALYZE:
        1. E-Rate & RFP History (Form 470/471): {erate_data}
        2. Board Technology Actions & Vendor Mentions: {board_items} | Mentions: {vendor_mentions}
        3. Current Tech Landscape: {profile.sis}, {profile.lms}, 1:1={profile.one_to_one_program}

        ANALYSIS FOCUS:
        - **RFP Award Pattern**: Do they always choose the same vendors (Loyalty)? Are there mentions of "lowest bid" wins (Price Sensitive)?
        - **Procurement Velocity**: How long is the gap between a Form 470 (RFP) and a Form 471 (Award/Commitment)?
        - **Competitor Sentiment**: Are incumbents being praised or criticized in board minutes?

        CATEGORIES:
        - **Innovator**: Early adopter, pilots new tech, fast procurement.
        - **Value Seeker**: High price sensitivity, lowest-bid preference, heavy grant usage.
        - **Incumbent Loyalist**: High vendor loyalty, rare switches, long-term contracts.
        - **Support Oriented**: Prioritizes service, training, and "high touch" partnerships.

        TONE CONSTRAINT:
        You are an elite, strictly factual intelligence analyst. NO FLUFF. ABSOLUTELY NO HALLUCINATIONS.
        If you do not have EXPLICIT, undeniable evidence of price sensitivity (e.g. they chose the lowest bid) or vendor loyalty, you MUST set the style to 'Insufficient Data'.
        DO NOT infer psychological traits from unrelated topics (e.g. DO NOT claim they are price-sensitive just because they mentioned 'Website Design').
        If no data exists, your 'justification' and 'recommended_sales_strategy' MUST simply state: 'Insufficient historical procurement data to determine a profile.'

        OUTPUT FORMAT (JSON ONLY). YOU MUST ESCAPE ALL INTERNAL QUOTES:
        {{
            "style": "Innovator | Value Seeker | Incumbent Loyalist | Support Oriented",
            "confidence": "HIGH | MEDIUM | LOW",
            "justification": "Detailed reasoning focusing on RFP behavior and award patterns.",
            "procurement_velocity": "FAST | MODERATE | SLOW",
            "price_sensitivity_score": 0-100,
            "vendor_loyalty_score": 0-100,
            "key_procurement_findings": ["Bullet points of evidence including RFP/Award behavior"],
            "recommended_sales_strategy": "Direct advice for the sales rep based on how they win contracts."
        }}
        """

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract JSON from response (handling potential markdown)
            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[-1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[-1].split("```")[0].strip()
            elif "{" in content and "}" in content:
                content = content[content.find("{"):content.rfind("}") + 1]
            
            data = json.loads(content)
            
            return BuyingProfile(
                style=data.get("style", "Unknown"),
                confidence=data.get("confidence", "LOW"),
                justification=data.get("justification", ""),
                procurement_velocity=data.get("procurement_velocity", "MODERATE"),
                price_sensitivity_score=data.get("price_sensitivity_score", 50),
                vendor_loyalty_score=data.get("vendor_loyalty_score", 50),
                key_procurement_findings=data.get("key_procurement_findings", []),
                recommended_sales_strategy=data.get("recommended_sales_strategy", "")
            )
            
        except Exception as e:
            return BuyingProfile(
                style="Unknown",
                confidence="LOW",
                justification=f"Error analyzing profile: {str(e)}",
                procurement_velocity="MODERATE",
                price_sensitivity_score=50,
                vendor_loyalty_score=50
            )
