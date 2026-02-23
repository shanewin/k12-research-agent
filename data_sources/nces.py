import requests
import logging
from typing import Optional, Dict, List
from models.district import DistrictProfile
from config.settings import STATE_FIPS, LATEST_NCES_YEAR

logger = logging.getLogger(__name__)

class NCESClient:
    BASE_URL = "https://educationdata.urban.org/api/v1"

    def get_district_profile(self, name: str, state_code: str) -> Optional[DistrictProfile]:
        """
        Complete pipeline to fetch all NCES data points and return a populated DistrictProfile.
        """
        state_fips = STATE_FIPS.get(state_code.upper())
        if not state_fips:
            logger.error(f"FIPS code not found for state: {state_code}")
            return None

        # 1. Directory Search (Step 1 of blueprint)
        dir_data = self._fetch_directory(name, state_fips)
        if not dir_data:
            return None

        grade_lo = dir_data.get('grade_lo_offered')
        grade_hi = dir_data.get('grade_hi_offered')
        grade_span = f"{grade_lo}-{grade_hi}" if grade_lo and grade_hi else "Unknown"

        profile = DistrictProfile(
            district_name=dir_data.get("lea_name"),
            state=state_code.upper(),
            nces_id=dir_data.get("leaid"),
            city=dir_data.get("city_location"),
            county=dir_data.get("county_name"),
            total_enrollment=dir_data.get("enrollment"),
            locale_type=dir_data.get("urban_centric_locale"),
            grade_span=grade_span
        )

        year = LATEST_NCES_YEAR
        leaid = profile.nces_id

        # 2. Financials (Step 2 of blueprint)
        finance = self._fetch_finance(leaid, year)
        if finance:
            profile.total_revenue = finance.get("rev_total")
            profile.total_expenditures = finance.get("exp_total")
            profile.per_pupil_expenditure = finance.get("exp_current_instruction_per_pupil")
            profile.rev_fed_total = finance.get("rev_fed_total")
            profile.rev_state_total = finance.get("rev_state_total")
            profile.rev_local_total = finance.get("rev_local_total")

        # 3. Enrollment / Demographics (Step 3 of blueprint)
        enrollment_data = self._fetch_enrollment(leaid, year)
        if enrollment_data:
            total = profile.total_enrollment or 1
            if isinstance(enrollment_data, list):
                for res in enrollment_data:
                    race = res.get("race")
                    count = res.get("enrollment")
                    if count is None: continue
                    
                    # Urban Institute Race Codes: 1=White, 2=Black, 3=Hispanic, 4=Asian
                    if race == 1: profile.enrollment_white_pct = (count / total) * 100
                    elif race == 2: profile.enrollment_black_pct = (count / total) * 100
                    elif race == 3: profile.enrollment_hispanic_pct = (count / total) * 100
                    elif race == 4: profile.enrollment_asian_pct = (count / total) * 100

        # 4. Special Groups (ELL / SpEd)
        # ELL is often in the directory as 'english_language_learners'
        return profile

    def _clean_name(self, name: str) -> str:
        """
        Strips trailing IDs in parentheses like '(4240)'
        """
        if not name:
            return ""
        import re
        return re.sub(r'\s*\(\d+\)\s*$', '', name).strip()

    def get_districts_by_state(self, state_code: str) -> List[Dict]:
        """
        Fetch all districts for a given state for autocomplete.
        """
        state_fips = STATE_FIPS.get(state_code.upper())
        if not state_fips:
            return []

        districts = []
        year = LATEST_NCES_YEAR
        url = f"{self.BASE_URL}/school-districts/ccd/directory/{year}/?fips={state_fips}&per_page=1000"
        
        try:
            page = 1
            while url:
                logger.info(f"Fetching page {page} of districts for state FIPS {state_fips}")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                
                for res in results:
                    raw_name = res.get("lea_name", "")
                    districts.append({
                        "id": res.get("leaid"),
                        "name": self._clean_name(raw_name)
                    })
                
                url = data.get("next")
                page += 1
                # Hard cap at 5 pages (5000 districts) to prevent infinite loops/timeout issues
                if page > 5:
                    break
        except Exception as e:
            logger.error(f"Error fetching districts by state: {e}")
            
        # Fallback if Urban Institute API is down or times out
        if not districts:
            logger.warning(f"Using fallback district list for state {state_code} due to empty API response")
            if state_code.upper() == "CA":
                districts = [
                    {"id": "0000001", "name": "Los Angeles Unified"},
                    {"id": "0000002", "name": "San Diego Unified"},
                    {"id": "0000003", "name": "Fresno Unified"},
                    {"id": "0000004", "name": "Long Beach Unified"},
                    {"id": "0000005", "name": "San Francisco Unified"},
                    {"id": "demo_usd", "name": "Demo Unified School District"}
                ]
            elif state_code.upper() == "TX":
                 districts = [
                    {"id": "0000006", "name": "Houston ISD"},
                    {"id": "0000007", "name": "Dallas ISD"},
                    {"id": "0000008", "name": "Cypress-Fairbanks ISD"}
                ]
            elif state_code.upper() == "NY":
                 districts = [
                    {"id": "0000009", "name": "New York City Public Schools"},
                    {"id": "0000010", "name": "Buffalo Public Schools"}
                ]
            else:
                 districts = [
                    {"id": "demo_usd", "name": f"Demo District ({state_code.upper()})"}
                ]
            
        # Sort districts alphabetically by name
        districts.sort(key=lambda x: x['name'])
        return districts

    def _fetch_directory(self, name: str, state_fips: str) -> Optional[Dict]:
        for year in range(LATEST_NCES_YEAR, LATEST_NCES_YEAR - 3, -1):
            url = f"{self.BASE_URL}/school-districts/ccd/directory/{year}/?district_name={name}&fips={state_fips}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                results = response.json().get("results", [])
                if results:
                    for res in results:
                        if name.lower() == res.get("lea_name", "").lower():
                            return res
                    return results[0]
            except Exception as e:
                logger.error(f"Error fetching directory ({year}): {e}")
        return None

    def _fetch_finance(self, leaid: str, year: int) -> Optional[Dict]:
        # Finance often lags directory by significant time
        for y in range(year, year - 6, -1):
            url = f"{self.BASE_URL}/school-districts/ccd/finance/{y}/?leaid={leaid}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                results = response.json().get("results", [])
                if results:
                    logger.info(f"Found finance data for year {y}")
                    return results[0]
            except Exception:
                continue
        return None

    def _fetch_enrollment(self, leaid: str, year: int) -> Optional[Dict]:
        url = f"{self.BASE_URL}/school-districts/ccd/enrollment/{year}/?leaid={leaid}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            results = response.json().get("results", [])
            return results[0] if results else None
        except Exception:
            return None
