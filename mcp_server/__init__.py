"""mcp_server：把平台能力经 Model Context Protocol 暴露给 AI Agent。

索引+引用服务（D-005/D-006）：只返元数据与 ArtifactRef，不返正文/源码/
二进制/密钥，不代理下载。数据源为公开采集样本；未实测 Skill 只返 D/U
证据等级（D-008）。
"""

from mcp_server.errors import McpToolError
from mcp_server.index import InMemorySkillIndex
from mcp_server.models import (
    ArtifactRefDTO,
    SkillDetail,
    SkillSummary,
    TrialReportSummary,
)

__all__ = [
    "ArtifactRefDTO",
    "InMemorySkillIndex",
    "McpToolError",
    "SkillDetail",
    "SkillSummary",
    "TrialReportSummary",
]
