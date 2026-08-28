"""GitHub source collector implementation."""
import json, logging, os, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from collector.base import RawSourceCandidate, SourceCollector, IngestReport, RateLimitError, AuthenticationError, CollectorError
from db.repository import SourceRepository
logger = logging.getLogger(__name__)
class GitHubCollector(SourceCollector):
    platform = "github"
    API_BASE = "https://api.github.com"
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
    def _build_headers(self):
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "AI-Skill-Eval-Platform/1.0"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    def _make_request(self, url, retry_on_rate_limit=True):
        headers = self._build_headers()
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", 60))
                if retry_on_rate_limit and retry_after <= 120:
                    time.sleep(retry_after)
                    return self._make_request(url, False)
                raise RateLimitError("Rate limit exceeded")
            elif e.code in (401, 403):
                raise AuthenticationError("GitHub API auth failed")
            elif e.code == 404:
                return None
            raise CollectorError(f"HTTP {e.code}")
        except urllib.error.URLError as e:
            raise CollectorError(f"Network error")
    async def discover(self, query="", limit=50):
        q = (query + " " if query else "") + "filename:SKILL.md"
        params = urllib.parse.urlencode({"q": q, "per_page": min(limit, 100), "sort": "updated"})
        url = f"{self.API_BASE}/search/repositories?{params}"
        try:
            response = self._make_request(url)
            if not response:
                return []
            items = response.get("items", [])
            return [self._parse_repository(item) for item in items[:limit]]
        except (RateLimitError, AuthenticationError, CollectorError):
            return []
    async def fetch_metadata(self, platform_object_id):
        url = f"{self.API_BASE}/repos/{platform_object_id}"
        try:
            response = self._make_request(url)
            return self._parse_repository(response) if response else None
        except (RateLimitError, AuthenticationError, CollectorError):
            return None
    def _parse_repository(self, repo_data):
        license_info = repo_data.get("license")
        license_spdx = "unknown"
        if license_info and isinstance(license_info, dict):
            license_spdx = license_info.get("spdx_id", "unknown")
            if license_spdx in ("NOASSERTION", "NONE", None):
                license_spdx = "unknown"
        owner = repo_data.get("owner", {})
        author = owner.get("login", "unknown") if isinstance(owner, dict) else "unknown"
        visibility = "public" if not repo_data.get("private", False) else "private"
        return RawSourceCandidate(
            platform_object_id=repo_data.get("full_name", ""),
            skill_name=repo_data.get("name", ""),
            raw_description=repo_data.get("description") or "",
            author=author,
            origin_url=repo_data.get("html_url", ""),
            visibility=visibility,
            license=license_spdx,
            default_branch=repo_data.get("default_branch", "main"),
            raw_payload=repo_data,
        )
async def ingest_from_github(query, limit, session):
    collector = GitHubCollector()
    report = IngestReport()
    try:
        candidates = await collector.discover(query, limit)
        if not candidates:
            report.warnings.append("No repositories found")
            return report
        repo = SourceRepository(session)
        for candidate in candidates:
            try:
                source_id = f"github::{candidate.platform_object_id}"
                existing = repo.get_by_platform_object("github", candidate.platform_object_id)
                repo.upsert_by_platform("github", candidate.platform_object_id, id=source_id, skill_name=candidate.skill_name, raw_description=candidate.raw_description, author=candidate.author, origin_url=candidate.origin_url, visibility=candidate.visibility, license=candidate.license, acquired=False, raw_payload=candidate.raw_payload, discovered_at=datetime.utcnow())
                if existing:
                    report.updated += 1
                else:
                    report.created += 1
            except Exception as e:
                report.skipped += 1
        session.commit()
    except Exception as e:
        session.rollback()
    return report