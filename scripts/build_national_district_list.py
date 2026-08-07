"""
One-time builder for data/districts_national.csv — the offline fallback for
district autocomplete when the Urban Institute API is slow or down.

Pulls the CCD directory for every state from the Education Data Portal API
(the same source the live autocomplete uses) and writes: state,leaid,name

Usage:  python scripts/build_national_district_list.py
Re-run any time to refresh; already-fetched states are skipped unless --force.
"""

import csv
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import STATE_FIPS, LATEST_NCES_YEAR  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "districts_national.csv")
BASE_URL = "https://educationdata.urban.org/api/v1/school-districts/ccd/directory"


def clean_name(name: str) -> str:
    import re
    return re.sub(r"\s*\(\d+\)\s*$", "", name or "").strip()


def fetch_state(state: str, fips: str) -> list:
    rows = []
    url = f"{BASE_URL}/{LATEST_NCES_YEAR}/?fips={fips}&per_page=1000"
    while url:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        for res in data.get("results", []):
            name = clean_name(res.get("lea_name", ""))
            leaid = res.get("leaid")
            if name and leaid:
                rows.append((state, leaid, name))
        url = data.get("next")
    return rows


def main():
    force = "--force" in sys.argv
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    done_states = set()
    existing = []
    if os.path.exists(OUT_PATH) and not force:
        with open(OUT_PATH, newline="") as f:
            for row in csv.reader(f):
                if row and row[0] != "state":
                    existing.append(row)
                    done_states.add(row[0])

    all_rows = existing
    for state, fips in sorted(STATE_FIPS.items()):
        if state in done_states:
            print(f"{state}: already fetched, skipping")
            continue
        for attempt in range(3):
            try:
                rows = fetch_state(state, fips)
                all_rows.extend(rows)
                print(f"{state}: {len(rows)} districts")
                break
            except Exception as e:
                print(f"{state}: attempt {attempt + 1} failed ({e})")
                time.sleep(5 * (attempt + 1))
        else:
            print(f"{state}: FAILED after 3 attempts — re-run script to retry")

        # Write incrementally so partial progress survives interruption
        with open(OUT_PATH, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["state", "leaid", "name"])
            w.writerows(sorted(all_rows))

    print(f"\nTotal: {len(all_rows)} districts -> {OUT_PATH}")


if __name__ == "__main__":
    main()
