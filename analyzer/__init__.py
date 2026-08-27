"""analyzer：静态检测层 PoC。

对已取得元数据/清单的候选做只读、声明级扫描：结构、许可信号、权限声明、
密钥启发、依赖清单。只产出 RuleFinding / StaticReviewReport，不下载制品
正文、不跑沙箱、不评分、不驱动状态机（QUARANTINED/STATIC_REVIEWED 的
转移由消费方根据 findings 触发）。
"""

from analyzer.errors import AnalyzerError
from analyzer.pipeline import StaticReviewReport, static_review
from analyzer.rules import RuleFinding, RuleId, RuleOutcome

__all__ = [
    "AnalyzerError",
    "RuleFinding",
    "RuleId",
    "RuleOutcome",
    "StaticReviewReport",
    "static_review",
]
