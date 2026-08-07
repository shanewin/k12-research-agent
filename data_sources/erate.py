import logging
import os
import requests
from typing import List, Optional
from models.erate import ErateReport, ErateFundingRequest

logger = logging.getLogger(__name__)


class ErateIntelligence:
    """
    E-Rate funding and RFP intelligence from USAC Open Data (Socrata).

    USAC datasets are keyed by BEN (Billed Entity Number), not NCES ID, so we
    first resolve the district's BEN by name+state via the C2 Budget dataset,
    then pull Form 471 funding requests (spending history + pending requests)
    and Form 470 postings (active RFPs / bidding intent).
    """

    # Current dataset IDs (verified 2026-08; USAC rotates these occasionally —
    # if everything starts returning not_found, re-check via
    # https://opendata.usac.org/api/views/metadata/v1)
    DS_C2_BUDGET = "https://opendata.usac.org/resource/6brt-5pbv.json"   # BEN lookup
    DS_FORM_471 = "https://opendata.usac.org/resource/qdmp-ygft.json"    # FRN status
    DS_FORM_470 = "https://opendata.usac.org/resource/jp7a-89nd.json"    # 470 basic info

    def __init__(self):
        self.headers = {}
        app_token = os.getenv("USAC_APP_TOKEN")
        if app_token and app_token != "optional":
            self.headers["X-App-Token"] = app_token

    def _get(self, url: str, params: dict) -> list:
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"USAC query failed ({resp.status_code}): {resp.text[:150]}")
                return []
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"USAC request error: {e}")
            return []

    def _resolve_ben(self, district_name: str, state: str = "CA") -> Optional[str]:
        """Find the district's Billed Entity Number by name."""
        name = district_name.upper().replace("'", "")
        # Try progressively looser name matches, preferring School District entities
        candidates = []
        for needle in [name, name.replace(" UNIFIED", "").replace(" ELEMENTARY", "").strip()]:
            rows = self._get(self.DS_C2_BUDGET, {
                "$where": f"upper(billed_entity_name) like '%{needle}%' AND state='{state.upper()}'",
                "$limit": 20,
            })
            if rows:
                candidates = rows
                break
        if not candidates:
            return None
        districts = [r for r in candidates if r.get("applicant_type") == "School District"]
        pick = (districts or candidates)[0]
        logger.info(f"E-Rate BEN resolved: {district_name} -> {pick.get('ben')} ({pick.get('billed_entity_name')})")
        return pick.get("ben")

    def get_district_erate_data(self, nces_id: str, district_name: str, state: str = "CA") -> ErateReport:
        report = ErateReport(status="searching")

        ben = self._resolve_ben(district_name, state)
        if not ben:
            report.status = "not_found"
            return report
        report.ben = ben

        all_requests = self._fetch_471(ben) + self._fetch_470(ben)
        if not all_requests:
            report.status = "not_found"
            return report

        report.funding_history = all_requests
        report.status = "complete"
        self._calculate_summary(report)
        return report

    def _fetch_471(self, ben: str) -> List[ErateFundingRequest]:
        rows = self._get(self.DS_FORM_471, {
            "$where": f"ben='{ben}'",
            "$order": "funding_year DESC",
            "$limit": 50,
        })
        out = []
        for item in rows:
            try:
                out.append(ErateFundingRequest(
                    funding_year=int(item.get("funding_year") or 0),
                    application_number=item.get("application_number", ""),
                    frn=item.get("funding_request_number", ""),
                    ben=item.get("ben", ""),
                    organization_name=item.get("organization_name", ""),
                    service_type=item.get("form_471_service_type_name", ""),
                    product_service_description=(item.get("narrative") or item.get("nickname") or "")[:500],
                    vendor_name=item.get("spin_name", ""),
                    total_cost=float(item.get("total_pre_discount_costs") or 0.0),
                    funding_commitment_request=float(item.get("funding_commitment_request") or 0.0),
                    status=item.get("form_471_frn_status_name", "Unknown"),
                    form_type="Form 471",
                ))
            except (TypeError, ValueError):
                continue
        return out

    def _fetch_470(self, ben: str) -> List[ErateFundingRequest]:
        rows = self._get(self.DS_FORM_470, {
            "$where": f"ben='{ben}'",
            "$order": "funding_year DESC",
            "$limit": 20,
        })
        out = []
        for item in rows:
            desc = item.get("category_one_description") or item.get("category_two_description") or ""
            try:
                out.append(ErateFundingRequest(
                    funding_year=int(item.get("funding_year") or 0),
                    application_number=item.get("application_number", ""),
                    frn="N/A (RFP Phase)",
                    ben=item.get("ben", ""),
                    organization_name=item.get("billed_entity_name", ""),
                    service_type=item.get("applicant_type", ""),
                    product_service_description=("RFP: " + (item.get("form_nickname") or "") + " " + desc)[:500],
                    vendor_name="N/A (Bidding)",
                    total_cost=0.0,
                    funding_commitment_request=0.0,
                    status="Active RFP",
                    form_type="Form 470",
                ))
            except (TypeError, ValueError):
                continue
        return out

    def _calculate_summary(self, report: ErateReport):
        latest_year = max((r.funding_year for r in report.funding_history), default=0)
        recent_cutoff = latest_year - 1
        total = 0.0
        rfps = 0
        pendings = 0
        vendors = set()

        for req in report.funding_history:
            if req.funding_year >= recent_cutoff:
                total += req.funding_commitment_request
            if req.form_type == "Form 470":
                rfps += 1
            if req.status.lower() in ["pending", "active rfp"]:
                pendings += 1
            if req.vendor_name and req.vendor_name != "N/A (Bidding)":
                vendors.add(req.vendor_name)

        report.total_funding_recent = total
        report.active_rfps_count = rfps
        report.pending_requests_count = pendings
        report.key_vendors = list(vendors)[:5]

        report.summary = (
            f"Identified {len(report.funding_history)} E-Rate records. "
            f"Funding requested for FY{recent_cutoff}+ totals ${total:,.2f}. "
        )
        if rfps > 0:
            report.summary += f"{rfps} Form 470 postings indicate competitive bidding activity."
        else:
            report.summary += "No recent Form 470 postings found."
