"""Source Record Model for L2 Data Layer (V1A L2)."""

from datetime import datetime
from pydantic import BaseModel


class SourceRecord(BaseModel):
    """源记录：记录从外部平台获取的原始技能信息。
    
    用于去重和追溯。
    """
    source_id: str                    # Unique ID for this source record
    platform: str                     # Platform name (github/doubao/etc)
    platform_skill_id: str            # Platform-specific skill ID
    fetched_at: datetime             # When this was fetched
    raw_url: str                      # Original URL
    dedupe_hash: str                  # Hash for deduplication (platform + platform_skill_id)
    canonical_skill_id: str | None = None  # Link to CanonicalSkill after normalization
    
    model_config = {"from_attributes": True}
