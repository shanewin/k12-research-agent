# K12 Research Agent: Workflows & Data Points

The K12 Research Agent is an autonomous system designed to build high-fidelity intelligence dossiers on school districts. The core goal is to determine a district's Ideal Customer Profile (ICP) match based on an EdTech company's specific `ProductContext`.

## The Research Pipeline (9 Phases)

The agent executes a highly modular, multi-phase research pipeline in `agent.py`, gathering over 80 data points.

1.  **NCES Baseline (Phase 3)**
    *   **Module**: `NCESClient`
    *   **Data Points**: Firmographics, total enrollment, district type, state, NCES ID. Matches the district to official federal records.

2.  **Tech Profile & Site-First Detection (Phase 7)**
    *   **Module**: `TechProfileDetector` (uses Tavily & Anthropic)
    *   **Data Points**: Finds the official district website URL (`profile.website_url`) and uses agentic reasoning to extract information directly from the district's site layout. Discovers the existing technology landscape, looking for the specific `ProductContext` incumbent vendor, systems currently in use (e.g., LMS, SIS), and potential integration blockers.

3.  **Leadership & Job Change Intelligence (Phase 4)**
    *   **Module**: `LeadershipIntelligence` (uses Tavily & Anthropic)
    *   **Data Points**: Identifies key administrative contacts and flags recent job changes or new hires within the last 24 months. Targets titles specified in the `ProductContext` (primary and secondary buyers).

4.  **Board Meeting Deep Scan (Phase 5)**
    *   **Module**: `BoardMeetingIntelligence` (uses Tavily & Anthropic)
    *   **Data Points**: Scans board portals for strategic plans, active RFPs, budget approvals, and discussions matching `board_agenda_triggers` (from `ProductContext`).

5.  **News Intelligence (Phase 6)**
    *   **Module**: `NewsIntelligence` (uses Tavily & Anthropic)
    *   **Data Points**: Pulls recent news articles related to the district, looking for funding announcements, leadership controversies, or strategic initiatives.

6.  **USAC E-Rate Integration (Phase 1.1)**
    *   **Module**: `ErateIntelligence`
    *   **Data Points**: Pulls historical E-Rate funding data, revealing telecom and networking budgets and historical vendor relationships.

7.  **Agentic Signal Detection (Phase 7)**
    *   **Module**: `SignalDetector` (uses Tavily & Anthropic)
    *   **Data Points**: Uses an autonomous agent loop to detect specific "buying signals" based on the holistic context gathered so far. 

8.  **District Buying Profile Analysis (Phase 1.1)**
    *   **Module**: `BuyingProfileAnalyzer` (uses Anthropic)
    *   **Data Points**: Synthesizes a specific buying profile—determining the district's likely purchasing velocity, budget constraints, and organizational structure.

9.  **Scoring & Synthesis (Phase 8)**
    *   **Module**: `ScoringEngine` and `SynthesisEngine`
    *   **Data Points**: Calculates an `icp_score` (0-100) based on weighted firmographic, decision-maker, and signal scores. Generates an `intelligence_brief` and a `recommended_action` (e.g., "Immediate Outreach", "Nurture").

## Product Context Dependency

The agent's entire logic is shaped by the `ProductContext`. If the template lacks high-quality keywords or exact buyer titles, the Tavily queries and Anthropic extractions will yield poor results. Data points such as `rfp_keywords`, `board_agenda_triggers`, and `ideal_enrollment_min` directly influence the score.
