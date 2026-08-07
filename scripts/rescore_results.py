"""
Post-hoc rescore: add the funding-fit component to saved research results.

Needed for dossiers created before funding fit was part of the scoring engine
(the score stored with them counts only live-scraped signals). Idempotent:
results already carrying a funding_fit_applied marker are skipped.

Usage: python scripts/rescore_results.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import SessionLocal
from models.research_result import ResearchResultModel
from analysis.scoring import ScoringEngine


def main():
    engine = ScoringEngine()
    db = SessionLocal()
    updated = 0
    try:
        for r in db.query(ResearchResultModel).all():
            data = dict(r.profile_data or {})
            meta = data.get("metadata") or {}
            if meta.get("funding_fit_applied"):
                continue
            points = ScoringEngine.funding_fit_points(
                meta.get("funding_profile"),
                data.get("title_i_eligible"),
                "preferred",  # matches the shipped product profile's preference
            )
            if points == 0:
                continue
            old = r.icp_score or 0
            new = min(100, old + points)
            r.icp_score = new
            r.signal_strength = engine.get_signal_strength(new)
            r.recommended_action = engine.get_recommended_action(new)
            data["icp_score"] = new
            data["signal_strength"] = r.signal_strength
            data["recommended_action"] = r.recommended_action
            meta["funding_fit_applied"] = True
            data["metadata"] = meta
            r.profile_data = data
            print(f"{r.district_name}: {old} -> {new} ({r.signal_strength}, {r.recommended_action})")
            updated += 1
        db.commit()
    finally:
        db.close()
    print(f"\nRescored {updated} result(s).")


if __name__ == "__main__":
    main()
