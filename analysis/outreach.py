"""
Outreach email sequence generator (ported from the original client engagement).

Turns a saved research dossier into a profile-based email sequence: one email
per matched ICP target profile, ordered by funding-angle strength, personalized
with intelligence evidence from the dossier. Writing style is governed by the
guideline files in prompts/ (core_rules.md is the authority).

The product identity comes from config/product_profile.json; the per-profile
pain points / capability pitches below are the product-specific mapping — edit
OUTREACH_MAP alongside the profile rules when adapting for another product.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")

# Profile -> email angle mapping for the shipped (anonymized) AI literacy tool.
OUTREACH_MAP = {
    "State Money + Literacy Gap": {
        "pain_point": "Significant LCFF funding but reading proficiency remains critically low",
        "capability": "AI Reading Fluency Tutor",
        "capability_pitch": (
            "The product's AI reading tutor gives students the daily guided read-aloud "
            "practice their curriculum alone isn't providing — with real-time feedback "
            "on fluency, pronunciation, and accuracy."
        ),
        "funding_angle": "LCFF Supplemental & Concentration Grants",
        "funding_priority": 1,
    },
    "Mandated to Improve": {
        "pain_point": "CSI/ATSI/TSI schools required to implement evidence-based reading interventions",
        "capability": "Post-Screener Reading Intervention",
        "capability_pitch": (
            "The product provides evidence-based reading practice with Lexile progress "
            "data that supports improvement plan documentation — the intervention "
            "layer their screener needs."
        ),
        "funding_angle": "School Improvement Funds + Title I Part A + LCFF",
        "funding_priority": 2,
    },
    "Title I Heavyweight": {
        "pain_point": "Large Title I allocation explicitly for supplemental reading instruction",
        "capability": "AI Reading Fluency Tutor",
        "capability_pitch": (
            "The product qualifies as supplemental evidence-based reading instruction "
            "under Title I — AI-guided fluency practice that supplements the core curriculum."
        ),
        "funding_angle": "Title I Part A",
        "funding_priority": 2,
    },
    "EL Pipeline Problem": {
        "pain_point": "EL students stuck at Beginning on ELPAC, not building English reading fluency",
        "capability": "EL Reading Fluency Support",
        "capability_pitch": (
            "The product's AI pronunciation feedback helps EL students build English "
            "reading fluency through guided read-aloud practice — the foundation "
            "for reclassification."
        ),
        "funding_angle": "Title III (English Language Acquisition) + Title I Part A",
        "funding_priority": 3,
    },
    "Disengagement Crisis": {
        "pain_point": "High chronic absence means students are missing reading instruction and falling behind",
        "capability": "Home Reading & Family Engagement",
        "capability_pitch": (
            "The product's parent portal and home reading feature let students practice "
            "fluency even when absent — and the engaging AI tutor format helps "
            "re-engage disengaged readers."
        ),
        "funding_angle": "LCFF + Title I Part A (Parent & Family Engagement set-aside)",
        "funding_priority": 4,
    },
    "SPED/Dyslexia Gap": {
        "pain_point": "Large SPED population with reading-related disabilities, now being screened under SB 114",
        "capability": "Lexile Progress Monitoring",
        "capability_pitch": (
            "The product provides the fluency practice and Lexile progress tracking "
            "students identified by screening need — with data that supports "
            "IEP goal documentation."
        ),
        "funding_angle": "IDEA Part B + Title I Part A",
        "funding_priority": 5,
    },
}

OUTREACH_PROMPT = """You are a sales copywriter for {product_name}. You write short, personalized
outreach email SEQUENCES to school district administrators.

=== WHAT THE PRODUCT IS ===
{one_liner}

=== WRITING GUIDELINES (primary authority on tone, structure, evidence usage) ===
{guidelines}

=== DISTRICT: {district_name} ===

=== INTELLIGENCE REPORT ===
{report_json}

=== EMAIL SEQUENCE INSTRUCTIONS ===

Write a sequence of {num_emails} emails. Each email is pre-assigned a profile,
pain point, product capability, and funding angle. Your job is to WRITE the email
using the intelligence report to personalize it — but follow the WRITING GUIDELINES
above as your primary authority on tone, structure, and evidence usage.

IMPORTANT: This entire sequence will be sent to ONE person — the same recipient
receives all emails in order. Write all emails so they work for any district
administrator. Use "Hi" without a name — the rep personalizes the greeting.

SEQUENCE RULES:
- Email 1 introduces the product. Subsequent emails reference "my last note" or
  open with a fresh angle — follow the WRITING GUIDELINES for follow-up variety.
- Do NOT suggest contacts in the emails. The rep chooses the recipient separately.

=== EMAIL ASSIGNMENTS ===
{email_assignments}

Respond ONLY with valid JSON:
{{
  "emails": [
    {{
      "sequence_number": 1,
      "profile": "profile name",
      "subject_line": "...",
      "body": "the email body text (start with 'Hi' — no name, no signature)",
      "evidence_used": "what intelligence finding this email is based on (or 'trend-based' if none)",
      "funding_source": "the assigned funding angle"
    }}
  ]
}}"""


def _load_guidelines(budget_chars: int = 12000) -> str:
    """Concatenate prompts/*.md, core_rules.md first, within a char budget."""
    parts = []
    try:
        files = sorted(os.listdir(PROMPTS_DIR))
    except FileNotFoundError:
        return "Write concise, curiosity-driven emails. Lead with what the district is doing, not their problems."
    ordered = ["core_rules.md"] + [f for f in files if f != "core_rules.md" and f.endswith(".md")]
    used = 0
    for fname in ordered:
        path = os.path.join(PROMPTS_DIR, fname)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            text = f.read()
        if used + len(text) > budget_chars and parts:
            break
        parts.append(f"--- {fname} ---\n{text}")
        used += len(text)
    return "\n\n".join(parts)


def _slim_report(profile_data: dict) -> dict:
    """Boil the saved dossier down to what the copywriter needs."""
    board = profile_data.get("board_meeting_report") or {}
    news = profile_data.get("news_report") or {}
    return {
        "district_name": profile_data.get("district_name"),
        "intelligence_brief": (profile_data.get("intelligence_brief") or "")[:4000],
        "buying_signals": [
            {k: s.get(k) for k in ("signal_type", "description", "strength") if k in s}
            for s in (profile_data.get("signals") or [])[:10]
        ],
        "board_findings": {
            "technology_items": (board.get("technology_items") or [])[:8],
            "leadership_signals": (board.get("leadership_signals") or [])[:5],
            "timeline_summary": board.get("timeline_summary") or "",
        },
        "news_problems": (news.get("problems") or [])[:6],
        "vendor_mentions": (board.get("vendor_mentions") or [])[:6],
        "contacts": [
            {k: c.get(k) for k in ("name", "title", "is_new") if k in c}
            for c in (profile_data.get("contacts") or [])[:10]
        ],
        "tech_stack": {
            "lms": profile_data.get("lms"),
            "sis": profile_data.get("sis"),
            "ecosystem": profile_data.get("ecosystem"),
        },
    }


def _contact_suggestions(profile_data: dict, buyer_titles: list) -> list:
    """Suggest recipients, strongest reason first. Evidence-based only."""
    suggestions = []
    for c in profile_data.get("contacts") or []:
        name, title = c.get("name"), c.get("title") or ""
        if not name:
            continue
        if c.get("is_new"):
            suggestions.append({"name": name, "title": title, "email": c.get("email"),
                                "reason": "New in role — likely open to new tools"})
        elif any(bt.lower() in title.lower() for bt in buyer_titles):
            suggestions.append({"name": name, "title": title, "email": c.get("email"),
                                "reason": "Title matches the product's primary buyer profile"})
    return suggestions[:5]


def generate_outreach(result_id: int) -> dict:
    """Generate and persist an outreach sequence for a saved research result."""
    from database import SessionLocal
    from models.research_result import ResearchResultModel
    from data_sources.local_funding import LocalFundingData, PROFILE_DEFINITIONS
    from main import load_product_context
    from anthropic import Anthropic
    from config.settings import ANTHROPIC_API_KEY

    db = SessionLocal()
    try:
        record = db.query(ResearchResultModel).filter(ResearchResultModel.id == result_id).first()
        if not record:
            return {"error": "Result not found"}
        profile_data = dict(record.profile_data or {})

        context = load_product_context()

        # Matched ICP profiles come from the funding dataset
        row = LocalFundingData.lookup(nces_id=profile_data.get("nces_id"),
                                      district_name=record.district_name, state=record.state)
        matched = [p["name"] for p in PROFILE_DEFINITIONS
                   if row and row.get(p["key"]) == 1 and p["name"] in OUTREACH_MAP]
        if not matched:
            return {"error": "No ICP target profiles matched — outreach sequences are profile-driven"}
        matched.sort(key=lambda p: OUTREACH_MAP[p]["funding_priority"])
        matched = matched[:4]  # a 4-email sequence is plenty

        assignments = []
        for i, name in enumerate(matched):
            m = OUTREACH_MAP[name]
            assignments.append(
                f"Email {i + 1}:\n"
                f"  Profile: {name}\n"
                f"  Pain point: {m['pain_point']}\n"
                f"  Product capability: {m['capability']}\n"
                f"  Capability pitch: {m['capability_pitch']}\n"
                f"  Funding angle: {m['funding_angle']}\n"
            )

        prompt = OUTREACH_PROMPT.format(
            product_name=context.product_name,
            one_liner=context.one_liner,
            guidelines=_load_guidelines(),
            district_name=record.district_name,
            report_json=json.dumps(_slim_report(profile_data), indent=1, default=str)[:15000],
            num_emails=len(matched),
            email_assignments="\n".join(assignments),
        )

        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(text)

        result["profiles_used"] = matched
        result["suggested_contacts"] = _contact_suggestions(profile_data, context.primary_buyer_titles)

        profile_data["outreach"] = result
        record.profile_data = profile_data
        db.commit()
        logger.info(f"Outreach sequence saved for {record.district_name} ({len(result.get('emails', []))} emails)")
        return result
    except json.JSONDecodeError:
        return {"error": "Failed to parse the generated sequence — try again"}
    except Exception as e:
        logger.error(f"Outreach generation failed for result {result_id}: {e}")
        return {"error": str(e)}
    finally:
        db.close()
