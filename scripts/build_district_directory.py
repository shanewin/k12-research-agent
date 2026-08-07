"""
Build data/ca_district_directory.csv — mailing address, phone, and location
for every California district, from the NCES/CCD directory (public, free).

These are the firmographics HubSpot expects on a company record (address,
city, zip, phone), which the funding dataset doesn't carry.

Usage: python scripts/build_district_directory.py
"""

import csv
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import STATE_FIPS, LATEST_NCES_YEAR  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ca_district_directory.csv")
BASE_URL = "https://educationdata.urban.org/api/v1/school-districts/ccd/directory"

FIELDS = ["leaid", "name", "street", "city", "state", "zip", "phone",
          "county", "latitude", "longitude", "number_of_schools", "state_leaid"]


def fetch_state(fips: str) -> list:
    rows, url = [], f"{BASE_URL}/{LATEST_NCES_YEAR}/?fips={fips}&per_page=1000"
    while url:
        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                break
            except Exception as e:
                print(f"  retry {attempt + 1}: {e}")
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError("directory fetch failed after 3 attempts")
        data = resp.json()
        for r in data.get("results", []):
            zip5 = str(r.get("zip_mailing") or r.get("zip_location") or "").strip()
            rows.append({
                "leaid": r.get("leaid"),
                "name": r.get("lea_name"),
                "street": r.get("street_mailing") or r.get("street_location") or "",
                "city": r.get("city_mailing") or r.get("city_location") or "",
                "state": r.get("state_mailing") or r.get("state_location") or "",
                "zip": zip5.zfill(5) if zip5.isdigit() else zip5,
                "phone": r.get("phone") or "",
                "county": r.get("county_name") or "",
                "latitude": r.get("latitude") or "",
                "longitude": r.get("longitude") or "",
                "number_of_schools": r.get("number_of_schools") or "",
                "state_leaid": r.get("state_leaid") or "",
            })
        url = data.get("next")
    return rows


def main():
    fips = STATE_FIPS["CA"]
    print(f"Fetching CA district directory (FIPS {fips}, year {LATEST_NCES_YEAR})...")
    rows = fetch_state(fips)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["name"] or ""))
    with_phone = sum(1 for r in rows if r["phone"])
    with_street = sum(1 for r in rows if r["street"])
    print(f"{len(rows)} districts -> {OUT_PATH}")
    print(f"  with phone: {with_phone} | with street address: {with_street}")


if __name__ == "__main__":
    main()
