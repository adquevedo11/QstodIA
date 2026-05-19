from __future__ import annotations

import httpx
from app.domain.models import Finding


SEVERITY_MAP = {
    "critical": "Critical", "crítico": "Critical",
    "high": "High", "alto": "High",
    "medium": "Medium", "medio": "Medium",
    "low": "Low", "bajo": "Low",
    "info": "Info", "informational": "Info",
}


class DefectDojoClient:

    def __init__(self, base_url: str, api_token: str, write_enabled: bool = False):
        self.base_url = base_url.rstrip("/")
        self.write_enabled = write_enabled
        self._headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
        }

    def get_product(self, product_id: int) -> dict:
        return self._get(f"/api/v2/products/{product_id}/")

    def get_engagement(self, engagement_id: int) -> dict:
        return self._get(f"/api/v2/engagements/{engagement_id}/")

    def list_findings(self, engagement_id: int) -> list[Finding]:
        data = self._get(f"/api/v2/findings/?test__engagement={engagement_id}&limit=500")
        results = data.get("results", [])
        print(f"[DefectDojo] Engagement {engagement_id}: {len(results)} hallazgos obtenidos")
        return [self._map_finding(f) for f in results]

    def add_finding_note(self, finding_id: int, note: str) -> None:
        if not self.write_enabled:
            print(f"[DRY-RUN] Agregaría nota al finding {finding_id}: {note[:80]}...")
            return
        self._post(f"/api/v2/findings/{finding_id}/notes/", {"entry": note})

    def add_finding_tags(self, finding_id: int, tags: list[str]) -> None:
        if not self.write_enabled:
            print(f"[DRY-RUN] Agregaría tags al finding {finding_id}: {tags}")
            return
        self._post(f"/api/v2/findings/{finding_id}/tags/", {"tags": tags})

    def upload_engagement_report(self, engagement_id: int, file_path: str) -> None:
        if not self.write_enabled:
            print(f"[DRY-RUN] Subiría reporte al engagement {engagement_id}: {file_path}")
            return
        with open(file_path, "rb") as f:
            httpx.post(
                f"{self.base_url}/api/v2/engagements/{engagement_id}/files/",
                headers={"Authorization": self._headers["Authorization"]},
                files={"file": f},
            ).raise_for_status()

    def _get(self, path: str) -> dict:
        resp = httpx.get(f"{self.base_url}{path}", headers=self._headers, timeout=30, verify=False)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        resp = httpx.post(f"{self.base_url}{path}", headers=self._headers, json=data, timeout=30, verify=False)
        resp.raise_for_status()
        return resp.json()

    def _map_finding(self, raw: dict) -> Finding:
        severity_raw = (raw.get("severity") or "Info").lower()
        severity = SEVERITY_MAP.get(severity_raw, "Info")

        tags = raw.get("tags", [])
        if isinstance(tags, list):
            tags = [str(t) for t in tags]
        else:
            tags = []

        return Finding(
            id=str(raw.get("id", "")),
            title=raw.get("title", "Sin título"),
            severity=severity,
            status=raw.get("status", "Active"),
            component=raw.get("component_name"),
            business_flow=None,
            cwe=str(raw.get("cwe")) if raw.get("cwe") else None,
            cvss_score=raw.get("cvssv3_score"),
            description=raw.get("description"),
            mitigation=raw.get("mitigation"),
            evidence=raw.get("references"),
            active=raw.get("active", True),
            verified=raw.get("verified", False),
            false_positive=raw.get("false_p", False),
            risk_accepted=raw.get("risk_accepted", False),
            tags=tags,
        )
