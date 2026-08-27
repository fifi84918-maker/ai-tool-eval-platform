"""compliance：许可/权利复核占位（Task 07 评审决策）。

只有协议与 stub，不实现真实服务、不接 DB/API。orchestrator 的
rights_override 注入口后续将由 RightsReviewer 实现方替代。
"""

from compliance.protocol import RightsDecision, RightsReviewer
from compliance.stub_reviewer import StubRightsReviewer

__all__ = [
    "RightsDecision",
    "RightsReviewer",
    "StubRightsReviewer",
]
