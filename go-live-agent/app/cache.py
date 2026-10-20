from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

CACHE_DIR = Path("/app/.cache")
TTL_SECONDS = 86400  # 24 horas


def _cache_path(engagement_id: int, findings_hash: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"report_{engagement_id}_{findings_hash}.json"


def findings_hash(findings: list) -> str:
    parts = sorted(
        f"{f.id}:{f.severity}:{f.active}:{f.verified}:{f.risk_accepted}:{f.false_positive}"
        for f in findings
    )
    return hashlib.md5("|".join(parts).encode()).hexdigest()[:12]


def get(engagement_id: int, fhash: str) -> dict | None:
    path = _cache_path(engagement_id, fhash)
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > TTL_SECONDS:
        path.unlink(missing_ok=True)
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def set(engagement_id: int, fhash: str, report_dict: dict) -> None:
    try:
        path = _cache_path(engagement_id, fhash)
        path.write_text(json.dumps(report_dict), encoding="utf-8")
    except Exception as e:
        print(f"[CACHE] Error guardando caché: {e}")


def invalidate(engagement_id: int) -> None:
    try:
        for f in CACHE_DIR.glob(f"report_{engagement_id}_*.json"):
            f.unlink(missing_ok=True)
    except Exception:
        pass
