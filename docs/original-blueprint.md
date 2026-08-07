# K12 District Research Agent — Architecture Blueprint

## What This Is

An AI agent that takes a school district name and produces a comprehensive intelligence brief for EdTech sales teams. It pulls structured data from public APIs, searches the web for buying signals, identifies decision makers, and uses Claude to synthesize everything into an actionable dossier.

The agent makes autonomous decisions about what to search for based on what it finds. If it discovers a new superintendent, it researches their background. If it finds an RFP, it extracts the full document. If it finds ESSER funding, it calculates urgency based on deadlines.

---

## Data Sources and APIs

### 1. Urban Institute Education Data API (NCES Data)
- **URL:** `https://educationdata.urban.org/api/v1/`
- **Auth:** None required (free, public)
- **Key endpoints:**
  - `school-districts/ccd/directory/{year}/` — name, address, locale, phone, enrollment
  - `school-districts/ccd/enrollment/{year}/` — enrollment by race/grade
  - `school-districts/ccd/finance/{year}/` — per-pupil expenditure, revenue by source
  - `schools/ccd/directory/{year}/` — individual schools within a district
- **Filters:** `?district_name=Springfield&fips=17` (FIPS for state)
- **Returns:** JSON with pagination (`next` URL)
- **Note:** Data runs 1-2 years behind. Latest in 2026 is probably school year 2023-24 (year=2023 in API)
- **Docs:** https://educationdata.urban.org/documentation/

### 2. Apollo.io API
- **Auth:** API key in header (`x-api-key`)
- **Free tier:** Limited credits/month
- **Key endpoint:** `POST /v1/mixed_people/search`
- **Returns:** name, title, email, phone, linkedin_url, tenure
- **K12 note:** Large districts (50K+) have good coverage. Small/rural may return nothing — use Tavily fallback.
- **Docs:** https://docs.apollo.io/

### 3. Tavily Search API
- **Auth:** API key
- **Free tier:** 1,000 credits/month
- **Methods:** search, extract, crawl, map
- **Cost:** basic search = 1 credit, advanced = 2 credits, extract = 1 credit per 5 URLs
- **Best practices:**
  - Wrap district name in quotes for relevance: `"Springfield Public Schools"`
  - Use `search_depth="advanced"` for LinkedIn
  - Use `include_domains` to filter to district websites
  - Use `time_range="month"` or `"year"` for recent signals
  - Budget 15-20 credits per district

### 4. Anthropic Claude API
- **Model:** claude-sonnet-4-20250514
- **Use for:** Signal analysis decisions (agentic loop), final dossier synthesis
- **Cost:** ~$0.05-0.15 per district

---

## Complete ICP Data Points

### A: District Firmographics (NCES API)

| Data Point | API Field |
|---|---|
| District name | `lea_name` |
| NCES ID | `leaid` |
| State | `fips` / `state_name` |
| City / County | `city_location`, `county_name` |
| Total enrollment | `enrollment` |
| Number of schools | count from schools endpoint |
| Grade span | `grade_lo_offered`, `grade_hi_offered` |
| Locale type | `urban_centric_locale` (City-Large, Suburb-Mid, Rural-Remote, etc.) |
| Title I eligible | school-level Title I status |
| Free/reduced lunch count and % | `free_lunch_eligible`, `reduced_lunch_eligible` / total |
| Total revenue / expenditures | `rev_total`, `exp_total` |
| Per-pupil expenditure | `exp_current_instruction_per_pupil` |
| Federal / State / Local revenue split | `rev_fed_total`, `rev_state_total`, `rev_local_total` |
| Student demographics (race/ethnicity) | enrollment by race fields |
| ELL % | English learner counts |
| SPED % | Students with disabilities counts |

### B: Decision Makers (Apollo + Tavily fallback)

| Data Point | Search Strategy |
|---|---|
| Superintendent | Apollo title search: "Superintendent" |
| CTO / Director of Technology | Titles: "Chief Technology", "Director of Technology", "Director of IT", "CIO" |
| Director of Curriculum / CAO | Titles: "Curriculum", "Chief Academic", "Instruction" |
| Director of Procurement | Titles: "Procurement", "Purchasing", "Business Manager" |
| Contact emails, phones, LinkedIn | Apollo fields |
| Tenure at current role | `started_at` or web search |
| Previous district (for new leaders) | Tavily: "{name} superintendent previously" |
| Previous district tech initiatives | Tavily: "{name} {previous district} technology" |

**Apollo search body:**
```json
{
  "q_organization_name": "Springfield Public Schools",
  "person_titles": [
    "Superintendent", "Chief Technology Officer", "Director of Technology",
    "Director of Information Technology", "Chief Information Officer",
    "Chief Academic Officer", "Director of Curriculum", "Director of Instruction",
    "Director of Procurement", "Business Manager", "Assistant Superintendent"
  ],
  "page": 1, "per_page": 25
}
```

### C: Technology Profile (Tavily Search)

| Data Point | Query Pattern |
|---|---|
| Google vs Microsoft ecosystem | `"{district}" "Google Workspace" OR "Microsoft 365" OR Chromebook` |
| 1:1 device program | `"{district}" "1:1" OR "one to one" device Chromebook iPad` |
| SIS | `"{district}" "PowerSchool" OR "Infinite Campus" OR "Skyward" OR "Tyler SIS"` |
| LMS | `"{district}" "Canvas" OR "Schoology" OR "Google Classroom"` |
| Technology plan | `"{district}" technology plan` (include_domains: district website) |
| E-Rate participation | `"{district}" E-Rate` |
| Current vendors | `"{district}" edtech vendor OR contract` |

### D: Buying Signals (Tavily — The Agentic Part)

| Signal | Query Pattern | Strength |
|---|---|---|
| Active RFPs | `"{district}" RFP "request for proposal" technology` | HIGH |
| Board meeting tech agenda items | `"{district}" board meeting agenda technology strategic plan` | HIGH |
| New superintendent (< 18 months) | `"{district}" superintendent appointed OR hired OR new` | HIGH |
| ESSER funding remaining | `"{district}" ESSER stimulus funding remaining allocation` | HIGH |
| Bond measure passed | `"{district}" bond measure referendum technology` | HIGH |
| New CTO/Tech Director | `"{district}" "director of technology" CTO hired appointed` | MEDIUM-HIGH |
| Technology strategic plan review | `"{district}" "technology plan" review update strategic` | MEDIUM |
| Grant awards | `"{district}" grant awarded technology STEM innovation` | MEDIUM |
| Job postings (tech roles) | `"{district}" hiring "instructional technology" "digital learning"` | MEDIUM |
| Conference attendance | `"{district}" ISTE OR CoSN OR FETC conference` | MEDIUM |
| Curriculum adoption cycle | `"{district}" curriculum adoption textbook review` | MEDIUM |
| New school construction | `"{district}" new school building construction expansion` | LOW-MEDIUM |

### E: Financial / Funding Signals (Tavily + NCES)

| Data Point | Source |
|---|---|
| Per-pupil vs state average | NCES (compare to state median) |
| ESSER allocation total + remaining | Tavily search |
| ESSER deadline status | Tavily (extensions, waivers) |
| Title I/II/III/IV allocations | NCES finance |
| Recent bond measures | Tavily search |
| E-Rate applications | Tavily search |
| State innovation grants | Tavily search |

### F: CRM Data (Optional Input from Client)

| Data Point | Type |
|---|---|
| Previous engagement history | Optional dict |
| Existing customer (cross-sell) | Optional bool |
| Event engagement | Optional list |
| Known champion | Optional string |
| Competitor installed | Optional string |
## Agent Architecture

```
Input: district_name, state, product_category (optional), crm_data (optional)
  |
  +-- Step 1: NCES Baseline Pull (deterministic)
  |    Urban Institute API -> firmographics, finance, enrollment
  |
  +-- Step 2: Decision Maker Identification (deterministic -> fallback)
  |    Apollo API -> contacts by title
  |    If sparse -> Tavily: district website staff directory + LinkedIn
  |
  +-- Step 3: Signal Detection (AGENTIC - Claude decides next searches)
  |    Run initial Tavily searches (board meetings, RFPs, leadership, funding)
  |    Claude analyzes results -> decides what to search next
  |       Found new superintendent -> search their background
  |       Found RFP -> extract full document
  |       Found board agenda -> extract agenda, identify tech items
  |       Found ESSER mention -> search allocation + spend status
  |       Found job posting -> determine role significance
  |       Found nothing -> try broader searches
  |    Repeat until budget exhausted or sufficient coverage (max 15-20 Tavily calls)
  |
  +-- Step 4: Technology Profile (deterministic Tavily searches)
  |    SIS, LMS, devices, Google vs Microsoft
  |
  +-- Step 5: Synthesis (Claude API)
       All data -> Claude with K12 domain expertise prompt
       Output: structured intelligence brief
```

---

## File Structure

```
k12_research_agent/
  agent.py              # Main K12ResearchAgent class, orchestrates everything
  config/
    __init__.py
    product_context.py  # ProductContext dataclass — shapes all searches and scoring
    templates.py        # Pre-built configs: SIS, LMS, adaptive learning, AI teaching
    settings.py         # API keys via .env, constants, FIPS codes
  data_sources/
    __init__.py
    nces.py             # Urban Institute Education Data API client
    apollo.py           # Apollo.io API client (uses ProductContext for title priority)
    tavily_client.py    # Tavily wrapper with K12-specific search methods + budget tracking
    board_meetings.py   # Board Meeting Intelligence Module — discover, extract, analyze
    news_intel.py       # News Intelligence Module — 18 months of coverage, problem detection
  analysis/
    __init__.py
    signals.py          # SignalDetector — agentic loop, Claude decides follow-ups
    scoring.py          # ICP scoring engine (uses ProductContext for weights)
    synthesis.py        # Claude dossier generation
  models/
    __init__.py
    district.py         # DistrictProfile dataclass
    contact.py          # Contact dataclass
    signal.py           # Signal dataclass
    board_meeting.py    # BoardMeetingReport, BoardMeetingItem, VendorMention, BudgetItem
    news.py             # NewsReport, NewsProblem, LeadershipEvent, CompetitorMention, etc.
  prompts/
    system_prompt.py    # K12 domain expertise system prompt
    signal_analysis.py  # Prompt for Claude to analyze signals + decide follow-ups
    board_analysis.py   # Board meeting analysis prompts (uses ProductContext triggers)
    news_analysis.py    # News analysis prompts (problem-to-opportunity mapping)
    dossier.py          # Prompt for final intelligence brief
  output/
    __init__.py
    formatters.py       # Markdown, JSON, CSV output
  tests/
    test_nces.py
    test_signals.py
    test_agent.py
  requirements.txt
  .env.example
  README.md
```

---

## Implementation Plan (Build Order)

### Phase 1: Data Models (30 min)

**models/district.py** — DistrictProfile dataclass with all fields from ICP schema above. Key fields: district_name, nces_id, state, total_enrollment, per_pupil_expenditure, contacts (list), signals (list), intelligence_brief, icp_score, signal_strength, tavily_credits_used.

**models/contact.py** — Contact dataclass: name, title, email, phone, linkedin_url, tenure_months, is_new (bool for < 18 months), previous_org, source ("apollo" or "tavily").

**models/signal.py** — Signal dataclass: signal_type, strength (HIGH/MEDIUM/LOW), title, detail, source_url, date_detected, relevance_note.

### Phase 2: NCES Client (1 hour)

**data_sources/nces.py** — NCESClient class

Key implementation details:
- Base URL: `https://educationdata.urban.org/api/v1/`
- State filtering uses FIPS codes (AL=1, AK=2, AZ=4, CA=6, IL=17, NY=36, TX=48, VA=51)
- Use most recent year: try year=2023 first, fall back to 2022 if no results
- Handle pagination: follow `next` URL until null
- District name search is fuzzy — search then filter results locally for best match
- Three calls needed per district: directory, enrollment, finance

```python
# Pseudocode
class NCESClient:
    BASE = "https://educationdata.urban.org/api/v1"
    
    def get_district(self, name, state_fips):
        # Search directory
        url = f"{self.BASE}/school-districts/ccd/directory/2023/?district_name={name}&fips={state_fips}"
        results = self._get_paginated(url)
        district = self._best_match(results, name)
        
        if district:
            leaid = district["leaid"]
            # Pull enrollment and finance
            district["enrollment_detail"] = self._get_enrollment(leaid)
            district["finance"] = self._get_finance(leaid)
        return district
```

### Phase 3: Apollo Client (30 min)

**data_sources/apollo.py** — ApolloClient class

```python
# Pseudocode  
class ApolloClient:
    def find_contacts(self, org_name):
        response = requests.post(
            "https://api.apollo.io/v1/mixed_people/search",
            headers={"x-api-key": self.api_key},
            json={
                "q_organization_name": org_name,
                "person_titles": [K12_TITLES],
                "per_page": 25
            }
        )
        return [self._to_contact(p) for p in response.json().get("people", [])]
```

### Phase 4: Tavily K12 Wrapper (1 hour)

**data_sources/tavily_client.py** — K12TavilyClient wrapping TavilyClient

```python
class K12TavilyClient:
    def __init__(self, api_key, budget=20):
        self.client = TavilyClient(api_key=api_key)
        self.budget = budget
        self.credits_used = 0
    
    def search(self, query, **kwargs):
        cost = 2 if kwargs.get("search_depth") == "advanced" else 1
        if self.credits_used + cost > self.budget:
            return None  # Budget exhausted
        result = self.client.search(query, **kwargs)
        self.credits_used += cost
        return result
    
    def extract(self, urls):
        cost = max(1, len(urls) // 5)
        if self.credits_used + cost > self.budget:
            return None
        result = self.client.extract(urls=urls)
        self.credits_used += cost
        return result
    
    def search_district(self, district_name, query_type):
        """Pre-built K12-specific searches"""
        queries = {
            "board_meetings": f'"{district_name}" board meeting agenda 2025 2026',
            "rfps": f'"{district_name}" RFP "request for proposal" technology',
            "leadership": f'"{district_name}" superintendent appointed hired new 2024 2025',
            "funding": f'"{district_name}" ESSER "federal funding" grant technology',
            "tech_initiatives": f'"{district_name}" technology plan "digital learning" "1:1"',
            "job_postings": f'"{district_name}" hiring "instructional technology" "digital learning"',
            "sis": f'"{district_name}" "PowerSchool" OR "Infinite Campus" OR "Skyward"',
            "lms": f'"{district_name}" "Canvas" OR "Schoology" OR "Google Classroom"',
            "devices": f'"{district_name}" "Google Workspace" OR Chromebook OR "Microsoft 365" OR iPad',
        }
        return self.search(queries[query_type], max_results=5)
```

### Phase 5: Signal Detection — The Agentic Loop (2-3 hours)

**analysis/signals.py** — SignalDetector class

This is the core. The flow:

1. Run 6 initial searches (board meetings, RFPs, leadership, funding, tech initiatives, job postings)
2. Send all results to Claude with the signal analysis prompt
3. Claude returns: identified signals + recommended follow-up searches + follow-up URL extracts
4. Run the follow-up searches (prioritized by Claude, limited by budget)
5. Claude extracts final structured signals from everything

The signal analysis prompt tells Claude to act as a K12 sales intelligence analyst and return JSON with signals found, follow-up queries to run, and URLs to extract.

Key: Claude decides what to search next. This is what makes it an agent, not a pipeline.

### Phase 6: Scoring Engine (30 min)

**analysis/scoring.py**

Weighted scoring 0-100:
- Firmographic fit: 0-30 points (enrollment sweet spot, per-pupil expenditure, locale, Title I)
- Decision maker signals: 0-20 points (has tech leader, new superintendent)
- Buying signals: 0-50 points (HIGH=15, MEDIUM=7, LOW=3, capped at 50)

Anti-ICP flags that reduce score:
- Enrollment < 2000 with no tech staff: -20
- Per-pupil well below state median: -10
- No superintendent (vacant): -15
- Active litigation or state takeover: -30

### Phase 7: Claude Synthesis (1-2 hours)

**analysis/synthesis.py** + **prompts/dossier.py**

The synthesis prompt is where your 15 years of EdTech sales knowledge gets encoded. Key domain knowledge to embed in the system prompt:

- School fiscal calendars: budgets set spring (Mar-May), fiscal year July 1
- Procurement cycles: RFPs posted 3-6 months before purchase
- ESSER timelines and urgency
- Superintendent dynamics: 0-12 months = assessment, 12-24 = PEAK BUYING WINDOW
- Cooperative purchasing: Sourcewell, TIPS/TAPS, E&I, EdTech JPA bypass RFP
- Board meeting signals predict RFPs by 3-6 months
- BOCES/ESD/IU dynamics for regional purchasing
- Conference signals: ISTE (June), CoSN (March-April), FETC (January)
- Director of Technology = technical champion, Superintendent = budget authority

**Signal priority order for the prompt:**
1. Active RFP in product category (near-certainty)
2. Board agenda + remaining federal funding (very strong)
3. New superintendent with tech background + budget (strong)
4. New CTO/Tech Director (strong — bring new vendor preferences)
5. Published technology plan with timelines (medium-strong)
6. Job postings for IT roles (medium)
7. Conference attendance (medium)
8. Bond measure (medium)
9. Enrollment growth / new construction (low-medium)

**Anti-ICP signals:**
- Enrollment < 2000 AND no dedicated tech staff
- Per-pupil well below state median
- Superintendent vacancy with no replacement
- Active litigation or state takeover
- Just signed multi-year competitor contract

**Dossier output structure:**
```
# {District Name}, {State} -- Intelligence Brief
Overall Signal Strength: HIGH / MEDIUM / LOW
ICP Score: X/100
Recommended Action: PURSUE AGGRESSIVELY / PURSUE / NURTURE / MONITOR / DISQUALIFY

## District Snapshot
## Decision Makers  
## Buying Signals
## Technology Landscape
## Recommended Approach
## Timeline Assessment
## Risks and Considerations
## Sources
```

### Phase 8: Main Orchestrator (1 hour)

**agent.py** — K12ResearchAgent class

```python
class K12ResearchAgent:
    def __init__(self, tavily_api_key, apollo_api_key, anthropic_api_key, budget=20):
        self.nces = NCESClient()
        self.apollo = ApolloClient(apollo_api_key)
        self.tavily = K12TavilyClient(tavily_api_key, budget=budget)
        self.anthropic = anthropic.Anthropic(api_key=anthropic_api_key)
        self.signal_detector = SignalDetector(self.tavily, self.anthropic)

    def research_district(self, district_name, state, product_category=None, crm_data=None):
        profile = DistrictProfile(district_name=district_name, state=state)
        
        # Step 1: NCES baseline
        self._populate_nces(profile)
        
        # Step 2: Decision makers  
        self._find_contacts(profile)
        
        # Step 3: Signal detection (agentic)
        profile.signals = self.signal_detector.detect_signals(district_name, state)
        
        # Step 4: Technology profile
        self._detect_tech_profile(profile)
        
        # Step 5: Claude synthesis
        self._synthesize(profile, product_category, crm_data)
        
        return profile

    def research_batch(self, districts, max_per_batch=50):
        results = []
        for d in districts[:max_per_batch]:
            try:
                result = self.research_district(d["name"], d["state"])
                results.append(result)
                time.sleep(2)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed: {d['name']}: {e}")
        return results
```
## Cost Estimates Per District

| API | Calls | Cost |
|---|---|---|
| NCES (Urban Institute) | 3-4 calls | Free |
| Apollo | 1-2 calls | Free tier credits |
| Tavily (initial + follow-ups) | 8-15 searches + 2-3 extracts | 10-20 credits = $0.08-$0.16 |
| Claude (analysis + synthesis) | 2-3 calls | ~$0.05-$0.15 |
| **Total per district** | | **~$0.13-$0.31** |

For 100 districts: ~$13-$31. For 1,000 districts: ~$130-$310.

---

## Board Meeting Crawl Strategy

Board meetings are the single highest-value public data source for buying signals. Most districts post agendas and minutes on their websites. Every district site is structured differently.

**The workflow:**
1. Tavily search: `"{district name}" board meeting agenda 2026`
2. From results, identify the board meeting page URL
3. Tavily map: `client.map(board_page_url)` to discover agenda/minutes links
4. Tavily extract: Pull the actual agenda content
5. Send to Claude to identify technology-related items

**What to look for in board agendas:**
- "Technology" or "IT" as an agenda item
- "Strategic Plan" discussions (often include tech components)
- "Curriculum adoption" (triggers platform purchases)
- "Budget" discussions mentioning technology line items
- Vendor presentations (districts invite vendors to present before purchasing)
- "RFP" or "bid" approval items
- "Data privacy" discussions (signals EdTech evaluation awareness)
- Committee formation for technology review

**Why this matters:** A board discussion about technology in January = RFP likely in March/April. Getting there in February with a proactive outreach looks like a crystal ball, but it's just reading public documents nobody else reads systematically.

---

## Testing Strategy

### Test Districts (pick these because they have rich public data)

| District | State | FIPS | Why |
|---|---|---|---|
| Fairfax County Public Schools | VA | 51 | Large, well-funded, active tech |
| Clark County School District | NV | 32 | Massive (300K+), complex procurement |
| Mesa Public Schools | AZ | 4 | Mid-size suburban, typical use case |
| Greenville County Schools | SC | 45 | Mid-size, active EdTech adoption |
| A tiny rural district | Any | -- | Test anti-ICP and sparse data handling |

### Validation Checklist

1. NCES data pulls correctly — enrollment matches known figures
2. Apollo returns relevant contacts — gets superintendent at minimum
3. Tavily searches return useful results — not garbage
4. Signal detection finds real signals — not hallucinated
5. Credit budget respected — doesn't blow through credits
6. Claude synthesis is actionable — a real sales rep would find it useful
7. Graceful failures — if any API fails, agent produces what it can

### Smoke Test

```python
from data_sources.nces import NCESClient
client = NCESClient()
district = client.get_district("Fairfax County Public Schools", state_fips=51)
assert district is not None
print(f"Found: {district['lea_name']}, enrollment: {district['enrollment']}")
```

---

## Implementation Gotchas

### NCES: Year Lag
Data runs 1-2 years behind. Latest available in 2026 is probably school year 2023-24. Still useful for firmographics. Mention the year in the brief.

### Apollo: Coverage Varies
Large districts (50K+) have good Apollo coverage. Small/rural may return nothing. Always implement Tavily fallback — search district website staff directory, then LinkedIn.

### Tavily: Quote Matching
Wrapping district name in quotes dramatically improves relevance. Without quotes you get noise about every Springfield and every public school.

### Claude: JSON Output
When asking Claude for JSON, add "Return ONLY valid JSON, no markdown fences, no explanation." Parse with json.loads() inside try/except. Have fallback that extracts what it can if parsing fails.

### Rate Limiting
Add simple time.sleep(1) between API calls in V1. Don't optimize until you need to.

---

## Output Formats (output/formatters.py)

**Markdown** (default) — The intelligence brief as Markdown. Good for Slack, email, docs.

**JSON** — For piping into other systems:
```json
{
  "district_name": "...",
  "icp_score": 78,
  "signal_strength": "HIGH",
  "recommended_action": "PURSUE AGGRESSIVELY",
  "contacts": [],
  "signals": [],
  "intelligence_brief": "...",
  "metadata": {
    "researched_at": "...",
    "tavily_credits_used": 14,
    "data_sources": ["nces", "apollo", "tavily", "claude"]
  }
}
```

**CSV Row** — For batch research into a spreadsheet. One row per district: district_name, state, enrollment, icp_score, signal_strength, top_signal, superintendent_name, superintendent_tenure, recommended_action.

---

## Claude Code Setup Instructions

When you open Claude Code, paste this:

```
I'm building a K12 school district research agent for EdTech sales intelligence.

Read the full blueprint: k12-research-agent-blueprint.md

CRITICAL: The agent is product-context-aware. A ProductContext configuration 
(company, product, keywords, competitors, buyer titles, board meeting triggers) 
is REQUIRED and shapes every search query, every Claude prompt, and the scoring 
engine. The agent cannot run without it.

Build in this order:
1. config/product_context.py (ProductContext dataclass — all fields from blueprint)
2. config/templates.py (pre-built configs: SIS, LMS, adaptive learning, AI teaching)
3. config/settings.py (.env loading, FIPS codes, constants)
4. models/ (DistrictProfile, Contact, Signal, BoardMeetingReport, BoardMeetingItem, VendorMention, BudgetItem, NewsReport, NewsProblem, LeadershipEvent, CompetitorMention, CommunitySentiment)
5. data_sources/nces.py (Urban Institute API client)
6. data_sources/apollo.py (Apollo contact search — uses ProductContext for title priority)
7. data_sources/tavily_client.py (K12 wrapper — uses ProductContext for search keywords + budget tracking)
8. data_sources/board_meetings.py (Board Meeting Intelligence Module — full pipeline: discover page, find agendas, extract content, Claude analysis with ProductContext triggers)
9. data_sources/news_intel.py (News Intelligence Module — 18 months of coverage, 9 targeted search queries, problem-to-opportunity mapping, competitor sentiment, budget indicators)
10. analysis/signals.py (SignalDetector — agentic loop where Claude decides follow-up searches, uses ProductContext)
11. analysis/scoring.py (ICP scoring — uses ProductContext for weights + news-based scoring adjustments)
12. analysis/synthesis.py (Claude dossier — K12 domain expertise prompt + ProductContext + news narrative + board meeting findings)
13. prompts/ (all system prompts reference ProductContext fields)
14. agent.py (main orchestrator — ProductContext is required init param, pipeline: NCES -> Apollo -> Signals -> Board Meetings -> News -> Synthesis)
15. output/formatters.py (markdown, JSON, CSV)
16. Test with AI_TEACHING_TEMPLATE customized for "Kira Learning" against "Fairfax County Public Schools", state="VA"

Tech stack:
- Python 3.11+
- Dataclasses (not Django models)
- Synchronous (no async, no Celery)
- API keys from .env via python-dotenv
- Dependencies: tavily, anthropic, requests, python-dotenv
- Each module independently testable
```

---

## Environment Setup

### .env.example
```
TAVILY_API_KEY=tvly-xxxxxxxxxxxxx
APOLLO_API_KEY=xxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

### requirements.txt
```
tavily>=0.5.0
anthropic>=0.40.0
requests>=2.31.0
python-dotenv>=1.0.0
```

---

## The Product Opportunity

This agent, once proven, becomes a sellable product to EdTech companies:

**Pricing model:** Per-district research credit
- Self-serve: $5-10 per district report
- Batch: $3-5 per district for 100+
- Subscription: $500-2K/month for continuous monitoring

**Your cost:** ~$0.15-0.30 per district in API costs. **Gross margin: 95%+**

**Value prop:** Sales rep currently spends 30-60 minutes manually researching a district. This does it in 60 seconds with more data points than any human would find. For 10 reps researching 20 districts/week = 200-400 hours/month of labor replaced.

Build V1 for yourself. Use it to pitch Kira Learning or any EdTech company. The pitch IS the demo.

---

## Future Enhancements (Not V1)

1. Scheduled monitoring — weekly agent runs against target list, alert on new signals
2. Board meeting RSS — subscribe to district RSS feeds, auto-analyze new agendas
3. CRM integration — push to HubSpot/Salesforce as enriched account records
4. ICP Discovery mode — reverse-engineer what closed-won deals have in common
5. Competitive intelligence — detect competitor mentions in board meetings/RFPs
6. Multi-agent parallel execution — one agent per data source
7. Historical tracking — store profiles over time, detect changes since last check
8. Outreach drafting — auto-generate emails referencing specific signals
9. Lookalike scoring — find districts matching won-deal profiles
10. Web dashboard — Django frontend to browse reports, filter, export

---

## Board Meeting Intelligence Module

This is a dedicated component, not just a search query. Board meetings are the single most underexploited public data source in K12 EdTech sales. Every district in the country posts agendas and minutes online — nobody reads them systematically.

### Why This Is a Standalone Module

A Tavily search for "board meeting agenda" only finds what Google has indexed, which is often just the board meeting page itself, not the actual agenda content. The real intelligence is inside the agenda documents — PDFs, embedded HTML, or linked Google Docs — that contain specific line items like "Discussion: Learning Management System Evaluation Committee Report" or "Action Item: Approve technology hardware refresh contract not to exceed $2.4M."

This module goes deeper: it finds the board page, discovers the document structure, extracts actual agenda and minutes content, and uses Claude to analyze every item for technology purchasing signals.

### Architecture

```
data_sources/board_meetings.py

class BoardMeetingIntelligence:

    discover_board_page(district_name, state, district_website_url=None)
        -> Returns the URL of the district's board meeting page
    
    get_recent_agendas(board_page_url, months_back=6)
        -> Returns list of agenda URLs (PDFs, HTML pages, Google Docs links)
    
    extract_agenda_content(agenda_urls)
        -> Returns raw text content from each agenda
    
    analyze_agendas(agenda_contents, product_category=None)
        -> Claude analyzes each agenda, returns structured BoardMeetingSignals
    
    full_scan(district_name, state, product_category=None)
        -> Runs the full pipeline, returns BoardMeetingReport
```

### Step 1: Discover the Board Meeting Page

Districts organize their board pages inconsistently. Common patterns:

- `district.org/board` or `district.org/school-board`
- `district.org/board-of-education`
- `district.org/boarddocs` (many use BoardDocs platform)
- `district.org/meetings` or `district.org/agendas`
- Hosted on third-party platforms: BoardDocs, BoardBook, Diligent (formerly Simbli)

**Discovery strategy:**

```python
def discover_board_page(self, district_name, state, district_website_url=None):
    """
    Find the board meeting / agenda page for a district.
    Returns: {"board_page_url": "...", "platform": "boarddocs|custom|unknown"}
    """
    
    # Strategy 1: If we have the district website, use Tavily map to find board page
    if district_website_url:
        sitemap = self.tavily.client.map(
            url=district_website_url,
            instructions="Find the school board, board of education, or board meetings page"
        )
        # Parse sitemap results for board-related URLs
    
    # Strategy 2: Search for the board page directly
    results = self.tavily.search(
        query=f'"{district_name}" {state} board meeting agenda minutes site:.org OR site:.us OR site:.k12',
        search_depth="advanced",
        max_results=5,
    )
    # Look for URLs containing: /board, /agendas, /meetings, boarddocs.com
    
    # Strategy 3: Check common board management platforms
    platform_searches = [
        f'site:boarddocs.com "{district_name}"',
        f'site:go.boarddocs.com "{district_name}"',
        f'site:meetings.boardbook.org "{district_name}"',
        f'site:simbli.eboardsolutions.com "{district_name}"',
    ]
    # Try each until one returns results
    
    # Detect which platform they use (affects extraction strategy)
    # BoardDocs: structured API-like access, agenda items are database records
    # Custom HTML: need to parse links to PDFs or embedded content
    # Google Docs: linked agendas in Google Docs format
```

### Step 2: Find Recent Agendas

Once we have the board page URL, discover individual meeting agendas going back 6 months.

```python
def get_recent_agendas(self, board_page_url, months_back=6):
    """
    From the board meeting page, find links to individual meeting agendas.
    Returns: [
        {"date": "2026-01-15", "title": "Regular Board Meeting", "agenda_url": "...", "minutes_url": "..."},
        {"date": "2025-12-18", "title": "Regular Board Meeting", "agenda_url": "...", "minutes_url": "..."},
        ...
    ]
    """
    
    # Use Tavily extract to pull the board page content
    page_content = self.tavily.client.extract(urls=[board_page_url])
    
    # Send to Claude to parse out meeting dates and agenda/minutes links
    # Claude is better than regex here because every district formats differently
    
    parsed = self._claude_parse_board_page(page_content, months_back)
    
    # For BoardDocs specifically: the agenda items are loaded dynamically via AJAX
    # May need to use Tavily crawl with instructions to navigate into individual meetings
    
    return parsed
```

**Claude prompt for parsing board pages:**

```python
BOARD_PAGE_PARSE_PROMPT = """You are parsing a school district's board meeting webpage to find 
links to meeting agendas and minutes.

Here is the page content:
{page_content}

Extract all board meetings from the last {months_back} months. For each meeting, find:
- date (YYYY-MM-DD format)
- meeting_title (e.g., "Regular Board Meeting", "Special Session")
- agenda_url (direct link to the agenda document — PDF, HTML, or Google Doc)
- minutes_url (direct link to the minutes if available, null if not)

Return as JSON array:
[
  {"date": "2026-01-15", "title": "Regular Board Meeting", "agenda_url": "...", "minutes_url": "..."},
  ...
]

If URLs are relative paths, prepend the base domain. If you cannot find direct document links 
but can see meeting dates, return what you have with null URLs. Return ONLY valid JSON."""
```

### Step 3: Extract Agenda Content

Pull the actual text from agenda documents.

```python
def extract_agenda_content(self, agenda_urls):
    """
    Extract text content from agenda documents.
    Handles: HTML pages, PDFs (via Tavily's extraction), Google Docs links.
    Returns: [{"url": "...", "date": "...", "content": "..."}]
    """
    
    # Filter to valid URLs, batch up to 20 per Tavily extract call
    valid_urls = [u for u in agenda_urls if u]
    
    # Tavily extract handles HTML and many PDF formats
    results = self.tavily.client.extract(urls=valid_urls[:20])
    
    extracted = []
    for result in results.get("results", []):
        extracted.append({
            "url": result["url"],
            "content": result["raw_content"],
        })
    
    return extracted
```

**Tavily credit cost for this step:** 1 credit per 5 URLs at basic depth. So extracting 6 months of agendas (roughly 12-24 meetings) = 3-5 credits.

### Step 4: Claude Analyzes Agenda Content

This is the intelligence extraction step. Claude reads every agenda item and identifies technology-related purchasing signals.

```python
def analyze_agendas(self, agenda_contents, product_category=None):
    """
    Claude analyzes extracted agenda content for technology purchasing signals.
    Returns: BoardMeetingReport with structured findings.
    """
    
    response = self.anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=BOARD_MEETING_ANALYSIS_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": BOARD_MEETING_ANALYSIS_USER_PROMPT.format(
                agenda_contents=json.dumps(agenda_contents, indent=2),
                product_category=product_category or "any EdTech product",
            )
        }]
    )
    
    return self._parse_analysis(response.content[0].text)
```

**The analysis system prompt (domain expertise):**

```python
BOARD_MEETING_ANALYSIS_SYSTEM_PROMPT = """You are a K12 EdTech sales intelligence analyst 
who specializes in reading school board agendas and minutes to identify technology purchasing signals.

You understand that board-level discussion is the EARLIEST public indicator of a purchasing decision.
The typical timeline is:

  Board discussion/committee formation (you are here) 
    -> 1-3 months -> 
  Formal needs assessment / vendor demos
    -> 1-3 months ->
  RFP drafted and posted
    -> 1-2 months ->
  RFP response deadline
    -> 1-2 months ->
  Evaluation and selection
    -> 1 month ->
  Board approval of contract
    -> Purchase

So identifying a board discussion gives 4-10 months of lead time before a purchase decision.

You know what matters in board agendas:

DIRECT TECHNOLOGY SIGNALS (highest value):
- Technology committee reports or formation
- LMS, SIS, or platform evaluation discussions
- Technology hardware refresh or device purchases
- Data privacy policy reviews (signals new vendor evaluation)
- "Technology plan" presentations or updates
- Specific vendor names mentioned in any context
- Line items for technology budget allocation
- RFP approvals for technology categories
- Curriculum platform adoption discussions
- Pilot program reports (district testing a product before full adoption)
- "Digital learning" or "digital transformation" initiatives
- Network infrastructure or E-Rate discussions
- Cybersecurity discussions (often trigger tool purchases)
- AI policy discussions (signals awareness and potential adoption)

INDIRECT SIGNALS (still valuable):
- Strategic plan presentations mentioning technology goals
- Superintendent presenting vision/priorities (new supers often include tech)
- Budget workshops showing technology line item changes year-over-year
- Enrollment growth requiring technology capacity expansion
- New school openings (need full technology build-out)
- Equity or access discussions (often lead to device/connectivity purchases)
- Assessment or testing platform discussions
- Special education technology needs
- English learner program technology needs
- Staff professional development on technology tools

TIMING CLUES:
- "First reading" = early stage, 2-4 months from action
- "Second reading" = imminent, 1-2 months from action
- "Action item" = vote happening at this meeting or next
- "Information only" = early stage awareness, 3-6+ months from action
- "Committee report" = active evaluation in progress, 2-4 months from purchase
- "Consent agenda" = routine approval, contract likely already negotiated
- "Public hearing" = required step before large purchases, 1-2 months from action

WHAT TO IGNORE:
- Routine technology maintenance reports with no purchasing implication
- HR items about technology staff (unless it's a new tech director position)
- Student achievement data (unless tied to platform discussion)
- Facilities items (unless about network infrastructure)
"""

BOARD_MEETING_ANALYSIS_USER_PROMPT = """Analyze these school board meeting agendas and minutes 
for technology purchasing signals relevant to {product_category}.

AGENDA CONTENTS:
{agenda_contents}

For each meeting, identify EVERY technology-related agenda item and classify it.

Return as JSON:
{{
  "meetings_analyzed": 12,
  "technology_items_found": [
    {{
      "meeting_date": "2026-01-15",
      "agenda_item": "Technology Committee Report: LMS Evaluation Update",
      "category": "platform_evaluation",
      "signal_strength": "HIGH",
      "stage": "active_evaluation",
      "estimated_purchase_timeline": "3-6 months",
      "detail": "Committee reviewed demos from Canvas and Schoology. Recommendation expected at February meeting.",
      "relevance_to_product": "Direct match - district is actively evaluating LMS platforms",
      "recommended_action": "Contact Director of Technology before February board meeting with demo request"
    }},
    ...
  ],
  "budget_items": [
    {{
      "meeting_date": "2025-11-20",
      "description": "Technology budget line item: $1.2M allocated for digital curriculum FY2026",
      "amount": 1200000,
      "fiscal_year": "2025-2026"
    }},
    ...
  ],
  "vendor_mentions": [
    {{
      "meeting_date": "2026-01-15",
      "vendor_name": "Canvas by Instructure",
      "context": "Vendor demo presented to Technology Committee",
      "implication": "Active competitor in evaluation process"
    }},
    ...
  ],
  "leadership_signals": [
    {{
      "meeting_date": "2025-09-18",
      "description": "New superintendent Dr. Martinez presented 100-day plan with emphasis on digital learning transformation",
      "implication": "New leadership prioritizing technology - peak buying window opening in 6-12 months"
    }},
    ...
  ],
  "timeline_summary": "District is in active LMS evaluation with committee formed in October 2025. Two vendors demonstrated in January 2026. Recommendation expected February. Board vote likely March-April. Budget allocated. This is a HIGH urgency opportunity with a 2-4 month window.",
  "overall_signal_strength": "HIGH"
}}

Return ONLY valid JSON."""
```

### Step 5: Full Scan Method

```python
def full_scan(self, district_name, state, product_category=None, district_website_url=None):
    """
    Run the complete board meeting intelligence pipeline.
    Returns: BoardMeetingReport
    
    Tavily credit budget for this module: ~8-12 credits
      - 1-2 credits: discover board page
      - 1-2 credits: map site structure  
      - 1 credit: extract board page
      - 3-5 credits: extract 12-24 agendas
      - Claude calls: ~$0.05-0.10
    """
    
    # Step 1: Find the board page
    board_info = self.discover_board_page(district_name, state, district_website_url)
    if not board_info:
        return BoardMeetingReport(status="board_page_not_found")
    
    # Step 2: Get recent agenda links
    agendas = self.get_recent_agendas(board_info["board_page_url"], months_back=6)
    if not agendas:
        return BoardMeetingReport(status="no_agendas_found", board_page_url=board_info["board_page_url"])
    
    # Step 3: Extract agenda content
    agenda_urls = [a["agenda_url"] for a in agendas if a.get("agenda_url")]
    contents = self.extract_agenda_content(agenda_urls)
    if not contents:
        return BoardMeetingReport(status="extraction_failed", agendas_found=len(agendas))
    
    # Step 4: Claude analysis
    analysis = self.analyze_agendas(contents, product_category)
    
    # Package results
    report = BoardMeetingReport(
        status="complete",
        board_page_url=board_info["board_page_url"],
        platform=board_info.get("platform", "unknown"),
        meetings_analyzed=len(contents),
        technology_items=analysis.get("technology_items_found", []),
        budget_items=analysis.get("budget_items", []),
        vendor_mentions=analysis.get("vendor_mentions", []),
        leadership_signals=analysis.get("leadership_signals", []),
        timeline_summary=analysis.get("timeline_summary", ""),
        overall_signal_strength=analysis.get("overall_signal_strength", "UNKNOWN"),
    )
    
    return report
```

### Data Model

```python
# models/board_meeting.py

@dataclass
class BoardMeetingItem:
    meeting_date: str
    agenda_item: str
    category: str           # platform_evaluation, hardware_refresh, budget, policy, etc.
    signal_strength: str    # HIGH, MEDIUM, LOW
    stage: str              # information_only, committee_review, active_evaluation, action_item, approved
    estimated_purchase_timeline: str
    detail: str
    relevance_to_product: str
    recommended_action: str

@dataclass
class VendorMention:
    meeting_date: str
    vendor_name: str
    context: str
    implication: str         # "active competitor", "incumbent", "being replaced"

@dataclass
class BudgetItem:
    meeting_date: str
    description: str
    amount: Optional[float] = None
    fiscal_year: str = ""

@dataclass
class BoardMeetingReport:
    status: str = ""                        # complete, board_page_not_found, no_agendas_found, extraction_failed
    board_page_url: str = ""
    platform: str = ""                      # boarddocs, custom, simbli, unknown
    meetings_analyzed: int = 0
    technology_items: list = field(default_factory=list)    # List of BoardMeetingItem
    budget_items: list = field(default_factory=list)        # List of BudgetItem
    vendor_mentions: list = field(default_factory=list)     # List of VendorMention
    leadership_signals: list = field(default_factory=list)
    timeline_summary: str = ""
    overall_signal_strength: str = ""
    tavily_credits_used: int = 0
```

### Integration with Main Agent

The board meeting module plugs into the main agent between Step 3 (signal detection) and Step 5 (synthesis). Add it to the orchestrator:

```python
# In agent.py, inside research_district():

    # Step 3: Signal detection (existing)
    profile.signals = self.signal_detector.detect_signals(district_name, state)
    
    # Step 3b: Board meeting deep scan (NEW)
    logger.info(f"Scanning board meetings...")
    board_intel = BoardMeetingIntelligence(self.tavily, self.anthropic)
    board_report = board_intel.full_scan(
        district_name, state, 
        product_category=product_category,
        district_website_url=self._get_district_website(profile)
    )
    profile.board_meeting_report = board_report
    
    # Convert board meeting findings into Signal objects for the main signals list
    if board_report.status == "complete":
        for item in board_report.technology_items:
            profile.signals.append(Signal(
                signal_type="board_agenda_tech",
                strength=item["signal_strength"],
                title=f"Board Agenda: {item['agenda_item']}",
                detail=item["detail"],
                source_url=board_report.board_page_url,
                date_detected=item["meeting_date"],
                relevance_note=item["recommended_action"],
            ))
        for vendor in board_report.vendor_mentions:
            profile.signals.append(Signal(
                signal_type="competitor_mention",
                strength="HIGH",
                title=f"Vendor Mentioned: {vendor['vendor_name']}",
                detail=vendor["context"],
                source_url=board_report.board_page_url,
                date_detected=vendor["meeting_date"],
                relevance_note=vendor["implication"],
            ))
```

### Updated File Structure

```
k12_research_agent/
  ...existing files...
  data_sources/
    board_meetings.py     # NEW — BoardMeetingIntelligence class
  models/
    board_meeting.py      # NEW — BoardMeetingReport, BoardMeetingItem, etc.
  prompts/
    board_analysis.py     # NEW — Board meeting analysis prompts
```

### Updated Cost Estimate Per District (with board meeting scan)

| API | Calls | Cost |
|---|---|---|
| NCES (Urban Institute) | 3-4 calls | Free |
| Apollo | 1-2 calls | Free tier credits |
| Tavily — signal detection | 8-15 searches | 8-15 credits |
| Tavily — board meeting scan | 3-7 searches/extracts | 5-10 credits |
| Claude — signal analysis | 2-3 calls | ~$0.05-$0.10 |
| Claude — board meeting analysis | 1-2 calls | ~$0.03-$0.08 |
| **Total per district** | | **~$0.20-$0.50** |

Budget increase is modest (extra ~$0.10-0.20) but the intelligence value of actual board meeting content is disproportionately high. This is where you find things like "Committee recommended Canvas over Schoology at the January meeting" that no amount of Google searching would surface.

### Standalone Monitoring Mode (Future Enhancement)

The board meeting module is designed to also run independently as a monitoring service:

```python
# Standalone usage — run weekly against a target list
monitor = BoardMeetingIntelligence(tavily_client, anthropic_client)

target_districts = [
    {"name": "Fairfax County Public Schools", "state": "VA", "board_url": "https://..."},
    {"name": "Mesa Public Schools", "state": "AZ", "board_url": "https://..."},
    # ... 50 districts
]

for district in target_districts:
    report = monitor.full_scan(
        district["name"], 
        district["state"],
        product_category="Student Information System",
        district_website_url=district.get("board_url"),
    )
    if report.overall_signal_strength == "HIGH":
        send_alert(district, report)  # Slack, email, whatever
```

This becomes the subscription product: "$500/month and we monitor 100 districts' board meetings for you, alerting you the moment technology discussions appear."

### BoardDocs Special Handling

Many districts (especially large ones) use BoardDocs (go.boarddocs.com), which is a structured platform. BoardDocs pages load content dynamically via JavaScript/AJAX, which means simple extraction may miss the actual agenda items.

**Workaround strategy:**
1. Detect if the district uses BoardDocs (URL contains boarddocs.com)
2. If yes, use Tavily crawl with instructions: "Navigate to each board meeting and extract the full agenda with all items listed"
3. BoardDocs also sometimes has a public API or RSS — check for this
4. Fallback: search Google for cached versions of the agendas: `site:go.boarddocs.com "{district_name}" agenda`

Add a `_handle_boarddocs()` method that implements this alternative extraction path.

### What This Catches That Normal Research Misses

Real examples of board meeting intelligence that would give a sales rep a massive edge:

- "Action Item: Approve RFP for Student Information System replacement, estimated value $800K" — the district is buying your product category and you know the budget
- "Information Item: Technology Committee formed to evaluate digital math curriculum options" — you're 4-6 months ahead of the RFP
- "Superintendent Report: 100-day plan includes transitioning all schools to 1:1 devices by fall 2027" — new leader committed to tech spending
- "Consent Agenda: Approve renewal of contract with [Competitor] for 1 year (reduced from 3-year)" — competitor is on thin ice, short renewal signals dissatisfaction
- "Budget Workshop: Technology line item increased from $1.2M to $1.8M for FY2027" — 50% budget increase, money is earmarked
- "Public Comment: Three parents expressed concern about [Competitor Platform] data privacy practices" — vulnerability to exploit in outreach
- "Board Member Question: Can we see a comparison of our per-pupil technology spending vs peer districts?" — board is scrutinizing tech investment, either up or down

---

## Product Context Configuration

This is not optional. This is the FIRST thing configured before the agent runs. Without it, the agent is doing generic research — with it, every search, every analysis, and every recommendation is tuned to what you're actually selling.

### Why This Changes Everything

Consider two EdTech companies using this agent to research the same district:

**Company A sells a Student Information System (SIS):**
- Board agenda item "Discussion: PowerSchool contract renewal" = 🔥 HIGHEST PRIORITY SIGNAL
- Board agenda item "STEM curriculum review" = irrelevant, ignore
- Decision maker priority: Director of Technology first, then Business Manager (procurement)
- Competitor detection: PowerSchool, Infinite Campus, Skyward, Tyler SIS, Aeries
- Tech profile that matters: What SIS do they currently run? When does the contract expire?
- RFP keywords: "student information", "SIS", "student data", "enrollment management"
- Scoring boost: District currently on a legacy SIS = higher score

**Company B sells an AI tutoring platform:**
- Board agenda item "PowerSchool contract renewal" = irrelevant
- Board agenda item "STEM curriculum review" = 🔥 HIGHEST PRIORITY SIGNAL
- Decision maker priority: Director of Curriculum first, then Superintendent (vision)
- Competitor detection: Khan Academy, IXL, DreamBox, Zearn, Carnegie Learning
- Tech profile that matters: What LMS do they use? (integration dependency) What curriculum are they on?
- RFP keywords: "tutoring", "intervention", "adaptive learning", "math curriculum", "supplemental"
- Scoring boost: Low math scores + ESSER funding remaining = higher score

Same district, same public data, completely different intelligence output. The product context is what makes the difference.

### The ProductContext Configuration Object

```python
# config/product_context.py

@dataclass
class ProductContext:
    """
    Configure once per EdTech company or product line.
    This shapes every search, analysis, and score the agent produces.
    """
    
    # === PRODUCT IDENTITY ===
    company_name: str = ""
    product_name: str = ""
    product_category: str = ""  # Primary category (see VALID_CATEGORIES below)
    product_subcategories: list = field(default_factory=list)  # Additional categories
    one_liner: str = ""  # What the product does in one sentence
    # Example: "AI-powered teaching platform with real-time tutoring, 
    #           grading, and K-12 CS curriculum"
    
    # === SEARCH KEYWORDS ===
    # These get injected into Tavily searches and Claude analysis prompts
    primary_keywords: list = field(default_factory=list)
    # The core terms that indicate a district is buying what you sell
    # Example for SIS: ["student information system", "SIS", "student data", 
    #                    "enrollment management", "student records"]
    # Example for AI tutor: ["tutoring", "adaptive learning", "intervention", 
    #                         "personalized learning", "AI tutor"]
    
    secondary_keywords: list = field(default_factory=list)
    # Related terms that suggest adjacent interest
    # Example for SIS: ["data integration", "interoperability", "Ed-Fi", 
    #                    "student privacy", "FERPA"]
    # Example for AI tutor: ["achievement gap", "math scores", "reading levels",
    #                         "differentiated instruction", "MTSS", "RTI"]
    
    # === COMPETITORS ===
    direct_competitors: list = field(default_factory=list)
    # Products that do exactly what you do
    # Example for SIS: ["PowerSchool", "Infinite Campus", "Skyward", 
    #                    "Tyler SIS", "Aeries", "Synergy"]
    
    adjacent_competitors: list = field(default_factory=list)
    # Products in a related space that sometimes compete
    # Example for SIS: ["Clever", "ClassLink"] (identity/rostering overlap)
    
    # These get used in:
    # - Board meeting analysis: flag any mention of these vendors
    # - Tech profile detection: identify incumbent/competitor installed
    # - Dossier generation: competitive positioning recommendations
    
    # === DECISION MAKER PRIORITY ===
    primary_buyer_titles: list = field(default_factory=list)
    # Who actually signs the purchase order or owns the decision
    # Example for SIS: ["Chief Technology Officer", "Director of Technology",
    #                    "Director of Information Systems"]
    # Example for AI tutor: ["Chief Academic Officer", "Director of Curriculum",
    #                         "Director of Instruction", "Assistant Superintendent of Instruction"]
    
    secondary_buyer_titles: list = field(default_factory=list)
    # Who influences the decision or champions internally
    # Example for SIS: ["Business Manager", "Director of Procurement",
    #                    "Data Manager", "Registrar"]
    # Example for AI tutor: ["Math Coordinator", "Instructional Coach",
    #                         "Director of STEM", "Intervention Specialist"]
    
    executive_sponsor_titles: list = field(default_factory=list)
    # Who approves budget — almost always the same across products
    # Default: ["Superintendent", "Deputy Superintendent", 
    #           "Assistant Superintendent of Business"]
    
    # === BOARD MEETING TRIGGERS ===
    board_agenda_triggers: list = field(default_factory=list)
    # Specific phrases in board agendas that indicate your product category is in play
    # Example for SIS: ["student information", "SIS", "PowerSchool", "student records",
    #                    "data system", "enrollment system", "registration system"]
    # Example for AI tutor: ["tutoring program", "intervention", "math curriculum",
    #                         "adaptive learning", "personalized", "achievement gap",
    #                         "supplemental curriculum", "MTSS", "RTI"]
    
    board_agenda_anti_triggers: list = field(default_factory=list)
    # Agenda items that look relevant but aren't for your product
    # Example for SIS: ["student information privacy policy" (policy, not purchasing)]
    # Example for AI tutor: ["tutoring center hours" (facility, not software)]
    
    # === RFP KEYWORDS ===
    rfp_keywords: list = field(default_factory=list)
    # Terms that indicate an RFP is for your product category
    # Example for SIS: ["student information system", "SIS replacement",
    #                    "student data management", "enrollment management system"]
    # Example for AI tutor: ["adaptive learning platform", "tutoring solution",
    #                         "math intervention software", "supplemental curriculum"]
    
    # === FUNDING RELEVANCE ===
    relevant_funding_sources: list = field(default_factory=list)
    # Which federal/state funding streams typically pay for your product
    # Example for SIS: ["E-Rate" (if SIS has network component), "state technology grants"]
    # Example for AI tutor: ["Title I", "Title III" (ELL), "ESSER", 
    #                         "state innovation grants", "IDEA" (SPED)]
    
    # === ICP SCORING ADJUSTMENTS ===
    ideal_enrollment_min: int = 2000
    ideal_enrollment_max: int = 100000
    # Override defaults based on your product's sweet spot
    # Enterprise SIS: 10000-500000
    # Niche tutoring app: 1000-20000
    
    minimum_per_pupil_expenditure: Optional[float] = None
    # Districts below this likely can't afford your product
    # Premium SIS: $12000+
    # Free/freemium tool: None (no minimum)
    
    title_i_preference: Optional[str] = None
    # "required" = only pursue Title I districts (if product is funded by Title I)
    # "preferred" = boost score for Title I (more federal funding available)
    # "neutral" = doesn't matter
    # None = default to neutral
    
    locale_preferences: list = field(default_factory=list)
    # Boost score for these locale types
    # Example: ["City-Large", "Suburb-Large", "Suburb-Midsize"]
    # Empty = no preference
    
    # === INTEGRATION DEPENDENCIES ===
    required_integrations: list = field(default_factory=list)
    # Your product requires these to be installed
    # Example: ["Google Workspace"] (if your product only works with Google)
    # Example: ["Canvas", "Schoology"] (if you're an LTI integration)
    
    incompatible_systems: list = field(default_factory=list)
    # Your product doesn't work with these
    # Example: ["Microsoft 365"] (if Google-only)
    
    # These get used in tech profile detection:
    # If required_integrations match = scoring boost
    # If incompatible_systems match = scoring penalty or disqualify
    
    # === SALES CYCLE CONTEXT ===
    typical_deal_size: str = ""
    # "under_10k", "10k_50k", "50k_200k", "200k_plus"
    # Affects which procurement path applies:
    #   under_10k: often no RFP needed, principal can approve
    #   10k_50k: department-level approval, may need quotes
    #   50k_200k: formal RFP likely, board awareness
    #   200k_plus: board approval required, multi-month process
    
    typical_sales_cycle_months: int = 6
    # How long from first contact to close
    # Affects timeline recommendations in dossier
    
    implementation_requirements: list = field(default_factory=list)
    # What the district needs to support your product
    # Example: ["1:1 devices", "minimum 100mbps internet", "dedicated IT staff"]
    # Used to flag districts that lack prerequisites
```

### Valid Product Categories

```python
VALID_CATEGORIES = [
    # Core Systems
    "Student Information System (SIS)",
    "Learning Management System (LMS)",
    "Enterprise Resource Planning (ERP)",
    "Human Capital Management (HCM)",
    
    # Instructional
    "Core Curriculum — Math",
    "Core Curriculum — ELA",
    "Core Curriculum — Science",
    "Core Curriculum — Social Studies",
    "Supplemental Curriculum",
    "Adaptive Learning / Tutoring",
    "Assessment Platform",
    "Special Education Management",
    "English Learner Tools",
    "Computer Science / Coding",
    "Career and Technical Education (CTE)",
    "Social-Emotional Learning (SEL)",
    "College and Career Readiness",
    
    # Infrastructure
    "Network / WiFi Infrastructure",
    "Devices (Chromebooks, iPads, laptops)",
    "Device Management (MDM)",
    "Cybersecurity",
    "Identity and Access Management",
    "Classroom AV / Interactive Displays",
    
    # Operations
    "Communication Platform (parent/community)",
    "Transportation Management",
    "Facilities Management",
    "Food Service Management",
    "Visitor Management / Safety",
    
    # Data and Analytics
    "Data Warehouse / Analytics",
    "Data Integration / Interoperability",
    "Reporting and Compliance",
    
    # Professional Development
    "Teacher PD Platform",
    "Classroom Observation / Coaching",
    
    # AI-Specific (emerging)
    "AI Teaching Assistant",
    "AI Tutoring",
    "AI Content Generation",
    "AI Administrative Tools",
]
```

### Pre-Built Configurations (Templates)

To make it easy to get started, include templates for common product categories:

```python
# config/templates.py

SIS_TEMPLATE = ProductContext(
    product_category="Student Information System (SIS)",
    primary_keywords=[
        "student information system", "SIS", "student data management",
        "enrollment management", "student records system", "grading system",
        "attendance tracking", "report cards", "transcripts",
    ],
    secondary_keywords=[
        "data integration", "interoperability", "Ed-Fi", "student privacy",
        "FERPA", "parent portal", "gradebook", "scheduling",
    ],
    direct_competitors=[
        "PowerSchool", "Infinite Campus", "Skyward", "Tyler SIS",
        "Aeries", "Synergy", "Follett Aspen",
    ],
    primary_buyer_titles=[
        "Chief Technology Officer", "Director of Technology",
        "Director of Information Systems", "Director of IT",
    ],
    secondary_buyer_titles=[
        "Business Manager", "Director of Procurement", "Data Manager",
        "Registrar", "Director of Student Services",
    ],
    board_agenda_triggers=[
        "student information", "SIS", "PowerSchool", "Infinite Campus",
        "student records", "data system", "enrollment system",
        "registration system", "grading system", "student data",
    ],
    rfp_keywords=[
        "student information system", "SIS replacement", "SIS migration",
        "student data management", "enrollment management system",
    ],
    relevant_funding_sources=["state technology grants", "E-Rate"],
    ideal_enrollment_min=5000,
    ideal_enrollment_max=200000,
    typical_deal_size="200k_plus",
    typical_sales_cycle_months=12,
)

ADAPTIVE_LEARNING_TEMPLATE = ProductContext(
    product_category="Adaptive Learning / Tutoring",
    primary_keywords=[
        "adaptive learning", "tutoring software", "personalized learning",
        "intervention", "math intervention", "reading intervention",
        "intelligent tutoring", "AI tutor",
    ],
    secondary_keywords=[
        "achievement gap", "test scores", "MTSS", "RTI", "response to intervention",
        "differentiated instruction", "remediation", "acceleration",
        "formative assessment", "learning loss",
    ],
    direct_competitors=[
        "DreamBox", "IXL", "Khan Academy", "Zearn", "Carnegie Learning",
        "i-Ready", "ALEKS", "Exact Path", "Lexia",
    ],
    primary_buyer_titles=[
        "Chief Academic Officer", "Director of Curriculum",
        "Director of Instruction", "Assistant Superintendent of Instruction",
        "Director of Teaching and Learning",
    ],
    secondary_buyer_titles=[
        "Math Coordinator", "Instructional Coach", "Director of STEM",
        "Intervention Specialist", "Director of Assessment",
    ],
    board_agenda_triggers=[
        "tutoring", "intervention", "adaptive", "personalized learning",
        "math curriculum", "reading curriculum", "achievement gap",
        "learning loss", "supplemental", "MTSS", "RTI",
    ],
    rfp_keywords=[
        "adaptive learning", "tutoring solution", "intervention software",
        "supplemental curriculum", "personalized learning platform",
    ],
    relevant_funding_sources=["Title I", "Title III", "ESSER", "IDEA", "state innovation grants"],
    ideal_enrollment_min=2000,
    ideal_enrollment_max=100000,
    minimum_per_pupil_expenditure=10000,
    title_i_preference="preferred",
    typical_deal_size="50k_200k",
    typical_sales_cycle_months=6,
)

LMS_TEMPLATE = ProductContext(
    product_category="Learning Management System (LMS)",
    primary_keywords=[
        "learning management system", "LMS", "course management",
        "digital classroom", "online learning platform",
    ],
    secondary_keywords=[
        "blended learning", "hybrid learning", "remote learning",
        "digital curriculum delivery", "LTI integration", "SCORM",
    ],
    direct_competitors=[
        "Canvas", "Schoology", "Google Classroom", "Blackboard",
        "Brightspace D2L", "Moodle", "itslearning",
    ],
    primary_buyer_titles=[
        "Chief Technology Officer", "Director of Technology",
        "Director of Digital Learning", "Director of Instructional Technology",
    ],
    secondary_buyer_titles=[
        "Director of Curriculum", "Instructional Technology Specialist",
        "Director of Professional Development",
    ],
    board_agenda_triggers=[
        "learning management", "LMS", "Canvas", "Schoology",
        "digital learning platform", "online learning", "course management",
    ],
    rfp_keywords=[
        "learning management system", "LMS", "digital learning platform",
        "course management system",
    ],
    relevant_funding_sources=["ESSER", "state technology grants", "E-Rate"],
    ideal_enrollment_min=3000,
    ideal_enrollment_max=150000,
    typical_deal_size="50k_200k",
    typical_sales_cycle_months=9,
)

AI_TEACHING_TEMPLATE = ProductContext(
    product_category="AI Teaching Assistant",
    one_liner="AI-powered teaching platform with real-time tutoring, grading, and curriculum tools",
    primary_keywords=[
        "AI teaching", "AI tutor", "AI grading", "AI classroom",
        "artificial intelligence education", "generative AI school",
        "AI curriculum", "AI assistant teacher",
    ],
    secondary_keywords=[
        "computer science curriculum", "coding education", "ChatGPT school",
        "AI policy", "AI literacy", "responsible AI", "machine learning education",
        "automated grading", "intelligent tutoring system",
    ],
    direct_competitors=[
        "Khanmigo", "MagicSchool", "Diffit", "Curipod", "SchoolAI",
        "Brisk Teaching", "Cognii",
    ],
    adjacent_competitors=[
        "Khan Academy", "IXL", "DreamBox", "Code.org",
    ],
    primary_buyer_titles=[
        "Chief Academic Officer", "Director of Curriculum",
        "Director of Instructional Technology", "Director of Innovation",
        "Director of Digital Learning",
    ],
    secondary_buyer_titles=[
        "Director of STEM", "Computer Science Coordinator",
        "Instructional Coach", "Director of Assessment",
    ],
    board_agenda_triggers=[
        "artificial intelligence", "AI policy", "AI in education",
        "generative AI", "ChatGPT", "AI curriculum", "computer science",
        "coding", "AI tutoring", "AI grading", "machine learning",
        "AI literacy", "responsible AI use",
    ],
    rfp_keywords=[
        "AI teaching platform", "AI tutoring", "AI grading",
        "computer science curriculum", "AI education tools",
    ],
    relevant_funding_sources=[
        "Title I", "Title II" , "Title IV-A", "ESSER",
        "state STEM grants", "state CS education funding",
        "NSF grants",
    ],
    ideal_enrollment_min=2000,
    ideal_enrollment_max=150000,
    title_i_preference="preferred",
    typical_deal_size="10k_50k",
    typical_sales_cycle_months=4,
)

TEMPLATES = {
    "sis": SIS_TEMPLATE,
    "lms": LMS_TEMPLATE,
    "adaptive_learning": ADAPTIVE_LEARNING_TEMPLATE,
    "ai_teaching": AI_TEACHING_TEMPLATE,
}
```

### How ProductContext Threads Through the Agent

Every module reads from ProductContext. Here is exactly where it gets used:

**1. Apollo Contact Search (data_sources/apollo.py)**
```python
# Instead of searching all K12 titles, prioritize the product-relevant ones
def find_contacts(self, org_name, product_context: ProductContext):
    titles = (
        product_context.primary_buyer_titles +
        product_context.secondary_buyer_titles +
        product_context.executive_sponsor_titles
    )
    # Search Apollo with these titles first
    # Tag each contact with their priority level: "primary_buyer", "secondary_buyer", "executive"
```

**2. Tavily Signal Searches (data_sources/tavily_client.py)**
```python
# Inject product keywords into signal detection queries
def build_signal_queries(self, district_name, product_context: ProductContext):
    keywords_or = " OR ".join(f'"{kw}"' for kw in product_context.primary_keywords[:5])
    competitors_or = " OR ".join(f'"{c}"' for c in product_context.direct_competitors[:5])
    
    return [
        # Product-specific RFP search
        {
            "query": f'"{district_name}" RFP {keywords_or}',
            "search_depth": "advanced",
        },
        # Competitor detection
        {
            "query": f'"{district_name}" {competitors_or}',
            "search_depth": "basic",
        },
        # Product-relevant board discussions
        {
            "query": f'"{district_name}" board agenda {" OR ".join(product_context.board_agenda_triggers[:5])}',
            "search_depth": "advanced",
        },
        # Relevant funding
        {
            "query": f'"{district_name}" {" OR ".join(product_context.relevant_funding_sources[:3])}',
            "search_depth": "basic",
        },
        # ... plus the generic searches (leadership, general tech) that apply to all products
    ]
```

**3. Board Meeting Analysis (data_sources/board_meetings.py)**
```python
# The board meeting prompt changes based on product context
BOARD_MEETING_ANALYSIS_USER_PROMPT = """Analyze these board agendas for signals relevant to:

PRODUCT: {product_context.product_name}
CATEGORY: {product_context.product_category}
DESCRIPTION: {product_context.one_liner}

TRIGGER TERMS (flag these if you see them):
{product_context.board_agenda_triggers}

COMPETITORS (flag any mention):
{product_context.direct_competitors + product_context.adjacent_competitors}

ANTI-TRIGGERS (these look relevant but aren't — ignore):
{product_context.board_agenda_anti_triggers}

AGENDA CONTENTS:
{agenda_contents}

... rest of prompt ...
"""
```

**4. Signal Analysis — Claude Follow-Up Decisions (analysis/signals.py)**
```python
# Claude's follow-up decision prompt includes product context
SIGNAL_ANALYSIS_PROMPT = """You are researching {district_name} for an EdTech company that sells:

PRODUCT: {product_context.product_name}
CATEGORY: {product_context.product_category}
WHAT IT DOES: {product_context.one_liner}
KEY COMPETITORS: {product_context.direct_competitors}
RELEVANT KEYWORDS: {product_context.primary_keywords}

Given these initial search results, decide what to investigate next.
Prioritize follow-up searches that would reveal whether this district is likely to
purchase a {product_context.product_category} in the next {product_context.typical_sales_cycle_months} months.

... search results and rest of prompt ...
"""
```

**5. ICP Scoring (analysis/scoring.py)**
```python
def calculate_icp_score(profile: DistrictProfile, ctx: ProductContext) -> int:
    score = 0
    
    # Enrollment fit (using product-specific ranges)
    enrollment = profile.total_enrollment or 0
    if ctx.ideal_enrollment_min <= enrollment <= ctx.ideal_enrollment_max:
        score += 15
    elif enrollment > 0:
        # Partial credit if close to range
        score += 5
    
    # Per-pupil expenditure check
    if ctx.minimum_per_pupil_expenditure:
        if profile.per_pupil_expenditure and profile.per_pupil_expenditure < ctx.minimum_per_pupil_expenditure:
            score -= 10  # Below minimum — budget risk
    
    # Title I preference
    if ctx.title_i_preference == "required" and not profile.title_i:
        return 0  # Hard disqualify
    elif ctx.title_i_preference == "preferred" and profile.title_i:
        score += 5
    
    # Locale preference
    if ctx.locale_preferences and profile.locale_type:
        if any(loc in profile.locale_type for loc in ctx.locale_preferences):
            score += 5
    
    # Integration compatibility
    if ctx.required_integrations:
        ecosystem = profile.ecosystem.lower()
        lms = profile.lms.lower()
        for req in ctx.required_integrations:
            if req.lower() in ecosystem or req.lower() in lms:
                score += 10  # Compatible stack
                break
        else:
            score -= 10  # Missing required integration
    
    if ctx.incompatible_systems:
        for inc in ctx.incompatible_systems:
            if inc.lower() in (profile.ecosystem + profile.lms + profile.sis).lower():
                score -= 15  # Incompatible stack
    
    # Competitor installed (from tech profile or board meeting analysis)
    competitor_installed = None
    for signal in profile.signals:
        if signal.signal_type == "competitor_mention":
            for comp in ctx.direct_competitors:
                if comp.lower() in signal.detail.lower():
                    competitor_installed = comp
                    break
    
    if competitor_installed:
        # Check if it's a displacement opportunity or a lock-out
        for signal in profile.signals:
            if "renewal" in signal.detail.lower() and "1 year" in signal.detail.lower():
                score += 10  # Short renewal = dissatisfaction signal
            elif "multi-year" in signal.detail.lower() or "3 year" in signal.detail.lower():
                score -= 20  # Locked into competitor
    
    # Deal size viability based on district budget
    if ctx.typical_deal_size == "200k_plus" and profile.total_expenditures:
        if profile.total_expenditures < 50_000_000:  # Very small district
            score -= 10  # Probably can't afford enterprise pricing
    
    # ... then add signal-based scoring from the existing scoring logic ...
    
    return min(100, max(0, score))
```

**6. Final Dossier (analysis/synthesis.py)**
```python
# The synthesis prompt tells Claude exactly what the company sells
DOSSIER_PROMPT = """Generate an intelligence brief for {district_name}, {state}.

THE COMPANY AND PRODUCT:
Company: {product_context.company_name}
Product: {product_context.product_name}
Category: {product_context.product_category}
Description: {product_context.one_liner}
Competitors: {product_context.direct_competitors}
Typical deal size: {product_context.typical_deal_size}
Typical sales cycle: {product_context.typical_sales_cycle_months} months

Based on the data below, generate recommendations specific to selling 
{product_context.product_name} to this district. Reference specific competitors
if detected. Recommend contacting the most relevant decision maker for this
product category, not just the superintendent.

... data and rest of prompt ...
"""
```

### Updated Agent Entry Point

```python
# agent.py

class K12ResearchAgent:
    def __init__(self, tavily_api_key, apollo_api_key, anthropic_api_key, 
                 product_context: ProductContext, budget=20):
        """
        product_context is REQUIRED. The agent cannot run without knowing
        what product it is researching for.
        """
        self.product_context = product_context
        self.nces = NCESClient()
        self.apollo = ApolloClient(apollo_api_key)
        self.tavily = K12TavilyClient(tavily_api_key, budget=budget)
        self.anthropic = anthropic.Anthropic(api_key=anthropic_api_key)
        self.signal_detector = SignalDetector(self.tavily, self.anthropic, self.product_context)
        self.board_intel = BoardMeetingIntelligence(self.tavily, self.anthropic, self.product_context)

# Usage:
from config.templates import AI_TEACHING_TEMPLATE

# Start from a template and customize
ctx = AI_TEACHING_TEMPLATE
ctx.company_name = "Kira Learning"
ctx.product_name = "Kira Learning Platform"
ctx.one_liner = "AI-powered teaching platform with AI Teaching Assistants, instant generators, AI tutor, grader, ChatLabs, coding tools, and K-12 CS curriculum"

agent = K12ResearchAgent(
    tavily_api_key=os.getenv("TAVILY_API_KEY"),
    apollo_api_key=os.getenv("APOLLO_API_KEY"),
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    product_context=ctx,
)

report = agent.research_district("Fairfax County Public Schools", state="VA")
```

### Custom Configuration (No Template)

For products that don't fit a template:

```python
ctx = ProductContext(
    company_name="AcmeSafe",
    product_name="AcmeSafe Visitor Management",
    product_category="Visitor Management / Safety",
    one_liner="Cloud-based visitor management system with sex offender screening, emergency lockdown alerts, and volunteer tracking for K-12 schools",
    
    primary_keywords=[
        "visitor management", "school safety", "visitor check-in",
        "sex offender screening", "emergency notification",
    ],
    secondary_keywords=[
        "school security", "lockdown", "emergency preparedness",
        "volunteer management", "background check",
    ],
    direct_competitors=[
        "Raptor Technologies", "LobbyGuard", "Ident-A-Kid",
        "SchoolPass", "Verkada",
    ],
    primary_buyer_titles=[
        "Director of Safety and Security", "Director of Operations",
        "Chief Operations Officer",
    ],
    secondary_buyer_titles=[
        "Director of Technology", "Facilities Manager",
        "Assistant Superintendent of Operations",
    ],
    board_agenda_triggers=[
        "visitor management", "school safety", "security",
        "emergency preparedness", "lockdown", "visitor screening",
        "Raptor", "volunteer management",
    ],
    rfp_keywords=[
        "visitor management system", "visitor screening",
        "school safety platform", "emergency management",
    ],
    relevant_funding_sources=[
        "ESSER", "state school safety grants",
        "Bipartisan Safer Communities Act",
    ],
    ideal_enrollment_min=1000,
    ideal_enrollment_max=200000,
    typical_deal_size="10k_50k",
    typical_sales_cycle_months=4,
    implementation_requirements=["internet connection", "front desk computer or tablet"],
)
```

### Updated File Structure

```
k12_research_agent/
  config/
    __init__.py
    product_context.py    # ProductContext dataclass
    templates.py          # Pre-built configs: SIS, LMS, adaptive learning, AI teaching, etc.
    settings.py           # API keys, .env loading, constants, FIPS codes
  ...rest of existing structure...
```

### Updated Claude Code Instructions

```
I'm building a K12 school district research agent for EdTech sales intelligence.

Read the blueprint file: k12-research-agent-blueprint.md

CRITICAL DESIGN PRINCIPLE: The agent is product-context-aware. A ProductContext 
configuration (company, product, keywords, competitors, buyer titles, board meeting 
triggers) is REQUIRED and shapes every search query, every Claude prompt, and the 
scoring engine. The agent is useless without it.

Build in this order:
1. config/product_context.py (ProductContext dataclass with all fields)
2. config/templates.py (pre-built configs for SIS, LMS, adaptive learning, AI teaching)
3. config/settings.py (.env loading, FIPS codes, constants)
4. models/ (DistrictProfile, Contact, Signal, BoardMeetingReport)
5. data_sources/nces.py (Urban Institute API)
6. data_sources/apollo.py (Apollo — uses ProductContext for title priority)
7. data_sources/tavily_client.py (K12 wrapper — uses ProductContext for search keywords)
8. data_sources/board_meetings.py (Board Meeting Intelligence Module — uses ProductContext for triggers)
9. analysis/signals.py (SignalDetector — uses ProductContext in Claude prompts)
10. analysis/scoring.py (ICP scoring — uses ProductContext for weights and disqualifiers)
11. analysis/synthesis.py (Claude dossier — uses ProductContext for recommendations)
12. prompts/ (all prompts reference ProductContext fields)
13. agent.py (orchestrator — takes ProductContext as required init param)
14. output/formatters.py (markdown, JSON, CSV)
15. Test with AI_TEACHING_TEMPLATE customized for "Kira Learning" against 
    "Fairfax County Public Schools", state="VA"
```

---

## News Intelligence Module

News coverage reveals what's actually happening in a district — not the sanitized version on their website, but the real problems, controversies, wins, and pressures that drive purchasing decisions. Board meetings show what's being planned. News shows what's going wrong (or right) that creates the urgency behind those plans.

### Why News Changes the Sales Conversation

A sales rep who opens with "I saw you're evaluating LMS platforms" is informed. A sales rep who opens with "I saw the Herald reported parent frustration with remote learning tools last fall, and your board formed a technology committee in January — sounds like you're actively looking for a better solution" is dangerous. That rep clearly understands the district's world.

News gives you:
- **The "why" behind signals** — Board discusses cybersecurity policy (signal). News: district suffered a ransomware attack in October (the why). Now your outreach references the actual pain.
- **Problems the district hasn't solved yet** — Achievement scores dropped, parents are angry, state put them on a watch list. If your product addresses that problem, you have a warm entry.
- **Political dynamics** — Superintendent under fire, board recall election, budget vote failed. These affect timing and who to contact.
- **Community sentiment** — Are parents pushing for more technology or resisting it? Are teachers complaining about tool overload? This shapes your pitch angle.
- **Competitive intelligence from coverage** — "District signs $2M contract with PowerSchool" tells you the competitor just won. "Parents complain about PowerSchool outages" tells you the competitor is vulnerable.

### Architecture

```
data_sources/news_intel.py

class NewsIntelligence:

    search_district_news(district_name, state, months_back=18)
        -> Runs multiple targeted news searches across time ranges
    
    analyze_news(articles, product_context)
        -> Claude analyzes all articles for product-relevant problems and opportunities
    
    full_scan(district_name, state, product_context)
        -> Complete pipeline, returns NewsReport
```

### Search Strategy

News search requires multiple queries because no single search captures everything relevant. Run these in sequence, deduplicate results by URL.

```python
def search_district_news(self, district_name, state, product_context, months_back=18):
    """
    Run multiple targeted news searches to get comprehensive coverage.
    Budget: 6-10 Tavily credits for this module.
    """
    dn = district_name
    all_results = []
    seen_urls = set()
    
    queries = [
        # 1. General district news — catches everything
        {
            "query": f'"{dn}" {state}',
            "search_depth": "basic",
            "topic": "news",
            "max_results": 10,
            "time_range": "year",
        },
        # 2. Older news (year 2 of the 18-month window)
        # Tavily time_range doesn't support custom ranges, so use date in query
        {
            "query": f'"{dn}" {state} 2024 2025',
            "search_depth": "basic",
            "topic": "news",
            "max_results": 5,
        },
        # 3. Technology-specific news
        {
            "query": f'"{dn}" technology OR "digital learning" OR cybersecurity OR data breach OR devices',
            "search_depth": "basic",
            "topic": "news",
            "max_results": 5,
            "time_range": "year",
        },
        # 4. Budget and funding news
        {
            "query": f'"{dn}" budget OR funding OR "bond measure" OR layoffs OR cuts OR ESSER',
            "search_depth": "basic",
            "topic": "news",
            "max_results": 5,
            "time_range": "year",
        },
        # 5. Leadership and personnel news
        {
            "query": f'"{dn}" superintendent OR "school board" OR hired OR resigned OR fired OR appointed',
            "search_depth": "basic",
            "topic": "news",
            "max_results": 5,
            "time_range": "year",
        },
        # 6. Problems and controversies
        {
            "query": f'"{dn}" investigation OR lawsuit OR complaint OR failing OR crisis OR controversy',
            "search_depth": "basic",
            "topic": "news",
            "max_results": 5,
            "time_range": "year",
        },
        # 7. Achievement and academic performance
        {
            "query": f'"{dn}" "test scores" OR achievement OR graduation OR "state assessment" OR ranking',
            "search_depth": "basic",
            "topic": "news",
            "max_results": 5,
            "time_range": "year",
        },
        # 8. Product-specific news (uses ProductContext keywords)
        {
            "query": f'"{dn}" {" OR ".join(product_context.primary_keywords[:4])}',
            "search_depth": "basic",
            "topic": "news",
            "max_results": 5,
            "time_range": "year",
        },
        # 9. Competitor-specific news
        {
            "query": f'"{dn}" {" OR ".join(product_context.direct_competitors[:4])}',
            "search_depth": "basic",
            "topic": "news",
            "max_results": 5,
        },
    ]
    
    for q in queries:
        if self.tavily.credits_used >= self.tavily.budget:
            break  # Respect budget
        results = self.tavily.search(**q)
        if results:
            for r in results.get("results", []):
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)
    
    return all_results
```

**Note on Tavily's `topic` parameter:** Setting `topic="news"` tells Tavily to prioritize news sources in results. This is key — without it you get district websites, vendor marketing pages, and other noise mixed in.

### Deep Fetch for Key Articles

Some search results return snippets that hint at important content but don't give the full picture. After the initial search, selectively fetch full articles for the most promising hits.

```python
def fetch_key_articles(self, search_results, max_fetches=5):
    """
    Use Tavily extract to get full content from the most important articles.
    Claude decides which articles are worth reading in full.
    """
    
    # Ask Claude to pick the most important articles to read in full
    selection_prompt = f"""From these news article snippets about a school district, 
    pick the {max_fetches} most important ones to read in full. 
    Prioritize articles about:
    - Major problems or crises (data breaches, budget cuts, leadership scandals)
    - Technology decisions or initiatives
    - Large contracts or purchasing decisions
    - Significant leadership changes
    - Community pressure or parent advocacy
    
    Articles:
    {json.dumps([{"url": r["url"], "title": r.get("title", ""), "snippet": r.get("content", "")[:300]} for r in search_results], indent=2)}
    
    Return ONLY a JSON array of URLs to fetch: ["url1", "url2", ...]"""
    
    response = self.anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": selection_prompt}]
    )
    
    urls_to_fetch = json.loads(response.content[0].text)
    
    # Extract full content
    full_articles = self.tavily.client.extract(urls=urls_to_fetch[:max_fetches])
    
    return full_articles
```

### Claude News Analysis

This is where the product context makes news actionable. Claude reads all the coverage and maps it to sales opportunities.

```python
NEWS_ANALYSIS_SYSTEM_PROMPT = """You are a K12 EdTech sales intelligence analyst reading local news 
coverage about a school district. Your job is to identify problems, events, and dynamics that 
create opportunities to sell technology solutions.

You understand how news events translate to purchasing decisions:

PROBLEM -> OPPORTUNITY MAPPING:
- Data breach or cybersecurity incident -> Cybersecurity tool purchases within 3-6 months
- Declining test scores in local press -> Intervention/adaptive learning platform evaluation
- Parent complaints about communication -> Communication platform RFP
- Teacher shortage coverage -> AI teaching tools, automated grading, efficiency tools
- Budget cuts -> Consolidation of tools (fewer vendors, more integrated solutions)
- Budget surplus or bond passage -> Expansion purchasing across categories
- State takeover or corrective action -> Mandated improvements, often include tech
- Superintendent fired/resigned -> New leadership brings new vendors (12-24 month window opening)
- New superintendent profiled -> Read for their stated priorities, previous district's tech
- School safety incident -> Safety/security tool purchases within 6 months
- Equity/access complaints -> Device programs, connectivity, accessibility tools
- Failed technology rollout -> Replacement opportunity for the failed product
- COVID learning loss follow-up -> Continued investment in intervention tools
- Enrollment growth -> Infrastructure expansion, new device purchases
- Enrollment decline -> Budget pressure, consolidation, efficiency tools
- Construction/new schools -> Full technology build-out needed
- Union negotiations mentioning workload -> Tools that reduce teacher burden
- FOIA/transparency controversy -> Data governance, privacy tools

WHAT TO FLAG AS HIGH VALUE:
- Any problem your product directly solves
- Any mention of a competitor (positive or negative)
- Any indication of money being allocated or freed up
- Leadership statements about priorities or vision
- Community pressure that could accelerate purchasing
- State or federal mandates requiring technology compliance

WHAT TO DEPRIORITIZE:
- Sports coverage
- Individual student achievements
- Routine event announcements
- Opinion pieces with no actionable content
- Unrelated legal matters (slip-and-fall lawsuits, etc.)
"""

NEWS_ANALYSIS_USER_PROMPT = """Analyze this news coverage about {district_name}, {state} 
for sales intelligence relevant to:

PRODUCT: {product_context.product_name}
CATEGORY: {product_context.product_category}  
DESCRIPTION: {product_context.one_liner}
COMPETITORS: {product_context.direct_competitors}

NEWS ARTICLES:
{articles_content}

Analyze every article and identify:

1. PROBLEMS that create opportunities for {product_context.product_name}
2. EVENTS that affect purchasing timeline or budget
3. LEADERSHIP dynamics (who's new, who's leaving, who's under pressure)
4. COMPETITOR mentions (positive, negative, or neutral)
5. COMMUNITY SENTIMENT about technology and education
6. BUDGET indicators (cuts, surpluses, bonds, grants)

Return as JSON:
{{
  "district_narrative": "2-3 sentence summary of what's been happening in this district over the past 18 months based on news coverage",
  
  "problems_identified": [
    {{
      "problem": "District experienced ransomware attack in October 2025",
      "source": "Springfield Herald, Oct 15 2025",
      "source_url": "https://...",
      "severity": "HIGH",
      "product_relevance": "DIRECT" | "INDIRECT" | "NONE",
      "opportunity": "District will be allocating emergency cybersecurity budget. Our platform addresses exactly this.",
      "recommended_talking_point": "Reference the incident sensitively — focus on prevention and recovery support, not fear"
    }}
  ],
  
  "leadership_dynamics": [
    {{
      "event": "Superintendent Dr. Johnson announced resignation effective June 2026",
      "date": "December 2025",
      "source_url": "https://...",
      "implication": "Transition period — current leadership may fast-track pending purchases before departure. New superintendent search opens 12-24 month buying window.",
      "sales_impact": "POSITIVE" | "NEGATIVE" | "NEUTRAL"
    }}
  ],
  
  "competitor_mentions": [
    {{
      "competitor": "PowerSchool",
      "context": "Parents complained about PowerSchool portal outages during registration week",
      "sentiment": "NEGATIVE",
      "source_url": "https://...",
      "opportunity": "Competitor vulnerability — reference reliability and uptime in outreach"
    }}
  ],
  
  "budget_indicators": [
    {{
      "indicator": "$45M bond measure passed in November 2025 election",
      "source_url": "https://...",
      "amount": 45000000,
      "implication": "Significant new capital available. Bond language included technology infrastructure.",
      "timeline": "Funds available starting FY2026-27"
    }}
  ],
  
  "community_sentiment": {{
    "technology_attitude": "POSITIVE" | "MIXED" | "NEGATIVE" | "UNKNOWN",
    "key_concerns": ["data privacy", "screen time", "equity of access"],
    "parent_advocacy": "Parents pushing for 1:1 device program — potential ally for technology purchases",
    "teacher_sentiment": "Teachers reported feeling overwhelmed by number of tools — consolidation opportunity"
  }},
  
  "overall_news_signal": "HIGH" | "MEDIUM" | "LOW",
  "key_takeaway": "One sentence: what does the news tell us about selling to this district right now?"
}}

Return ONLY valid JSON."""
```

### Full Scan Method

```python
def full_scan(self, district_name, state, product_context):
    """
    Complete news intelligence pipeline.
    
    Tavily credit budget: 8-12 credits
      - 7-9 credits: news searches (7-9 queries at 1 credit each)
      - 1-2 credits: full article extraction (5-10 URLs)
      - Claude calls: ~$0.05-0.10
    """
    
    # Step 1: Run targeted news searches
    search_results = self.search_district_news(district_name, state, product_context)
    
    if not search_results:
        return NewsReport(status="no_news_found")
    
    # Step 2: Fetch full content for key articles
    full_articles = self.fetch_key_articles(search_results, max_fetches=5)
    
    # Step 3: Combine snippets + full articles for analysis
    # Use full content where available, fall back to snippets
    articles_for_analysis = self._merge_results(search_results, full_articles)
    
    # Step 4: Claude analysis
    analysis = self.analyze_news(articles_for_analysis, product_context)
    
    return NewsReport(
        status="complete",
        articles_found=len(search_results),
        articles_analyzed=len(articles_for_analysis),
        district_narrative=analysis.get("district_narrative", ""),
        problems=analysis.get("problems_identified", []),
        leadership_dynamics=analysis.get("leadership_dynamics", []),
        competitor_mentions=analysis.get("competitor_mentions", []),
        budget_indicators=analysis.get("budget_indicators", []),
        community_sentiment=analysis.get("community_sentiment", {}),
        overall_signal=analysis.get("overall_news_signal", "UNKNOWN"),
        key_takeaway=analysis.get("key_takeaway", ""),
        source_urls=[r["url"] for r in search_results],
    )
```

### Data Model

```python
# models/news.py

@dataclass
class NewsProblem:
    problem: str
    source: str
    source_url: str
    severity: str               # HIGH, MEDIUM, LOW
    product_relevance: str      # DIRECT, INDIRECT, NONE
    opportunity: str
    recommended_talking_point: str

@dataclass
class LeadershipEvent:
    event: str
    date: str
    source_url: str
    implication: str
    sales_impact: str           # POSITIVE, NEGATIVE, NEUTRAL

@dataclass
class CompetitorMention:
    competitor: str
    context: str
    sentiment: str              # POSITIVE, NEGATIVE, NEUTRAL
    source_url: str
    opportunity: str

@dataclass 
class BudgetIndicator:
    indicator: str
    source_url: str
    amount: Optional[float] = None
    implication: str = ""
    timeline: str = ""

@dataclass
class CommunitySentiment:
    technology_attitude: str = "UNKNOWN"    # POSITIVE, MIXED, NEGATIVE, UNKNOWN
    key_concerns: list = field(default_factory=list)
    parent_advocacy: str = ""
    teacher_sentiment: str = ""

@dataclass
class NewsReport:
    status: str = ""
    articles_found: int = 0
    articles_analyzed: int = 0
    district_narrative: str = ""
    problems: list = field(default_factory=list)            # List of NewsProblem
    leadership_dynamics: list = field(default_factory=list)  # List of LeadershipEvent
    competitor_mentions: list = field(default_factory=list)  # List of CompetitorMention
    budget_indicators: list = field(default_factory=list)    # List of BudgetIndicator
    community_sentiment: CommunitySentiment = field(default_factory=CommunitySentiment)
    overall_signal: str = ""
    key_takeaway: str = ""
    source_urls: list = field(default_factory=list)
    tavily_credits_used: int = 0
```

### Integration with Main Agent

News intelligence plugs into the agent as Step 3c, after signal detection and board meetings, before synthesis.

```python
# In agent.py, inside research_district():

    # Step 3: Signal detection (existing)
    profile.signals = self.signal_detector.detect_signals(district_name, state)
    
    # Step 3b: Board meeting deep scan (existing)
    board_report = self.board_intel.full_scan(district_name, state, product_category)
    profile.board_meeting_report = board_report
    
    # Step 3c: News intelligence (NEW)
    logger.info(f"Scanning news coverage...")
    news_intel = NewsIntelligence(self.tavily, self.anthropic)
    news_report = news_intel.full_scan(district_name, state, self.product_context)
    profile.news_report = news_report
    
    # Convert news findings into Signal objects
    if news_report.status == "complete":
        for problem in news_report.problems:
            if problem.product_relevance in ("DIRECT", "INDIRECT"):
                profile.signals.append(Signal(
                    signal_type="news_problem",
                    strength=problem.severity,
                    title=f"News: {problem.problem}",
                    detail=f"{problem.opportunity}. Talking point: {problem.recommended_talking_point}",
                    source_url=problem.source_url,
                    relevance_note=problem.recommended_talking_point,
                ))
        
        for event in news_report.leadership_dynamics:
            profile.signals.append(Signal(
                signal_type="news_leadership",
                strength="HIGH" if event.sales_impact == "POSITIVE" else "MEDIUM",
                title=f"News: {event.event}",
                detail=event.implication,
                source_url=event.source_url,
            ))
        
        for mention in news_report.competitor_mentions:
            profile.signals.append(Signal(
                signal_type="news_competitor",
                strength="HIGH" if mention.sentiment == "NEGATIVE" else "MEDIUM",
                title=f"News: {mention.competitor} — {mention.sentiment}",
                detail=f"{mention.context}. Opportunity: {mention.opportunity}",
                source_url=mention.source_url,
            ))
        
        for budget in news_report.budget_indicators:
            profile.signals.append(Signal(
                signal_type="news_budget",
                strength="HIGH" if (budget.amount and budget.amount > 1000000) else "MEDIUM",
                title=f"News: {budget.indicator}",
                detail=f"{budget.implication}. Timeline: {budget.timeline}",
                source_url=budget.source_url,
            ))
```

### How News Feeds Into the Final Dossier

The synthesis prompt gets an additional section:

```python
# Added to the dossier prompt in analysis/synthesis.py:

"""
## News Coverage (Past 18 Months)

District Narrative: {news_report.district_narrative}

Problems Identified:
{formatted_problems}

Leadership Dynamics:
{formatted_leadership}

Competitor Mentions:
{formatted_competitors}

Budget Indicators:
{formatted_budget}

Community Sentiment:
- Technology attitude: {news_report.community_sentiment.technology_attitude}
- Key concerns: {news_report.community_sentiment.key_concerns}
- Parent advocacy: {news_report.community_sentiment.parent_advocacy}
- Teacher sentiment: {news_report.community_sentiment.teacher_sentiment}

News Signal Strength: {news_report.overall_signal}
Key Takeaway: {news_report.key_takeaway}
"""
```

This gives Claude the full picture for the dossier. Instead of just "this district has 45,000 students and a new superintendent," the dossier can say "this district has 45,000 students, a new superintendent who was hired after the previous one resigned amid a budget controversy, parents have been publicly pushing for better technology, the district just passed a bond measure, and their current SIS vendor had a public outage that made the local news."

### Updated Cost Estimate Per District (with all modules)

| Module | Tavily Credits | Claude Cost |
|---|---|---|
| Signal detection | 8-15 | ~$0.05-$0.10 |
| Board meeting scan | 5-10 | ~$0.03-$0.08 |
| News intelligence | 8-12 | ~$0.05-$0.10 |
| Tech profile detection | 3-5 | — |
| Final dossier synthesis | — | ~$0.05-$0.15 |
| **Total per district** | **24-42 credits** | **~$0.18-$0.43** |
| **Total per district (all-in)** | | **~$0.35-$0.75** |

At 1,000 free Tavily credits/month, you can research ~25-40 districts for free. After that, $0.008/credit = about $0.20-$0.34 in Tavily costs per district. Total all-in with Claude API: roughly $0.35-$0.75 per district.

For 100 districts: ~$35-$75 total.

### Scoring Engine Update

News signals affect ICP scoring:

```python
# In analysis/scoring.py, add to calculate_icp_score():

    # News-based scoring adjustments
    if profile.news_report and profile.news_report.status == "complete":
        
        # Direct product-relevant problems = strong buying signal
        direct_problems = [p for p in profile.news_report.problems 
                          if p.product_relevance == "DIRECT"]
        score += min(15, len(direct_problems) * 8)
        
        # Negative competitor sentiment = displacement opportunity
        negative_competitor = [m for m in profile.news_report.competitor_mentions 
                              if m.sentiment == "NEGATIVE"]
        score += min(10, len(negative_competitor) * 5)
        
        # Budget indicators with large amounts
        big_budget = [b for b in profile.news_report.budget_indicators 
                     if b.amount and b.amount > 1000000]
        score += min(10, len(big_budget) * 5)
        
        # Community pushing for tech = political cover for purchase
        if profile.news_report.community_sentiment.technology_attitude == "POSITIVE":
            score += 5
        elif profile.news_report.community_sentiment.technology_attitude == "NEGATIVE":
            score -= 5  # Harder sell, community resistance
        
        # Anti-signals from news
        # District in crisis (state takeover, major scandal) = frozen purchasing
        crisis_keywords = ["state takeover", "investigation", "indictment", "bankruptcy"]
        for problem in profile.news_report.problems:
            if any(kw in problem.problem.lower() for kw in crisis_keywords):
                score -= 20  # Major red flag
```

### Updated File Structure

```
k12_research_agent/
  ...existing...
  data_sources/
    news_intel.py         # NEW — NewsIntelligence class
  models/
    news.py               # NEW — NewsReport, NewsProblem, LeadershipEvent, etc.
  prompts/
    news_analysis.py      # NEW — News analysis prompts
```

### What News Catches That Other Modules Miss

Real examples of news-only intelligence:

- "Teachers Union Protests Mandatory Use of [Competitor Platform]" — competitor vulnerability you'd never find in a board agenda because the board wouldn't advertise internal conflict
- "District Receives $8M State Innovation Grant for STEM Education" — money earmarked for exactly what you sell, announced in press before it hits board agendas
- "Parents Pack Board Meeting Demanding Better Online Learning Tools" — community pressure creating political cover for the purchase, but the board minutes might just say "public comment period"
- "Superintendent Dr. Martinez Profiled in EdWeek: 'Every Student Deserves AI-Powered Learning'" — the new super's stated priorities, from an interview, not from district documents
- "District Settles Student Data Privacy Lawsuit for $500K" — they're now hyper-sensitive about data security, which could be a selling point or an obstacle depending on your product
- "Local Paper Investigation: District Spent $3M on EdTech Tools with No Measurable Impact" — they're under scrutiny, which means the next purchase needs to come with clear ROI evidence. Shape your pitch accordingly.
