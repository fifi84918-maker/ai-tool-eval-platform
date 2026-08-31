"""Artifact Record Model for L2 Data Layer (V1A L2)."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel


ArtifactKind = Literal[
    "skill_md",       # skill.md 文件
    "repo_zip",       # 仓库压缩包
    "scan_report",    # 静态扫描报告
    "sandbox_log",    # 沙箱执行日志
    "score_json"      # 评分结果
]


class ArtifactRecord(BaseModel):
    """制品记录：存储技能相关的文件和报告。
    
    可以是文本（path_or_text 直接存内容）或路径（存文件路径）。
    """
    artifact_id: str                  # Unique ID for this artifact
    skill_id: str                     # Link to CanonicalSkill
    kind: ArtifactKind                # Type of artifact
    path_or_text: str                 # File path or inline text content
    created_at: datetime             # When this was created
    
    model_config = {"from_attributes": True}
