"""Deduplication utilities for L1 Collectors (V1A L1)."""

import hashlib
from api.store import list_sources


def compute_dedupe_hash(platform: str, platform_skill_id: str) -> str:
    """计算去重哈希。
    
    Args:
        platform: 平台名（github/doubao/...）
        platform_skill_id: 平台原始 ID
        
    Returns:
        去重哈希字符串（格式：platform:platform_skill_id）
    """
    return f"{platform}:{platform_skill_id}"


def is_duplicate(platform: str, platform_skill_id: str) -> bool:
    """检查是否已存在（去重）。
    
    Args:
        platform: 平台名
        platform_skill_id: 平台原始 ID
        
    Returns:
        True 如果已存在（重复）
    """
    dedupe_hash = compute_dedupe_hash(platform, platform_skill_id)
    existing_sources = list_sources()
    
    for source in existing_sources:
        if source.dedupe_hash == dedupe_hash:
            return True
    
    return False
