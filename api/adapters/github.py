"""GitHub Source Adapter for L1 Collectors (V1A L1)."""

import hashlib
import uuid
import os
import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone
from typing import Protocol
from api.models import CanonicalSkill, SourceRecord, ArtifactRecord
from api.adapters.dedup import compute_dedupe_hash, is_duplicate


class GitHubFetcher(Protocol):
    """GitHub API 抽象（可注入 fake 实现用于测试）。"""
    
    def search(self, query: str, limit: int = 20) -> list[dict]:
        """搜索仓库。
        
        Returns:
            list of {repo_full_name, description, html_url, license: {spdx_id}, topics: [...]}
        """
        ...
    
    def get_skill_md(self, repo_full_name: str) -> str | None:
        """获取 SKILL.md 内容。
        
        Returns:
            SKILL.md 文本内容，或 None（不存在）
        """
        ...


class FakeGitHubFetcher:
    """测试用假 fetcher（不联网）。"""
    
    def search(self, query: str, limit: int = 20) -> list[dict]:
        """返回模拟搜索结果。"""
        return [{
            "repo_full_name": "acme/demo-skill",
            "description": "Processes PDF and Word documents with python",
            "html_url": "https://github.com/acme/demo-skill",
            "license": {"spdx_id": "MIT"},
            "topics": ["documentation", "pdf"],
        }]
    
    def get_skill_md(self, repo_full_name: str) -> str | None:
        """返回模拟 SKILL.md 内容。"""
        if repo_full_name == "acme/demo-skill":
            return """---
name: PDF Processor
description: Process PDF/Word docs
allowed-tools: [read, write]
---

# PDF Processor

This skill processes PDF and Word documents.
"""
        return None


class GitHubAdapter:
    """GitHub 来源适配器。"""
    
    platform = "github"
    
    def __init__(self, fetcher: GitHubFetcher | None = None):
        """初始化适配器。
        
        Args:
            fetcher: 可注入的 fetcher（默认用 FakeGitHubFetcher）
        """
        self.fetcher = fetcher or FakeGitHubFetcher()
        self._item_cache: dict[str, dict] = {}  # Cache for search results
    
    def _cache_item(self, repo_full_name: str, item: dict) -> None:
        """缓存搜索结果项用于 fetch。"""
        self._item_cache[repo_full_name] = item
    
    def _get_cached_item(self, repo_full_name: str) -> dict | None:
        """获取缓存的搜索结果项。"""
        return self._item_cache.get(repo_full_name)
    
    def discover(self, query: str, limit: int = 20) -> list[SourceRecord]:
        """发现候选技能（创建 DISCOVERED 状态的 CanonicalSkill）。
        
        Args:
            query: 搜索关键词
            limit: 最大返回数量
            
        Returns:
            SourceRecord 列表（去重后）
        """
        from api.store import put_skill
        
        results = self.fetcher.search(query, limit)
        
        sources = []
        for item in results:
            repo_full_name = item["repo_full_name"]
            
            # 去重检查
            if is_duplicate(self.platform, repo_full_name):
                continue
            
            # Store raw item data for fetch() to use
            self._cache_item(repo_full_name, item)
            
            # 构造 SourceRecord
            source = SourceRecord(
                source_id=str(uuid.uuid4()),
                platform=self.platform,
                platform_skill_id=repo_full_name,
                fetched_at=datetime.now(timezone.utc),
                raw_url=item["html_url"],
                dedupe_hash=compute_dedupe_hash(self.platform, repo_full_name),
                canonical_skill_id=None  # 将在下面回填
            )
            
            # 计算 skill_id
            skill_id = hashlib.sha256(f"github:{repo_full_name}".encode()).hexdigest()
            
            # 创建 DISCOVERED 状态的 CanonicalSkill
            skill = CanonicalSkill(
                skill_id=skill_id,
                name=item.get("name", repo_full_name.split("/")[-1]),
                description=item.get("description", ""),
                platform=self.platform,
                platform_skill_id=repo_full_name,
                state="DISCOVERED",
                source_refs=[source.source_id],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                # 默认值
                target_domains=[],
                required_languages=[],
                security_level="lax",
                high_risk=False,
                state_history=[],
                artifact_refs=[],
            )
            
            # 存储 skill
            put_skill(skill)
            
            # 回填 source 的 canonical_skill_id
            source.canonical_skill_id = skill_id
            
            sources.append(source)
        
        return sources
    
    def fetch(self, source: SourceRecord) -> tuple[CanonicalSkill, list[ArtifactRecord]]:
        """获取完整技能内容，从 DISCOVERED 转换到 ACQUIRED。
        
        Args:
            source: 源记录
            
        Returns:
            (CanonicalSkill, ArtifactRecord 列表)
        """
        from api.store import get_skill, put_skill, put_artifact, transition_state
        
        repo_full_name = source.platform_skill_id
        
        # 1. 计算 skill_id
        skill_id = self._compute_skill_id(repo_full_name)
        
        # 2. 从 store 取已有的 DISCOVERED skill
        skill = get_skill(skill_id)
        if skill is None:
            raise ValueError(f"Skill {skill_id} not found. Call discover() first.")
        if skill.state != "DISCOVERED":
            raise ValueError(f"Skill {skill_id} is in state {skill.state}, expected DISCOVERED")
        
        # 3. 获取 SKILL.md
        skill_md_content = self.fetcher.get_skill_md(repo_full_name)
        if skill_md_content is None:
            skill_md_content = ""
        
        # 4. 解析 SKILL.md（获取更完整的信息）
        cached_item = self._get_cached_item(repo_full_name)
        metadata = self._parse_skill_md(skill_md_content, cached_item)
        
        # 5. 更新 skill 字段（用解析后的更完整信息）
        skill.name = metadata["name"]
        skill.description = metadata["description"]
        skill.license = metadata["license"]
        skill.target_domains = metadata["target_domains"]
        skill.required_languages = metadata["required_languages"]
        put_skill(skill)
        
        # 6. transition 到 ACQUIRED
        transition_state(skill_id, "ACQUIRED", reason=f"Fetched SKILL.md from GitHub: {repo_full_name}")
        
        # 7. 刷新 skill（获取更新后的状态）
        skill = get_skill(skill_id)
        
        # 8. 构造 ArtifactRecord
        artifact = ArtifactRecord(
            artifact_id=str(uuid.uuid4()),
            skill_id=skill_id,
            kind="skill_md",
            path_or_text=skill_md_content,
            created_at=datetime.now(timezone.utc)
        )
        put_artifact(artifact)
        
        # 9. 更新 skill 的 artifact_refs
        skill.artifact_refs.append(artifact.artifact_id)
        put_skill(skill)
        
        return (skill, [artifact])
    
    def _compute_skill_id(self, repo_full_name: str) -> str:
        """计算 skill_id（SHA256 hex）。
        
        Args:
            repo_full_name: 仓库全名（owner/repo）
            
        Returns:
            64 字符 SHA256 hex
        """
        content = f"github:{repo_full_name}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _parse_skill_md(self, content: str, cached_item: dict | None = None) -> dict:
        """解析 SKILL.md 内容。
        
        Args:
            content: SKILL.md 文本
            cached_item: 缓存的搜索结果（含 license/topics/description）
            
        Returns:
            {name, description, license, target_domains, required_languages}
        """
        metadata = {
            "name": "Unknown Skill",
            "description": "",
            "license": "UNKNOWN",
            "target_domains": [],
            "required_languages": [],
        }
        
        # 从 cached_item 提取 license 和 topics
        if cached_item:
            # Extract license
            license_info = cached_item.get("license")
            if license_info and isinstance(license_info, dict):
                spdx_id = license_info.get("spdx_id")
                if spdx_id:
                    metadata["license"] = spdx_id
            
            # Extract domains from topics
            topics = cached_item.get("topics", [])
            known_domains = ["documentation", "file-processing", "data", "web", "api", "pdf"]
            for domain in known_domains:
                if domain in topics or domain.replace("-", "") in topics:
                    metadata["target_domains"].append(domain)
        
        # 尝试解析 frontmatter
        if content.startswith("---"):
            lines = content.split("\n")
            in_frontmatter = True
            frontmatter_lines = []
            
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    break
                frontmatter_lines.append(line)
            
            # 简单 key: value 解析
            for line in frontmatter_lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == "name":
                        metadata["name"] = value
                    elif key == "description":
                        metadata["description"] = value
        
        # 如果没有 description，从全文提取第一段
        if not metadata["description"]:
            lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#") and not l.startswith("---")]
            if lines:
                metadata["description"] = lines[0][:200]
        
        # 如果还是没有 description，用 cached_item 的 description
        if not metadata["description"] and cached_item:
            metadata["description"] = cached_item.get("description", "")
        
        # 从内容中提取额外的 domains（补充 topics）
        content_lower = content.lower()
        known_domains = ["documentation", "file-processing", "data", "web", "api", "pdf"]
        for domain in known_domains:
            if domain not in metadata["target_domains"]:
                if domain in content_lower or domain.replace("-", " ") in content_lower:
                    metadata["target_domains"].append(domain)
        
        # 从内容中提取 languages（简单关键词匹配）
        known_languages = ["python", "javascript", "typescript", "go", "java", "rust"]
        for lang in known_languages:
            if lang in content_lower:
                metadata["required_languages"].append(lang)
        
        return metadata


class RealGitHubFetcher:
    """真实 GitHub API 实现。"""
    
    def __init__(self, token: str = None):
        """初始化 GitHub API fetcher。
        
        Args:
            token: GitHub personal access token (optional, reads from GITHUB_TOKEN env var)
            
        Raises:
            ValueError: If token not provided and GITHUB_TOKEN not set
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise ValueError(
                "GITHUB_TOKEN environment variable not set. "
                "Please set it with: export GITHUB_TOKEN=your_token_here"
            )
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ai-tool-eval-platform",
        }
    
    def search(self, query: str, limit: int = 20) -> list[dict]:
        """调用 GitHub Search API 搜索仓库。
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of repository dicts matching GitHubFetcher protocol
        """
        # Encode query
        encoded = urllib.parse.quote(f"{query} skill")
        url = f"https://api.github.com/search/repositories?q={encoded}&sort=stars&per_page={limit}"
        
        # Make request
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if hasattr(e, "read") else ""
            raise RuntimeError(f"GitHub API error: {e.code} {e.reason}. {error_body}")
        
        # Transform to expected format
        results = []
        for item in data.get("items", []):
            repo_full_name = f"{item['owner']['login']}/{item['name']}"
            
            results.append({
                "repo_full_name": repo_full_name,
                "description": item.get("description", ""),
                "html_url": item["html_url"],
                "license": {"spdx_id": item["license"]["spdx_id"]} if item.get("license") else None,
                "topics": item.get("topics", []),
            })
        
        return results
    
    def get_skill_md(self, repo_full_name: str) -> str | None:
        """从 GitHub raw 读取 SKILL.md 内容。
        
        Args:
            repo_full_name: Repository full name (owner/repo)
            
        Returns:
            SKILL.md content or None if not found
        """
        # Try main branch first
        branches = ["main", "master"]
        
        for branch in branches:
            url = f"https://raw.githubusercontent.com/{repo_full_name}/{branch}/SKILL.md"
            req = urllib.request.Request(url, headers=self.headers)
            
            try:
                with urllib.request.urlopen(req) as resp:
                    return resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # Try next branch
                    continue
                else:
                    # Other error, raise
                    raise RuntimeError(f"GitHub raw file error: {e.code} {e.reason}")
        
        # Not found in any branch
        return None

