#!/usr/bin/env python3
"""
GreenClose Database Layer
Uses a local JSON file for MVP (no Supabase setup needed yet).
Designed so Supabase can be dropped in later without changing callers.
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

DB_FILE = Path(__file__).parent.parent / "data" / "jobs.json"


class Database:
    def __init__(self):
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not DB_FILE.exists():
            DB_FILE.write_text(json.dumps({"jobs": {}, "stats": {"total_jobs": 0, "revenue": 0}}))

    def _read(self) -> Dict:
        return json.loads(DB_FILE.read_text())

    def _write(self, data: Dict):
        DB_FILE.write_text(json.dumps(data, indent=2))

    async def save_job(self, job: Dict[str, Any]):
        data = self._read()
        data["jobs"][job["id"]] = job
        data["stats"]["total_jobs"] = len(data["jobs"])
        self._write(data)

    async def update_job_status(self, job_id: str, status: str, **kwargs):
        data = self._read()
        if job_id in data["jobs"]:
            data["jobs"][job_id]["status"] = status
            data["jobs"][job_id]["updated_at"] = datetime.utcnow().isoformat()
            for k, v in kwargs.items():
                data["jobs"][job_id][k] = v
        self._write(data)

    async def get_job(self, job_id: str) -> Optional[Dict]:
        data = self._read()
        return data["jobs"].get(job_id)

    async def get_all_jobs(self) -> Dict:
        return self._read()["jobs"]

    async def get_stats(self) -> Dict:
        data = self._read()
        jobs = data["jobs"]
        delivered = [j for j in jobs.values() if j.get("status") == "delivered"]
        pending = [j for j in jobs.values() if j.get("status") in ("pending", "generating")]
        return {
            "total_jobs": len(jobs),
            "delivered": len(delivered),
            "pending": len(pending),
            "revenue_usd": data["stats"].get("revenue", 0),
        }

    async def record_payment(self, job_id: str, amount: float):
        data = self._read()
        if job_id in data["jobs"]:
            data["jobs"][job_id]["paid"] = True
            data["jobs"][job_id]["amount_paid"] = amount
        data["stats"]["revenue"] = data["stats"].get("revenue", 0) + amount
        self._write(data)


db = Database()
