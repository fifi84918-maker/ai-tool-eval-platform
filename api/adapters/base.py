"""Source Adapter Base Protocol for L1 Collectors (V1A L1)."""

from typing import Protocol, runtime_checkable
from api.models import CanonicalSkill, SourceRecord, ArtifactRecord


@runtime_checkable
class SourceAdapter(Protocol):
    """源适配器协议：定义采集器的统一接口。
    
    每个平台（GitHub/豆包/千问等）实现此协议。
    """
    platform: str
    
    def discover(self, query: str, limit: int = 20) -> list[SourceRecord]:
        """发现候选技能（仅元数据阶段）。
        
        Args:
            query: 搜索关键词
            limit: 最大返回数量
            
        Returns:
            SourceRecord 列表（尚未创建 CanonicalSkill）
        """
        ...
    
    def fetch(self, source: SourceRecord) -> tuple[CanonicalSkill, list[ArtifactRecord]]:
        """获取完整技能内容并构造规范化模型。
        
        Args:
            source: 源记录
            
        Returns:
            (CanonicalSkill, ArtifactRecord 列表)
            CanonicalSkill.state 应为 "ACQUIRED"
        """
        ...
