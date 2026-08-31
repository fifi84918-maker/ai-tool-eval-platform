"""GitHub Source Adapter for L1 Collectors (V1A L1)."""

import hashlib
import uuid
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
    
    def discover(self, query: str, limit: int = 20) -> list[SourceRecord]:
        """发现候选技能（仅元数据）。
        
        Args:
            query: 搜索关键词
            limit: 最大返回数量
            
        Returns:
            SourceRecord 列表（去重后）
        """
        results = self.fetcher.search(query, limit)
        
        sources = []
        for item in results:
            repo_full_name = item["repo_full_name"]
            
            # 去重检查
            if is_duplicate(self.platform, repo_full_name):
                continue
            
            # 构造 SourceRecord
            source = SourceRecord(
                source_id=str(uuid.uuid4()),
                platform=self.platform,
                platform_skill_id=repo_full_name,
                fetched_at=datetime.now(timezone.utc),
                raw_url=item["html_url"],
                dedupe_hash=compute_dedupe_hash(self.platform, repo_full_name),
                canonical_skill_id=None  # 尚未关联
            )
            sources.append(source)
        
        return sources
    
    def fetch(self, source: SourceRecord) -> tuple[CanonicalSkill, list[ArtifactRecord]]:
        """获取完整技能内容并构造规范化模型。
        
        Args:
            source: 源记录
            
        Returns:
            (CanonicalSkill, ArtifactRecord 列表)
        """
        repo_full_name = source.platform_skill_id
        
        # 获取 SKILL.md
        skill_md_content = self.fetcher.get_skill_md(repo_full_name)
        if skill_md_content is None:
            skill_md_content = ""
        
        # 解析 SKILL.md
        metadata = self._parse_skill_md(skill_md_content, source.raw_url)
        
        # 构造 CanonicalSkill
        skill_id = self._compute_skill_id(repo_full_name)
        
        skill = CanonicalSkill(
            skill_id=skill_id,
            name=metadata["name"],
            description=metadata["description"],
            platform=self.platform,
            platform_skill_id=repo_full_name,
            license=metadata["license"],
            security_level="lax",  # 默认 lax，静态检测再定级
            high_risk=False,
            target_domains=metadata["target_domains"],
            required_languages=metadata["required_languages"],
            state="ACQUIRED",  # DISCOVERED → ACQUIRED
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            source_refs=[source.source_id],
        )
        
        # 构造 ArtifactRecord
        artifact = ArtifactRecord(
            artifact_id=str(uuid.uuid4()),
            skill_id=skill_id,
            kind="skill_md",
            path_or_text=skill_md_content,
            created_at=datetime.now(timezone.utc)
        )
        
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
    
    def _parse_skill_md(self, content: str, fallback_url: str) -> dict:
        """解析 SKILL.md 内容。
        
        Args:
            content: SKILL.md 文本
            fallback_url: 回退用的 URL（从 description 提取）
            
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
            lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
            if lines:
                metadata["description"] = lines[0][:200]
        
        # 从内容中提取 domains（简单关键词匹配）
        content_lower = content.lower()
        known_domains = ["documentation", "file-processing", "data", "web", "api", "pdf"]
        for domain in known_domains:
            if domain in content_lower or domain.replace("-", " ") in content_lower:
                metadata["target_domains"].append(domain)
        
        # 从内容中提取 languages（简单关键词匹配）
        known_languages = ["python", "javascript", "typescript", "go", "java", "rust"]
        for lang in known_languages:
            if lang in content_lower:
                metadata["required_languages"].append(lang)
        
        return metadata
