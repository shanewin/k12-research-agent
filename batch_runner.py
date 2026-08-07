"""
Batch research runner (ported from an earlier client engagement).

Runs the full AI research pipeline over the top ICP-targeted California
districts, in priority order (most profiles matched, then federal $/pupil).
Each completed district is persisted to the research_results table, ready
for `hubspot_import.py --all-unsynced`.

Used by the /api/batch/* endpoints and scripts/batch_research.py.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

LOG_DIR = os.path.join(os.path.dirname(__file__), "data", "batch_logs")


def get_targets(min_profiles: int = 1, limit: int = 10, skip_researched: bool = True) -> List[Dict]:
    """Top targeted CA districts, priority-ordered. Skips already-researched by default."""
    from data_sources.local_funding import LocalFundingData

    LocalFundingData._load()
    rows = [r for r in LocalFundingData._rows_by_id.values()
            if r.get("profile_count", 0) >= min_profiles]

    def fed_pp(r):
        try:
            return float(r.get("rev_fed_pp") or 0)
        except ValueError:
            return 0.0

    rows.sort(key=lambda r: (-r["profile_count"], -fed_pp(r)))

    if skip_researched:
        from database import SessionLocal
        from models.research_result import ResearchResultModel
        db = SessionLocal()
        try:
            done = {name.lower() for (name,) in db.query(ResearchResultModel.district_name)
                    .filter(ResearchResultModel.state == "CA").all()}
        finally:
            db.close()
        rows = [r for r in rows if r["dist_name"].lower() not in done]

    return rows[:limit]


class BatchRunner:
    """Singleton sequential batch runner. One batch at a time."""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = False
        self.reset()

    def reset(self):
        self.state = "idle"          # idle | running | stopping
        self.queue: List[str] = []
        self.current: Optional[str] = None
        self.completed: List[Dict] = []
        self.errors: List[Dict] = []
        self.started_at: Optional[str] = None
        self.product_type: Optional[str] = None

    def status(self) -> Dict:
        return {
            "state": self.state,
            "product_type": self.product_type,
            "started_at": self.started_at,
            "current": self.current,
            "queued": self.queue,
            "completed": self.completed,
            "errors": self.errors,
            "done": len(self.completed) + len(self.errors),
            "total": len(self.completed) + len(self.errors) + len(self.queue) + (1 if self.current else 0),
        }

    def start(self, product_type: str, limit: int = 10, min_profiles: int = 1,
              delay_seconds: int = 20) -> Dict:
        with self._lock:
            if self.state == "running":
                return {"error": "A batch is already running"}
            targets = get_targets(min_profiles=min_profiles, limit=limit)
            if not targets:
                return {"error": "No unresearched districts match the criteria"}
            self.reset()
            self.state = "running"
            self.product_type = product_type
            self.started_at = datetime.now().isoformat(timespec="seconds")
            self.queue = [t["dist_name"] for t in targets]
            self._stop = False
            self._thread = threading.Thread(
                target=self._run, args=(product_type, delay_seconds), daemon=True)
            self._thread.start()
            return {"started": True, "targets": self.queue}

    def stop(self) -> Dict:
        if self.state == "running":
            self.state = "stopping"
            self._stop = True
        return {"state": self.state}

    def _run(self, product_type: str, delay_seconds: int):
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, f"batch_{self.started_at.replace(':', '-')}.jsonl")

        from database import SessionLocal
        from models.template import ProductTemplateModel
        from config.product_context import ProductContext
        from agent import K12ResearchAgent

        db = SessionLocal()
        try:
            template = db.query(ProductTemplateModel).filter(
                ProductTemplateModel.slug == product_type).first()
        finally:
            db.close()
        if not template:
            self.errors.append({"district": None, "error": f"Unknown product type: {product_type}"})
            self.state = "idle"
            return

        context = ProductContext(**template.context_data)

        while self.queue and not self._stop:
            name = self.queue.pop(0)
            self.current = name
            started = time.time()
            entry = {"district": name, "started_at": datetime.now().isoformat(timespec="seconds")}
            try:
                agent = K12ResearchAgent(context)
                profile = agent.research_district(name, "CA")
                from main import save_research_result
                result_id = save_research_result(profile, product_type)
                entry.update({"status": "ok", "result_id": result_id,
                              "icp_score": profile.icp_score,
                              "signal_strength": profile.signal_strength,
                              "seconds": round(time.time() - started)})
                self.completed.append(entry)
                logger.info(f"Batch: {name} done (score {profile.icp_score}) in {entry['seconds']}s")
            except Exception as e:
                entry.update({"status": "error", "error": str(e),
                              "seconds": round(time.time() - started)})
                self.errors.append(entry)
                logger.error(f"Batch: {name} failed: {e}")
            finally:
                self.current = None
                with open(log_path, "a") as f:
                    f.write(json.dumps(entry) + "\n")

            if self.queue and not self._stop:
                time.sleep(delay_seconds)  # spread out LLM/search API load

        self.state = "idle"
        logger.info(f"Batch finished: {len(self.completed)} ok, {len(self.errors)} errors")


runner = BatchRunner()
