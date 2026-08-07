import logging
import time
from dataclasses import asdict
from typing import Optional, Callable
from anthropic import Anthropic
import concurrent.futures

from config.settings import TAVILY_API_KEY, ANTHROPIC_API_KEY
from config.product_context import ProductContext
from models.district import DistrictProfile
from data_sources.nces import NCESClient
from data_sources.leadership import LeadershipIntelligence
from data_sources.tavily_client import K12TavilyClient
from data_sources.news_intel import NewsIntelligence
from data_sources.board_meetings import BoardMeetingIntelligence
from data_sources.tech_profile import TechProfileDetector
from data_sources.erate import ErateIntelligence
from analysis.buying_profile import BuyingProfileAnalyzer
from analysis.signals import SignalDetector
from analysis.scoring import ScoringEngine
from analysis.synthesis import SynthesisEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class K12ResearchAgent:
    def __init__(self, product_context: ProductContext, budget: int = 2000):
        """
        product_context is REQUIRED as per the blueprint.
        The agent is useless without knowing the specific product context.
        """
        self.context = product_context
        self.tavily = K12TavilyClient(TAVILY_API_KEY, budget=budget)
        self.anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Intelligence Modules
        self.nces = NCESClient()
        self.tech_profile = TechProfileDetector(self.tavily, self.anthropic)
        self.leadership = LeadershipIntelligence(self.tavily, self.anthropic)
        self.board_intel = BoardMeetingIntelligence(self.tavily, self.anthropic)
        self.news_intel = NewsIntelligence(self.tavily, self.anthropic)
        self.erate_intel = ErateIntelligence()
        
        # Analysis Engines
        self.signal_detector = SignalDetector(self.tavily, self.anthropic)
        self.buying_profile = BuyingProfileAnalyzer(self.anthropic)
        self.scoring = ScoringEngine()
        self.synthesis = SynthesisEngine(self.anthropic)

    def research_district(self, name: str, state_code: str, status_callback: Optional[Callable[[str], None]] = None) -> DistrictProfile:
        """
        High-fidelity modular research pipeline.
        Each step contributes to the 80+ data points for the intelligence dossier.
        """
        def update_status(msg):
            logger.info(msg)
            if status_callback:
                status_callback(msg)

        update_status(f"--- STARTING RESEARCH: {name}, {state_code} ---")
        
        profile = DistrictProfile(district_name=name, state=state_code)

        # 1. Exhaustive Domain Scraping (Phase 1)
        update_status("Phase 1: Resolving official district website...")
        website_url = None

        # Authoritative source first: the funding dataset carries each CA
        # district's official website (no search, no wrong-domain risk).
        from data_sources.local_funding import LocalFundingData
        funding_row = LocalFundingData.lookup(district_name=name, state=state_code)
        if funding_row and funding_row.get("website"):
            website_url = funding_row["website"]
            if not website_url.startswith("http"):
                website_url = f"https://{website_url}"
            update_status(f"Phase 1: Official website from dataset: {website_url}")

        if not website_url:
            query = f'"{name}" {state_code} official school district website'
            results = self.tavily.search(query, search_depth="basic", max_results=5)
            # Aggregators/encyclopedias that match the old ".org" heuristic but
            # are never the district's own site
            blocked = ["wikipedia.", "facebook.", "niche.com", "greatschools",
                       "usnews.", "linkedin.", "twitter.", "instagram.", "youtube.",
                       "publicschoolreview", "highbond.com", "zillow."]
            if results and results.get("results"):
                for res in results["results"]:
                    url = res.get("url", "").lower()
                    if any(b in url for b in blocked):
                        continue
                    if any(x in url for x in [".org", ".edu", ".us", ".net", ".k12"]):
                        website_url = res.get("url")
                        break
        
        # 1. Targeted Discovery & Download (Phase 1)
        update_status("Phase 1: Executing Targeted Site-First Discovery (2-Year Window)...")
        if website_url:
            from urllib.parse import urlparse
            parsed = urlparse(website_url)
            website_url = f"{parsed.scheme}://{parsed.netloc}/"
            domain = parsed.netloc.replace("www.", "")
            profile.website_url = website_url
            
            from analysis.site_discovery import SiteDiscoveryAgent
            discovery = SiteDiscoveryAgent(self.tavily)
            target_urls = discovery.generate_target_urls(domain, self.context)
            profile.metadata["scraped_urls"] = target_urls
            
            update_status(f"Phase 1: Downloading {len(target_urls)} highly-targeted pages...")
            from data_sources.universal_scraper import UniversalScraper
            scraper = UniversalScraper(max_pages=200, max_pdf_pages=50)
            full_corpus = scraper.scrape_urls(target_urls, domain, status_callback=update_status)
            
            update_status("Filtering downloaded target pages for strict context...")
            from analysis.keyword_scanner import KeywordScanner
            scanner = KeywordScanner(snippet_radius=500)
            profile.corpus = scanner.scan_for_context(full_corpus, self.context)
            
        # Bypassing Anthropic Tier 1 Rate Limits (50,000 TPM)
        update_status("Pausing 15s to clear LLM token rate limits before deep-extraction...")
        time.sleep(15)

        # 2. Comprehensive Data Extraction (Phase 2)
        update_status("Phase 2: Comprehensive Corpus Analysis for 80+ Data Points...")
        # Have internal modules consume profile.corpus instead of live searches
        from analysis.comprehensive_extractor import ComprehensiveExtractor
        comp_extractor = ComprehensiveExtractor(self.anthropic)
        comp_extractor.extract_all_data_points(profile, self.context)

        self.tech_profile.detect_tech_landscape(name, state_code, profile, self.context)
        
        update_status("Pausing 15s to clear LLM token rate limits before parallel runs...")
        time.sleep(15)

        update_status("Phases 3-6: Firing parallel augmentation modules (NCES, LinkedIn, Board, News)...")
        
        def run_nces():
            nces_profile = self.nces.get_district_profile(name, state_code)
            if nces_profile:
                profile.nces_id = nces_profile.nces_id
                profile.total_enrollment = nces_profile.total_enrollment
                profile.number_of_schools = nces_profile.number_of_schools
                profile.total_revenue = nces_profile.total_revenue
                profile.per_pupil_expenditure = nces_profile.per_pupil_expenditure

        def run_linkedin():
            profile.contacts = self.leadership.get_leadership_changes(name, state_code, self.context)

        def run_board():
            profile.board_meeting_report = self.board_intel.full_scan(name, state_code, self.context)
            
        def run_news():
            profile.news_report = self.news_intel.full_scan(name, state_code, self.context)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(run_nces),
                executor.submit(run_linkedin),
                executor.submit(run_board),
                executor.submit(run_news)
            ]
            concurrent.futures.wait(futures)
        
        # 5a. Contact email discovery (published addresses + district convention)
        if profile.contacts and profile.website_url:
            update_status(f"Finding email addresses for {len(profile.contacts)} contacts...")
            from data_sources.email_finder import find_emails
            try:
                stats = find_emails(profile.contacts, profile.website_url, self.tavily)
                profile.metadata["email_discovery"] = stats
                update_status(f"Emails: {stats['published']} published, {stats['pattern']} inferred, {stats['none']} not found")
            except Exception as e:
                logger.error(f"Email discovery failed: {e}")

        # 5b. Local Funding Enrichment (FundFinder dataset — free, offline)
        update_status("Enriching with local funding dataset (Title I, LCFF, FRPM, poverty)...")
        from data_sources.local_funding import LocalFundingData
        LocalFundingData.enrich_profile(profile)

        # 6. USAC E-Rate Integration (V1.1)
        if profile.nces_id:
            update_status("V1.1: Pulling USAC E-Rate funding data...")
            profile.erate_report = self.erate_intel.get_district_erate_data(profile.nces_id, name)
        
        # 7. Agentic Signal Detection (Phase 7)
        update_status("Phase 7: Running agentic research loop for complex signals...")
        agent_context = {
            "nces_id": profile.nces_id,
            "enrollment": profile.total_enrollment,
            "board_report": asdict(profile.board_meeting_report) if profile.board_meeting_report else None
        }
        profile.signals = self.signal_detector.detect_signals(name, state_code, self.context, agent_context)
        
        # 6b. District Buying Profile Analysis (V1.1)
        update_status("V1.1: Analyzing district buying behavior and procurement velocity...")
        profile.buying_profile = self.buying_profile.analyze(profile, self.context)
        
        # 7. Scoring & Synthesis (Phase 8)
        update_status("Phase 8: Finalizing ICP score and synthesizing dossier...")
        profile.icp_score = self.scoring.calculate_score(profile, self.context)
        profile.metadata["funding_fit_applied"] = True  # scored natively; rescore script skips
        profile.signal_strength = self.scoring.get_signal_strength(profile.icp_score)
        profile.recommended_action = self.scoring.get_recommended_action(profile.icp_score)
        
        profile.intelligence_brief = self.synthesis.generate_brief(profile, self.context)
        
        profile.tavily_credits_used = self.tavily.credits_used
        update_status(f"--- RESEARCH COMPLETE for {name} (Score: {profile.icp_score}) ---")
        
        return profile
