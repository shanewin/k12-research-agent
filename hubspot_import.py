"""
HubSpot Lead Importer for the K12 Research Agent.

Pushes researched district profiles into HubSpot as Companies (districts)
and Contacts (decision-makers), with associations and custom intelligence
properties (ICP score, signal strength, SIS/LMS, job-change signal, etc.).

Sources:
  - The local research_results table in k12_research.db (default), or
  - A raw DistrictProfile JSON file exported by the agent.

Usage:
  python hubspot_import.py --setup                 # one-time: create custom properties
  python hubspot_import.py --list                  # show saved research runs
  python hubspot_import.py --result-id 1           # import one saved run
  python hubspot_import.py --all-unsynced          # import every run not yet synced
  python hubspot_import.py --json profile.json     # import from a JSON export
  python hubspot_import.py --result-id 1 --dry-run # preview without writing

Auth: set HUBSPOT_ACCESS_TOKEN in .env (a Private App token with
crm.objects.companies + crm.objects.contacts + crm.schemas read/write scopes).
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("hubspot-import")

HUBSPOT_BASE = "https://api.hubapi.com"
TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN")

# --- Custom properties this pipeline maintains in HubSpot ---

COMPANY_PROPERTIES = [
    {"name": "k12_icp_score", "label": "K12 ICP Score", "type": "number", "fieldType": "number"},
    {"name": "k12_signal_strength", "label": "K12 Signal Strength", "type": "enumeration", "fieldType": "select",
     "options": [{"label": s, "value": s} for s in ["LOW", "MEDIUM", "HIGH"]]},
    {"name": "k12_recommended_action", "label": "K12 Recommended Action", "type": "string", "fieldType": "text"},
    # hasUniqueValue makes this usable as the idProperty for batch upserts
    {"name": "k12_nces_id", "label": "NCES District ID", "type": "string", "fieldType": "text",
     "hasUniqueValue": True},
    {"name": "k12_total_enrollment", "label": "Total Enrollment", "type": "number", "fieldType": "number"},
    {"name": "k12_sis", "label": "Incumbent SIS", "type": "string", "fieldType": "text"},
    {"name": "k12_lms", "label": "Incumbent LMS", "type": "string", "fieldType": "text"},
    {"name": "k12_ecosystem", "label": "Ecosystem (Google/Microsoft)", "type": "string", "fieldType": "text"},
    {"name": "k12_intelligence_brief", "label": "Intelligence Brief", "type": "string", "fieldType": "textarea"},
]

# Funding-intelligence properties (from the FundFinder CA dataset)
FUNDING_COMPANY_PROPERTIES = [
    {"name": "k12_enrollment", "label": "Enrollment", "type": "number", "fieldType": "number"},
    {"name": "k12_county", "label": "County", "type": "string", "fieldType": "text"},
    {"name": "k12_urbanicity", "label": "Urbanicity", "type": "string", "fieldType": "text"},
    {"name": "k12_poverty_pct", "label": "Student Poverty %", "type": "number", "fieldType": "number"},
    {"name": "k12_frpm_pct", "label": "Free/Reduced Meals %", "type": "number", "fieldType": "number"},
    {"name": "k12_ell_pct", "label": "English Learner %", "type": "number", "fieldType": "number"},
    {"name": "k12_sped_pct", "label": "SPED %", "type": "number", "fieldType": "number"},
    {"name": "k12_fed_rev_per_pupil", "label": "Federal Revenue $/Pupil", "type": "number", "fieldType": "number"},
    {"name": "k12_total_rev", "label": "Total Revenue", "type": "number", "fieldType": "number"},
    {"name": "k12_title_i_amount", "label": "Title I Amount ($)", "type": "number", "fieldType": "number"},
    {"name": "k12_lcff_supp_conc", "label": "LCFF Supplemental+Concentration ($)", "type": "number", "fieldType": "number"},
    {"name": "k12_ela_proficient_pct", "label": "ELA Proficient %", "type": "number", "fieldType": "number"},
    {"name": "k12_chronic_absent_rate", "label": "Chronic Absenteeism %", "type": "number", "fieldType": "number"},
    {"name": "k12_school_count", "label": "School Count", "type": "number", "fieldType": "number"},
    {"name": "k12_icp_profile_count", "label": "ICP Profiles Matched", "type": "number", "fieldType": "number"},
    {"name": "k12_icp_profile_tags", "label": "ICP Target Profiles", "type": "string", "fieldType": "text"},
]

CONTACT_PROPERTIES = [
    {"name": "k12_district", "label": "K12 District", "type": "string", "fieldType": "text"},
    {"name": "k12_tenure_months", "label": "Tenure (Months)", "type": "number", "fieldType": "number"},
    {"name": "k12_job_change_signal", "label": "New-in-Role Signal (<24mo)", "type": "enumeration",
     "fieldType": "booleancheckbox",
     "options": [{"label": "Yes", "value": "true"}, {"label": "No", "value": "false"}]},
    {"name": "k12_source", "label": "Lead Source Detail", "type": "string", "fieldType": "text"},
]


class HubSpotClient:
    """Thin wrapper around the HubSpot CRM v3 API with retry on rate limits."""

    def __init__(self, token: str, dry_run: bool = False):
        self.dry_run = dry_run
        # Dry-run without a real token: skip even read calls so previews work offline
        self.offline = dry_run and (not token or token == "dry-run")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs) -> Optional[dict]:
        if self.offline:
            return {"results": []}
        url = f"{HUBSPOT_BASE}{path}"
        for attempt in range(4):
            resp = self.session.request(method, url, timeout=30, **kwargs)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 10))
                logger.warning(f"Rate limited by HubSpot; sleeping {wait}s...")
                time.sleep(wait)
                continue
            if resp.status_code >= 400:
                raise RuntimeError(f"HubSpot {method} {path} failed ({resp.status_code}): {resp.text[:300]}")
            return resp.json() if resp.text else {}
        raise RuntimeError(f"HubSpot {method} {path}: exhausted retries on rate limit")

    # --- Properties ---

    def ensure_property(self, object_type: str, prop: dict):
        try:
            self._request("GET", f"/crm/v3/properties/{object_type}/{prop['name']}")
            logger.info(f"  Property {object_type}.{prop['name']} already exists")
        except RuntimeError:
            body = {**prop, "groupName": f"{object_type}information"}
            if self.dry_run:
                logger.info(f"  [dry-run] Would create property {object_type}.{prop['name']}")
                return
            self._request("POST", f"/crm/v3/properties/{object_type}", json=body)
            logger.info(f"  Created property {object_type}.{prop['name']}")

    # --- Search ---

    def search(self, object_type: str, prop: str, value: str) -> Optional[str]:
        """Returns the id of the first object where prop == value, else None."""
        body = {
            "filterGroups": [{"filters": [{"propertyName": prop, "operator": "EQ", "value": value}]}],
            "limit": 1,
        }
        data = self._request("POST", f"/crm/v3/objects/{object_type}/search", json=body)
        results = data.get("results", [])
        return results[0]["id"] if results else None

    # --- Upserts ---

    def upsert(self, object_type: str, search_prop: str, search_value: str, properties: dict) -> Optional[str]:
        existing_id = self.search(object_type, search_prop, search_value) if search_value else None
        if self.dry_run:
            action = "update" if existing_id else "create"
            logger.info(f"  [dry-run] Would {action} {object_type}: {json.dumps(properties, default=str)[:200]}")
            return existing_id or "dry-run-id"
        if existing_id:
            self._request("PATCH", f"/crm/v3/objects/{object_type}/{existing_id}", json={"properties": properties})
            logger.info(f"  Updated {object_type} {existing_id}")
            return existing_id
        data = self._request("POST", f"/crm/v3/objects/{object_type}", json={"properties": properties})
        logger.info(f"  Created {object_type} {data['id']}")
        return data["id"]

    def find_contact_by_name(self, first: str, last: str, district: str) -> Optional[str]:
        """Dedup fallback for contacts with no email: firstname+lastname+district."""
        body = {
            "filterGroups": [{"filters": [
                {"propertyName": "firstname", "operator": "EQ", "value": first},
                {"propertyName": "lastname", "operator": "EQ", "value": last},
                {"propertyName": "k12_district", "operator": "EQ", "value": district},
            ]}],
            "limit": 1,
        }
        data = self._request("POST", "/crm/v3/objects/contacts/search", json=body)
        results = data.get("results", [])
        return results[0]["id"] if results else None

    def upsert_by_id(self, object_type: str, object_id: Optional[str], properties: dict) -> Optional[str]:
        if self.dry_run:
            action = "update" if object_id else "create"
            logger.info(f"  [dry-run] Would {action} {object_type}: {json.dumps(properties, default=str)[:200]}")
            return object_id or "dry-run-id"
        if object_id:
            self._request("PATCH", f"/crm/v3/objects/{object_type}/{object_id}", json={"properties": properties})
            logger.info(f"  Updated {object_type} {object_id}")
            return object_id
        data = self._request("POST", f"/crm/v3/objects/{object_type}", json={"properties": properties})
        logger.info(f"  Created {object_type} {data['id']}")
        return data["id"]

    def associate_contact_to_company(self, contact_id: str, company_id: str):
        if self.dry_run:
            logger.info(f"  [dry-run] Would associate contact {contact_id} -> company {company_id}")
            return
        path = f"/crm/v4/objects/contacts/{contact_id}/associations/default/companies/{company_id}"
        self._request("PUT", path)

    def create_company_note(self, company_id: str, body_html: str):
        """Attach a note to a company (used for drafted outreach sequences)."""
        if self.dry_run:
            logger.info(f"  [dry-run] Would attach note ({len(body_html)} chars) to company {company_id}")
            return
        from datetime import datetime, timezone
        note = self._request("POST", "/crm/v3/objects/notes", json={"properties": {
            "hs_note_body": body_html[:65000],
            "hs_timestamp": datetime.now(timezone.utc).isoformat(),
        }})
        self._request("PUT", f"/crm/v4/objects/notes/{note['id']}/associations/default/companies/{company_id}")


# --- Mapping: DistrictProfile dict -> HubSpot records ---

def district_domain(profile: dict) -> str:
    url = profile.get("website_url") or ""
    return urlparse(url).netloc.replace("www.", "") if url else ""


def split_name(full_name: str):
    clean = re.sub(r"^(Dr|Mr|Mrs|Ms|Prof)\.?\s+", "", (full_name or "").strip())
    parts = clean.split()
    if not parts:
        return "", ""
    return parts[0], " ".join(parts[1:]) or "-"


def company_payload(profile: dict) -> dict:
    props = {
        "name": profile.get("district_name"),
        "state": profile.get("state"),
        "city": profile.get("city") or "",
        "website": profile.get("website_url") or "",
        "domain": district_domain(profile),
        "industry": "EDUCATION_MANAGEMENT",
        "k12_icp_score": profile.get("icp_score") or 0,
        "k12_signal_strength": profile.get("signal_strength") or "LOW",
        "k12_recommended_action": profile.get("recommended_action") or "",
        "k12_nces_id": profile.get("nces_id") or "",
        "k12_sis": profile.get("sis") or "Unknown",
        "k12_lms": profile.get("lms") or "Unknown",
        "k12_ecosystem": profile.get("ecosystem") or "Unknown",
        "k12_intelligence_brief": (profile.get("intelligence_brief") or "")[:5000],
    }
    if profile.get("total_enrollment"):
        props["k12_total_enrollment"] = profile["total_enrollment"]
    return {k: v for k, v in props.items() if v not in (None, "")}


def contact_payload(contact: dict, profile: dict) -> dict:
    first, last = split_name(contact.get("name", ""))
    props = {
        "firstname": first,
        "lastname": last,
        "jobtitle": contact.get("title") or "",
        "email": (contact.get("email") or "").lower(),
        "phone": contact.get("phone") or "",
        "company": profile.get("district_name") or "",
        "k12_district": profile.get("district_name") or "",
        "k12_source": contact.get("source") or "k12-research-agent",
        "k12_job_change_signal": "true" if contact.get("is_new") else "false",
    }
    if contact.get("linkedin_url"):
        props["hs_linkedin_url"] = contact["linkedin_url"]
    if contact.get("tenure_months") is not None:
        props["k12_tenure_months"] = contact["tenure_months"]
    return {k: v for k, v in props.items() if v not in (None, "")}


# --- Import flows ---

def import_profile(client: HubSpotClient, profile: dict, skip_no_email: bool = False) -> Dict:
    """Import one DistrictProfile dict: upsert company, contacts, associations."""
    name = profile.get("district_name", "Unknown District")
    logger.info(f"Importing district: {name}")

    # Dedup precedence: NCES ID (unique property, matches the bulk CSV import)
    # -> website domain -> district name.
    payload = company_payload(profile)
    if profile.get("nces_id"):
        search_prop, search_value = ("k12_nces_id", profile["nces_id"])
    else:
        domain = district_domain(profile)
        search_prop, search_value = ("domain", domain) if domain else ("name", name)
    company_id = client.upsert("companies", search_prop, search_value, payload)

    contacts = profile.get("contacts") or []
    imported, skipped = 0, 0
    for contact in contacts:
        if not contact.get("name"):
            skipped += 1
            continue
        email = (contact.get("email") or "").lower()
        if not email and skip_no_email:
            logger.info(f"  Skipping {contact['name']} (no email)")
            skipped += 1
            continue
        payload = contact_payload(contact, profile)
        if email:
            # Email is the reliable dedup key
            contact_id = client.upsert("contacts", "email", email, payload)
        else:
            # No email: dedup on exact name within this district before creating
            contact_id = client.find_contact_by_name(payload.get("firstname", ""),
                                                     payload.get("lastname", ""), name)
            contact_id = client.upsert_by_id("contacts", contact_id, payload)
        if contact_id and company_id:
            client.associate_contact_to_company(contact_id, company_id)
        imported += 1

    # Drafted outreach sequence -> a note on the company record
    outreach = profile.get("outreach") or {}
    notes_created = 0
    if outreach.get("emails") and company_id:
        lines = [f"<strong>Drafted outreach sequence — {name}</strong> (AI-generated, review before sending)<br><br>"]
        for e in outreach["emails"]:
            lines.append(
                f"<strong>Email {e.get('sequence_number')}: {e.get('subject_line')}</strong><br>"
                f"<em>Angle: {e.get('profile')} · Funding: {e.get('funding_source')}</em><br>"
                f"{(e.get('body') or '').replace(chr(10), '<br>')}<br><br>"
            )
        client.create_company_note(company_id, "".join(lines))
        notes_created = 1

    logger.info(f"Done: {name} — company synced, {imported} contacts imported, {skipped} skipped"
                + (", outreach note attached" if notes_created else ""))
    return {"company_id": company_id, "contacts_imported": imported,
            "contacts_skipped": skipped, "outreach_notes": notes_created}


def _csv_num(val, pct_scale=False):
    try:
        f = float(val)
        if f < 0:
            return None
        return round(f, 2)
    except (TypeError, ValueError):
        return None


def funding_company_payload(row: dict) -> dict:
    """Map one ca_district_funding_full.csv row to HubSpot company properties."""
    website = (row.get("website") or "").strip()
    domain = ""
    if website:
        from urllib.parse import urlparse
        parsed = urlparse(website if "//" in website else f"https://{website}")
        domain = parsed.netloc.replace("www.", "")
    props = {
        "name": row.get("dist_name"),
        "state": "CA",
        "industry": "EDUCATION_MANAGEMENT",
        "website": website,
        "domain": domain,
        "k12_nces_id": row.get("ncesid") or "",
        "k12_county": row.get("county") or "",
        "k12_urbanicity": row.get("urbanicity") or "",
        "k12_enrollment": _csv_num(row.get("enroll")),
        "k12_poverty_pct": _csv_num((_csv_num(row.get("stpov_pct")) or 0) * 100),
        "k12_frpm_pct": _csv_num(row.get("frpm_pct")),
        "k12_ell_pct": _csv_num((_csv_num(row.get("ell_pct")) or 0) * 100),
        "k12_sped_pct": _csv_num((_csv_num(row.get("sped_pct")) or 0) * 100),
        "k12_fed_rev_per_pupil": _csv_num(row.get("rev_fed_pp")),
        "k12_total_rev": _csv_num(row.get("rev_total")),
        "k12_title_i_amount": _csv_num(row.get("title_i_amount")),
        "k12_lcff_supp_conc": _csv_num(row.get("lcff_supp_conc_total")),
        "k12_ela_proficient_pct": _csv_num(row.get("ela_proficient_pct")),
        "k12_chronic_absent_rate": _csv_num(row.get("chronic_absent_rate")),
        "k12_school_count": _csv_num(row.get("school_count")),
        "k12_icp_profile_count": row.get("profile_count"),
        "k12_icp_profile_tags": row.get("profile_tags") if row.get("profile_tags") != "—" else "",
    }
    return {k: v for k, v in props.items() if v not in (None, "")}


def import_funding_csv(client: HubSpotClient, csv_path: str, limit: Optional[int] = None,
                       min_enrollment: int = 0) -> Dict:
    """Bulk-import districts from the FundFinder CSV as HubSpot companies.

    Uses HubSpot's batch upsert (100/request) keyed on the k12_nces_id
    property to make re-runs idempotent.
    """
    import csv as csv_mod
    from data_sources.local_funding import _compute_profiles

    with open(csv_path, newline="") as f:
        rows = [r for r in csv_mod.DictReader(f) if r.get("dist_name")]
    for r in rows:
        r.update(_compute_profiles(r))
    if min_enrollment:
        rows = [r for r in rows if (_csv_num(r.get("enroll")) or 0) >= min_enrollment]
    if limit:
        rows = rows[:limit]

    logger.info(f"Importing {len(rows)} districts from {os.path.basename(csv_path)}...")
    created = 0
    for i in range(0, len(rows), 100):
        batch = rows[i:i + 100]
        inputs = [{
            "idProperty": "k12_nces_id",
            "id": r.get("ncesid"),
            "properties": funding_company_payload(r),
        } for r in batch if r.get("ncesid")]
        if client.dry_run:
            logger.info(f"  [dry-run] Would upsert batch of {len(inputs)} companies "
                        f"({inputs[0]['properties']['name']} ... {inputs[-1]['properties']['name']})")
        else:
            client._request("POST", "/crm/v3/objects/companies/batch/upsert", json={"inputs": inputs})
            logger.info(f"  Upserted {i + len(inputs)}/{len(rows)}")
        created += len(inputs)
    logger.info(f"Done: {created} companies upserted.")
    return {"companies": created}


def load_from_db(result_id: Optional[int] = None, all_unsynced: bool = False) -> List[tuple]:
    """Returns [(result_id, profile_dict)] from the local SQLite research_results table."""
    from database import SessionLocal
    from models.research_result import ResearchResultModel

    db = SessionLocal()
    try:
        q = db.query(ResearchResultModel)
        if result_id:
            q = q.filter(ResearchResultModel.id == result_id)
        elif all_unsynced:
            q = q.filter(ResearchResultModel.hubspot_synced == False)  # noqa: E712
        rows = q.all()
        return [(r.id, r.profile_data) for r in rows]
    finally:
        db.close()


def mark_synced(result_ids: List[int]):
    from database import SessionLocal
    from models.research_result import ResearchResultModel

    db = SessionLocal()
    try:
        db.query(ResearchResultModel).filter(ResearchResultModel.id.in_(result_ids)).update(
            {"hubspot_synced": True}, synchronize_session=False)
        db.commit()
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Import K12 research leads into HubSpot")
    parser.add_argument("--setup", action="store_true", help="Create the custom HubSpot properties (one-time)")
    parser.add_argument("--list", action="store_true", help="List saved research runs")
    parser.add_argument("--result-id", type=int, help="Import one saved research run by id")
    parser.add_argument("--all-unsynced", action="store_true", help="Import all runs not yet synced")
    parser.add_argument("--json", dest="json_file", help="Import from a DistrictProfile JSON export")
    parser.add_argument("--funding-csv", nargs="?", const="data/ca_district_funding_full.csv",
                        help="Bulk-import districts from the FundFinder funding CSV as companies "
                             "(default: data/ca_district_funding_full.csv)")
    parser.add_argument("--limit", type=int, help="Cap the number of districts imported from the CSV")
    parser.add_argument("--min-enrollment", type=int, default=0,
                        help="Skip districts below this enrollment when importing from CSV")
    parser.add_argument("--skip-no-email", action="store_true", help="Skip contacts that have no email address")
    parser.add_argument("--dry-run", action="store_true", help="Preview all writes without touching HubSpot")
    args = parser.parse_args()

    if args.list:
        for rid, profile in load_from_db():
            print(f"#{rid}: {profile.get('district_name')}, {profile.get('state')} "
                  f"(ICP {profile.get('icp_score')}, {len(profile.get('contacts') or [])} contacts)")
        return

    if not TOKEN and not args.dry_run:
        sys.exit("HUBSPOT_ACCESS_TOKEN is not set in .env — create a HubSpot Private App and add its token.")

    client = HubSpotClient(TOKEN or "dry-run", dry_run=args.dry_run)

    if args.setup:
        logger.info("Ensuring custom properties exist...")
        for prop in COMPANY_PROPERTIES + FUNDING_COMPANY_PROPERTIES:
            client.ensure_property("companies", prop)
        for prop in CONTACT_PROPERTIES:
            client.ensure_property("contacts", prop)
        logger.info("Property setup complete.")
        if not (args.result_id or args.all_unsynced or args.json_file or args.funding_csv):
            return

    if args.funding_csv:
        import_funding_csv(client, args.funding_csv, limit=args.limit,
                           min_enrollment=args.min_enrollment)
        return

    if args.json_file:
        with open(args.json_file) as f:
            import_profile(client, json.load(f), skip_no_email=args.skip_no_email)
        return

    rows = load_from_db(result_id=args.result_id, all_unsynced=args.all_unsynced)
    if not rows:
        sys.exit("No matching research results found. Run --list to see saved runs.")

    synced_ids = []
    for rid, profile in rows:
        try:
            import_profile(client, profile, skip_no_email=args.skip_no_email)
            synced_ids.append(rid)
        except Exception as e:
            logger.error(f"Failed to import result #{rid}: {e}")

    if synced_ids and not args.dry_run:
        mark_synced(synced_ids)
        logger.info(f"Marked results {synced_ids} as synced.")


if __name__ == "__main__":
    main()
