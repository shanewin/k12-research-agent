"""
Local funding enrichment from the FundFinder dataset.

Loads data/ca_district_funding_full.csv (edfinr + Urban Institute educationdata
+ California CDE data: LCFF, FRPM, ELPAC, CAASPP, chronic absenteeism) and
enriches DistrictProfile with funding intelligence the NCES API cannot provide.

Currently California-only — the CDE columns (LCFF, FRPM, ELPAC) only exist for
CA. The edfinr pipeline in the fund-finder repo documents how to generate the
national base for other states.
"""

import csv
import logging
import os
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ca_district_funding_full.csv")

# CSV columns surfaced verbatim into profile.metadata["funding_profile"]
FUNDING_METADATA_COLS = [
    "rev_total_pp", "rev_fed_pp", "rev_state_pp", "rev_local_pp",
    "mhi", "stpov_pct", "ba_plus_pct", "urbanicity", "county",
    "title_i_amount", "frpm_pct", "frpm_count",
    "lcff_supplemental", "lcff_concentration", "lcff_supp_conc_total", "lcff_unduplicated_pct",
    "ela_proficient_pct", "chronic_absent_rate",
    "csi_school_count", "atsi_school_count", "tsi_school_count", "has_improvement_status",
    "sped_enroll", "ell_enroll", "total_teachers_fte", "counselors_fte", "website",
    "profile_count", "profile_tags",
]


# --- Target Profiles (ported from an earlier client engagement) ---
# Six named strategic ICPs. Each is a data rule mapping to a specific sales
# pitch and funding angle; districts matching multiple profiles are hot accounts.

PROFILE_DEFINITIONS = [
    {
        "name": "State Money + Literacy Gap", "label": "LCFF+ELA", "key": "profile_lcff_ela",
        "rule": "Receives over $1M in LCFF supplemental/concentration funding AND fewer than half of students read at grade level.",
        "angle": "They have extra state money earmarked for high-need students, and the need is visible in their reading scores. The funding source and the problem line up.",
    },
    {
        "name": "EL Pipeline Problem", "label": "EL Pipeline", "key": "profile_el_pipeline",
        "rule": "500+ English learners (15%+ of enrollment), with 20%+ stuck at beginning ELPAC proficiency and under 25% reaching well-developed.",
        "angle": "A large EL population that isn't progressing. Title III and LCFF dollars specifically fund tools that help these students.",
    },
    {
        "name": "Mandated to Improve", "label": "Improv.", "key": "profile_improvement",
        "rule": "Has schools in state/federal improvement status (CSI, ATSI, or TSI).",
        "angle": "These districts are required to show improvement and must publish plans for how. Urgency is built in.",
    },
    {
        "name": "Title I Heavyweight", "label": "Title I", "key": "profile_title_i",
        "rule": "Title I funding is at least 3% of total revenue AND fewer than half of students read at grade level.",
        "angle": "Title I is a meaningful slice of their budget, not a rounding error — and supplemental instruction is exactly what Title I pays for.",
    },
    {
        "name": "Disengagement Crisis", "label": "Absence", "key": "profile_absence",
        "rule": "Chronic absenteeism above 25% AND fewer than half of students read at grade level.",
        "angle": "A quarter of students regularly missing school compounds the achievement gap. Engagement-focused tools speak directly to this.",
    },
    {
        "name": "SPED/Dyslexia Gap", "label": "SPED", "key": "profile_sped",
        "rule": "1,000+ special education students (12%+ of enrollment) AND fewer than 45% of students read at grade level.",
        "angle": "A large SPED population with IEP goals to document. IDEA Part B funds progress-monitoring and intervention tools.",
    },
]


def _compute_profiles(row: dict) -> dict:
    """Tag one district row with the target profiles it matches."""
    def n(col, default):
        v = _num(row.get(col))
        return v if v is not None else default

    p = {}
    # 1. State Money + Literacy Gap: big LCFF supp/conc money, low reading scores
    p["profile_lcff_ela"] = int(n("lcff_supp_conc_total", 0) > 1_000_000 and n("ela_proficient_pct", 100) < 50)
    # 2. EL Pipeline Problem: large EL population stuck at beginning proficiency
    p["profile_el_pipeline"] = int(
        n("ell_enroll", 0) > 500 and n("ell_pct", 0) > 0.15
        and n("elpac_beginning_pct", 0) > 20 and n("elpac_well_developed_pct", 100) < 25)
    # 3. Mandated to Improve: has schools in CSI/ATSI/TSI status
    p["profile_improvement"] = int(n("has_improvement_status", 0) == 1)
    # 4. Title I Heavyweight: Title I >= 3% of total revenue + low reading scores
    rev_total = n("rev_total", 0)
    t1_pct = (n("title_i_amount", 0) / rev_total) if rev_total else 0
    p["profile_title_i"] = int(t1_pct >= 0.03 and n("ela_proficient_pct", 100) < 50)
    # 5. Disengagement Crisis: high chronic absenteeism + low reading scores
    p["profile_absence"] = int(n("chronic_absent_rate", 0) > 25 and n("ela_proficient_pct", 100) < 50)
    # 6. SPED/Dyslexia Gap: large SPED population + very low reading scores
    p["profile_sped"] = int(n("sped_enroll", 0) > 1000 and n("sped_pct", 0) > 0.12 and n("ela_proficient_pct", 100) < 45)

    p["profile_count"] = sum(p[d["key"]] for d in PROFILE_DEFINITIONS)
    p["profile_tags"] = " · ".join(d["name"] for d in PROFILE_DEFINITIONS if p[d["key"]]) or "—"
    return p


def _norm_name(name: str) -> str:
    """Normalize district names for fuzzy matching across data sources."""
    n = (name or "").lower().strip()
    n = re.sub(r"\b(school district|unified school district|public schools|schools|district|elementary|union|joint)\b", "", n)
    return re.sub(r"[^a-z0-9]", "", n)


def _num(val) -> Optional[float]:
    try:
        f = float(val)
        return f if f >= 0 else None  # CCD uses negative codes for "not available"
    except (TypeError, ValueError):
        return None


class LocalFundingData:
    _rows_by_id: Dict[str, dict] = None
    _rows_by_name: Dict[str, dict] = None

    @classmethod
    def _load(cls):
        if cls._rows_by_id is not None:
            return
        cls._rows_by_id, cls._rows_by_name = {}, {}
        if not os.path.exists(CSV_PATH):
            logger.warning("Local funding CSV not found; enrichment disabled")
            return
        with open(CSV_PATH, newline="") as f:
            for row in csv.DictReader(f):
                row.update(_compute_profiles(row))
                leaid = (row.get("ncesid") or "").strip()
                if leaid:
                    cls._rows_by_id[leaid] = row
                key = _norm_name(row.get("dist_name", ""))
                if key:
                    cls._rows_by_name[key] = row
        logger.info(f"Loaded {len(cls._rows_by_id)} districts from local funding dataset")

    @classmethod
    def lookup(cls, nces_id: Optional[str] = None, district_name: Optional[str] = None,
               state: Optional[str] = None) -> Optional[dict]:
        cls._load()
        if state and state.upper() != "CA":
            return None  # dataset is CA-only for now
        if nces_id and nces_id in cls._rows_by_id:
            return cls._rows_by_id[nces_id]
        if district_name:
            return cls._rows_by_name.get(_norm_name(district_name))
        return None

    @classmethod
    def enrich_profile(cls, profile) -> bool:
        """Fill DistrictProfile gaps + attach the full funding intelligence block.
        Returns True if a match was found."""
        row = cls.lookup(nces_id=profile.nces_id, district_name=profile.district_name,
                         state=profile.state)
        if not row:
            return False

        # Fill core fields only where the live pipeline left gaps
        if not profile.nces_id:
            profile.nces_id = row.get("ncesid")
        if not profile.county:
            profile.county = row.get("county")
        if not profile.total_enrollment:
            profile.total_enrollment = int(_num(row.get("enroll")) or 0) or None
        if not profile.number_of_schools:
            sc = _num(row.get("school_count"))
            profile.number_of_schools = int(sc) if sc else None
        if not profile.locale_type or profile.locale_type == "Unknown":
            profile.locale_type = row.get("urbanicity") or profile.locale_type
        if not profile.total_revenue:
            profile.total_revenue = _num(row.get("rev_total"))
        if not profile.rev_fed_total:
            profile.rev_fed_total = _num(row.get("rev_fed"))
        if not profile.rev_state_total:
            profile.rev_state_total = _num(row.get("rev_state"))
        if not profile.rev_local_total:
            profile.rev_local_total = _num(row.get("rev_local"))
        if not profile.per_pupil_expenditure:
            profile.per_pupil_expenditure = _num(row.get("exp_cur_pp"))
        if profile.ell_pct is None:
            profile.ell_pct = _num(row.get("ell_pct"))
        if profile.sped_pct is None:
            profile.sped_pct = _num(row.get("sped_pct"))
        if profile.free_reduced_lunch_pct is None:
            profile.free_reduced_lunch_pct = _num(row.get("frpm_pct"))
        if profile.title_i_eligible is None:
            t1 = _num(row.get("title_i_amount"))
            profile.title_i_eligible = bool(t1 and t1 > 0)
        if not profile.website_url and row.get("website"):
            profile.website_url = row["website"]

        # Full funding intelligence block (incl. CA-only LCFF/CDE data)
        profile.metadata["funding_profile"] = {
            col: row.get(col) for col in FUNDING_METADATA_COLS if row.get(col) not in (None, "", "NA")
        }
        profile.metadata["funding_profile"]["source"] = (
            "FundFinder dataset (NCES F-33 + SAIPE + ACS via edfinr; CCD via educationdata; CA CDE: LCFF/FRPM/ELPAC/CAASPP), FY2022"
        )
        logger.info(f"Enriched {profile.district_name} from local funding dataset")
        return True
