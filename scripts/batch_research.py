"""
CLI batch research runner.

Usage:
  python scripts/batch_research.py --list                    # preview targets
  python scripts/batch_research.py --limit 10 --product moodle_lms
  python scripts/batch_research.py --limit 50 --min-profiles 3 --product moodle_lms

Already-researched districts are skipped automatically, so re-running
continues where the last batch left off. Results persist to research_results
(sync to HubSpot afterwards with: python hubspot_import.py --all-unsynced).
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser(description="Batch AI research over top ICP districts")
    parser.add_argument("--list", action="store_true", help="Preview targets without researching")
    parser.add_argument("--limit", type=int, default=10, help="Number of districts (default 10)")
    parser.add_argument("--min-profiles", type=int, default=1, help="Minimum ICP profiles matched (default 1)")
    parser.add_argument("--product", help="Product template slug (see /api/templates)")
    parser.add_argument("--delay", type=int, default=20, help="Seconds between districts (default 20)")
    args = parser.parse_args()

    from batch_runner import get_targets, runner

    if args.list:
        targets = get_targets(min_profiles=args.min_profiles, limit=args.limit)
        print(f"Next {len(targets)} targets (min {args.min_profiles} profiles, already-researched skipped):\n")
        for i, t in enumerate(targets, 1):
            print(f"{i:3}. [{t['profile_count']}] {t['dist_name']} — {t['profile_tags']}")
        return

    if not args.product:
        sys.exit("--product is required (a template slug, e.g. moodle_lms). Use --list to preview targets.")

    result = runner.start(args.product, limit=args.limit,
                          min_profiles=args.min_profiles, delay_seconds=args.delay)
    if "error" in result:
        sys.exit(f"Error: {result['error']}")

    print(f"Batch started: {len(result['targets'])} districts. Ctrl-C to stop after current district.\n")
    try:
        while runner.state == "running":
            s = runner.status()
            line = f"[{s['done']}/{s['total']}] current: {s['current'] or '—'}"
            print(line.ljust(80), end="\r")
            time.sleep(5)
    except KeyboardInterrupt:
        runner.stop()
        print("\nStopping after current district...")
        while runner.state != "idle":
            time.sleep(2)

    s = runner.status()
    print(f"\nDone: {len(s['completed'])} researched, {len(s['errors'])} errors")
    for c in s["completed"]:
        print(f"  ✓ {c['district']} (score {c.get('icp_score')}, {c['seconds']}s)")
    for e in s["errors"]:
        print(f"  ✗ {e['district']}: {e['error']}")
    if s["completed"]:
        print("\nSync to HubSpot: python hubspot_import.py --all-unsynced")


if __name__ == "__main__":
    main()
