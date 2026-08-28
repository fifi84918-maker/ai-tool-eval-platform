"""Base interfaces for source collectors (V1A PRD 11.1)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class RawSourceCandidate:
    """Raw source candidate from platform discovery.
    
    Contains metadata only (no code content) for source_records insertion.
    """
    platform_object_id: str  # e.g., "owner/repo" for GitHub
    skill_name: str
    raw_description: str
    author: str
    origin_url: str
    visibility: str  # "public", "private"
    license: str  # SPDX identifier or "unknown"
    default_branch: str
    raw_payload: dict  # Original API response snapshot


class SourceCollector(ABC):
    """Abstract base class for platform-specific source collectors.
    
    Implementations discover AI Skill candidates from various platforms
    (GitHub, HuggingFace, WorkBuddy, etc.) and fetch their metadata.
    
    This is metadata-only discovery (PRD D-003):
    - No code download
    - No content_hash calculation
    - acquired=False (left for pipeline stage 29.2)
    """
    
    platform: str  # e.g., "github", "huggingface"
    
    @abstractmethod
    async def discover(self, query: str = "", limit: int = 50) -> list[RawSourceCandidate]:
        """Discover source candidates matching query.
        
        Args:
            query: Search query (platform-specific semantics)
            limit: Max candidates to return
            
        Returns:
            List of raw source candidates (metadata only)
            
        Raises:
            CollectorError: On unrecoverable errors (auth failure, rate limit)
        """
        pass
    
    @abstractmethod
    async def fetch_metadata(self, platform_object_id: str) -> Optional[RawSourceCandidate]:
        """Fetch metadata for a known platform object.
        
        Args:
            platform_object_id: Platform-specific object identifier
            
        Returns:
            RawSourceCandidate or None if not found
            
        Raises:
            CollectorError: On unrecoverable errors
        """
        pass


class CollectorError(Exception):
    """Base exception for collector errors."""
    pass


class RateLimitError(CollectorError):
    """Raised when rate limit is hit (429)."""
    pass


class AuthenticationError(CollectorError):
    """Raised when authentication fails (401/403)."""
    pass


@dataclass
class IngestReport:
    """Report of ingestion operation results."""
    created: int = 0  # New source_records created
    updated: int = 0  # Existing source_records updated
    skipped: int = 0  # Candidates skipped (error/duplicate)
    warnings: list[str] = None  # Warning messages
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
