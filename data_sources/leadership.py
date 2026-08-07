import requests
import logging
import json
from typing import List, Optional
from models.contact import Contact
from config.product_context import ProductContext
from .tavily_client import K12TavilyClient
from config.settings import LINKEDIN_RAPIDAPI_KEY, LINKEDIN_RAPIDAPI_HOST

logger = logging.getLogger(__name__)

class LeadershipIntelligence:
    """
    Pivoted Engine: Focuses on Administrative Job Changes.
    1. Finds Leadership/Superintendent page.
    2. Extracts names via Tavily Extract + Claude.
    3. Verifies tenure via LinkedIn Scraper (RapidAPI).
    """

    def __init__(self, tavily_client: K12TavilyClient, anthropic_client=None):
        self.tavily = tavily_client
        self.claude = anthropic_client
        self.rapid_key = LINKEDIN_RAPIDAPI_KEY
        self.rapid_host = LINKEDIN_RAPIDAPI_HOST

    def get_leadership_changes(self, district_name: str, state: str, context: ProductContext) -> List[Contact]:
        """
        Detect job changes across the entire district administration.
        Returns a verified list of all administrators with tenure data.
        """
        logger.info(f"--- Exhaustive Leadership Discovery: {district_name}, {state} ---")
        
        # 1. Discover Comprehensive Leadership/Directory Page
        dir_url = self._discover_leadership_page(district_name, state)
        if not dir_url:
            logger.warning("No comprehensive leadership page found. Aborting deep enrichment.")
            return []

        # 2. Extract Full Personnel List (Names/Titles) - No limits
        raw_personnel = self._extract_personnel(dir_url)
        if not raw_personnel:
            logger.warning("No personnel extracted from directory.")
            return []

        logger.info(f"Extracted {len(raw_personnel)} administrators. Starting deep verification...")

        # 3. Enrich & Verify via LinkedIn for ALL extracted personnel
        final_contacts = []
        for p in raw_personnel: 
            name = p.get("name")
            title = p.get("title")
            
            # Match LinkedIn URL
            linkedin_url = self._match_linkedin_url(name, title, district_name, state)
            if not linkedin_url:
                # Add unverified contact if LinkedIn not found
                final_contacts.append(Contact(name=name, title=title, source="Web Directory"))
                continue
                
            # Fetch Tenure & Identity Verification
            contact = self._enrich_via_linkedin(name, title, district_name, state, linkedin_url)
            if contact:
                final_contacts.append(contact)
            else:
                # Fallback to unverified contact
                final_contacts.append(Contact(name=name, title=title, linkedin_url=linkedin_url, source="Web Directory (LinkedIn Unverified)"))

        return final_contacts

    def _discover_leadership_page(self, district_name: str, state: str) -> Optional[str]:
        # Loosening search to find full administrative directories
        queries = [
            f'"{district_name}" school district {state} "District Office" administration directory',
            f'"{district_name}" {state} "Cabinet" or "Leadership Team" roster',
            f'"{district_name}" {state} superintendent personnel directory'
        ]
        
        for query in queries:
            logger.info(f"Searching for exhaustive directory via: {query}")
            results = self.tavily.search(query, search_depth="basic", max_results=5)
            if results and results.get("results"):
                for res in results["results"]:
                    url = res.get("url", "")
                    if any(x in url.lower() for x in [".edu", ".gov", "administration", "directory", "staff", "cabinet"]):
                        logger.info(f"Targeting comprehensive directory URL: {url}")
                        return url
        return None

    def _extract_personnel(self, url: str) -> List[dict]:
        """Extracts names/titles from the district page using Claude."""
        try:
            logger.info(f"Scraping personnel list from: {url}")
            extract = self.tavily.extract(urls=[url])
            
            if not extract or not extract.get("results"):
                logger.warning(f"No extract results for {url}")
                return []
                
            content = extract.get("results")[0].get("raw_content", "")
            
            logger.info(f"Raw content length: {len(content)}")
            if len(content) < 150:
                logger.warning("Content too short for reliable extraction. Skipping.")
                return []
                
            prompt = f"""Extract the FULL administrative roster from this school district directory.
            For each entry, you MUST extract:
            1. The HUMAN name of the administrator (Ignore department names like 'Office of the Superintendent').
            2. Their specific Job Title.
            
            Look for patterns like 'Name - Title' or 'Title: Name'.
            
            RAW CONTENT: {content[:35000]}
            
            Return ONLY JSON:
            {{"personnel": [{{"name": "Actual Person Name", "title": "Job Title"}}]}}"""
            
            response = self.claude.messages.create(
                model="claude-haiku-4-5",
                max_tokens=4000, # Increased to handle full roster
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response.content:
                logger.warning("Empty response from Claude.")
                return []
                
            text_content = response.content[0].text
            logger.info(f"Claude Response: {text_content[:200]}...")
            
            # Robust JSON extraction using regex
            import re
            json_match = re.search(r"(\{.*\})", text_content, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    return data.get("personnel", [])
                except json.JSONDecodeError:
                    logger.error("Parsed JSON block was invalid.")
            else:
                logger.warning("No JSON block found in Claude's response.")
            
            return []
        except Exception as e:
            logger.error(f"Personnel extraction failed: {e}")
            return []

    def _match_linkedin_url(self, name: str, title: str, district: str, state: str) -> Optional[str]:
        """Finds the most likely LinkedIn URL using Multi-Strategy Search."""
        clean_name = name.replace("Dr. ", "").replace("Dr ", "").strip()
        
        # Strategy 1: site-limited name + district
        # Strategy 2: Absolute Name + Title + District
        queries = [
            f'site:linkedin.com/in "{clean_name}" {district} {state}',
            f'"{clean_name}" "{title}" {district} LinkedIn',
            f'"{name}" {district} LinkedIn'
        ]
        
        all_results = []
        for query in queries:
            logger.info(f"Searching LinkedIn via: {query}")
            results = self.tavily.search(query, search_depth="basic", max_results=8)
            if results and results.get("results"):
                for res in results["results"]:
                    if "linkedin.com/in/" in res["url"].lower():
                        all_results.append(res)
                
        if not all_results:
            logger.warning(f"No LinkedIn results found for {name}")
            return None
            
        # De-duplicate results by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r["url"].split("?")[0].rstrip("/") # Normalize URL
            if url not in seen_urls:
                r["url"] = url
                unique_results.append(r)
                seen_urls.add(url)

        logger.info(f"Analyzing {len(unique_results)} unique LinkedIn candidates.")
        
        # Use Claude to pick the BEST matching URL from snippets
        prompt = f"""Given these LinkedIn search results for {name} ({title} at {district}), 
        pick the URL that most likely belongs to this specific person.
        
        TARGET:
        Name: {name}
        Title: {title}
        Org: {district}
        
        RESULTS:
        {json.dumps(unique_results, indent=2)}
        
        CRITERIA:
        - Prioritize results that mention '{name}' and '{district}' or '{state}'.
        - Even if it's not a 100% match in the snippet, if it's the most likely candidate, return the URL.
        - We will perform deep verification in the next step.
        
        Return ONLY the URL as a string. If absolutely no reasonable match exists, return 'NONE'."""
        
        response = self.claude.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        url = response.content[0].text.strip()
        logger.info(f"Claude raw selection: {url}")
        
        # Extract URL using simple regex to be safe
        import re
        url_match = re.search(r'(https://www\.linkedin\.com/in/[^\s"\'\\)]+)', url)
        if url_match:
            selected_url = url_match.group(1)
            logger.info(f"AI Selected LinkedIn URL: {selected_url}")
            return selected_url
            
        return None

    def _enrich_via_linkedin(self, name: str, title: str, district: str, state: str, linkedin_url: str) -> Optional[Contact]:
        """
        Calls Fresh LinkedIn Scraper API and uses Claude to verify identity/tenure.
        """
        try:
            logger.info(f"Calling LinkedIn Scraper for: {linkedin_url}")
            # Standardizing endpoint and headers
            url = f"https://{self.rapid_host}/enrich-lead?linkedin_url={linkedin_url}"
            headers = {
                "X-RapidAPI-Key": self.rapid_key,
                "X-RapidAPI-Host": self.rapid_host
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 401:
                logger.error("LinkedIn Scraper failed with 401. Check RapidAPI key/subscription.")
                return None
            if response.status_code != 200:
                logger.warning(f"LinkedIn Scraper API failed ({response.status_code})")
                return None
                
            profile_data = response.json().get("data", {})
            if not profile_data:
                return None
            
            # Tier 3: Identity & Tenure Verification via Claude
            prompt = f"""
            Identify if this LinkedIn profile belongs to the leader of {district}.
            
            TARGET:
            Name: {name}
            Title: {title}
            State: {state}
            
            LINKEDIN PROFILE DATA (JSON):
            {json.dumps(profile_data, indent=2)}
            
            VERIFICATION PROTOCOL:
            1. LOCATION CHECK: Is the profile in or near {state}?
            2. JOB MATCH: Does the history show them currently at {district}?
            3. TENURE & JOB CHANGE: When did they start this current role? 
               - If they started WITHIN THE LAST 24 MONTHS (2 Years), set "is_new" to true.
               - Otherwise, set "is_new" to false.
            
            Return JSON:
            {{
                "verified": true/false,
                "confidence_score": 0-100,
                "start_date": "YYYY-MM-DD",
                "tenure_months": 24,
                "is_new": true/false,
                "previous_org": "..."
            }}
            """
            
            verification = self.claude.messages.create(
                model="claude-haiku-4-5",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )
            v_text = verification.content[0].text
            logger.info(f"Verification AI Response: {v_text[:200]}...")

            import re
            v_match = re.search(r"(\{.*\})", v_text, re.DOTALL)
            if not v_match:
                logger.warning("No JSON block in verification response.")
                return None
                
            v_data = json.loads(v_match.group(1))
            
            if not v_data.get("verified") or v_data.get("confidence_score", 0) < 60:
                logger.info(f"LinkedIn Verification failed for {name} (Confidence: {v_data.get('confidence_score')})")
                return None
            
            return Contact(
                name=name,
                title=title,
                linkedin_url=linkedin_url,
                started_at=v_data.get("start_date"),
                tenure_months=v_data.get("tenure_months"),
                is_new=v_data.get("is_new", False),
                previous_org=v_data.get("previous_org"),
                source=f"LinkedIn (Job Change Signal: {'YES' if v_data.get('is_new') else 'NO'})"
            )

        except Exception as e:
            logger.error(f"LinkedIn enrichment failed: {e}")
            return None
