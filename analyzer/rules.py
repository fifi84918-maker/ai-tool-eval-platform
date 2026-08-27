"""规则标识、结论与发现（finding）形状。

对应 PRD 12.3 静态检测输出六分类的采集侧映射：
PASS=通过 / FAIL=阻断候选信号 / WARN=警告 / INFO=情报 /
NEED_INFO=无法判断或需作者补充（人工复核由消费方基于 findings 决定）。
EvidenceGrade 不在本层赋值。
"""

from dataclasses import dataclass, field
from enum import Enum

from core.schema.test_run import EvidenceRef


class RuleId(str, Enum):
    # 结构与规范（PRD 12.2-A）
    STRUCT_SKILL_MD_PRESENT = "struct.skill_md_present"
    STRUCT_FRONTMATTER_FIELDS = "struct.frontmatter_fields"
    STRUCT_PORTABLE_PATHS = "struct.portable_paths"
    STRUCT_PLACEHOLDERS = "struct.placeholders"
    # 许可与来源（PRD 12.2-F）
    LICENSE_PRESENT = "license.present"
    LICENSE_TEST_RIGHTS = "license.test_rights"
    LICENSE_PUBLIC_RESULT_RIGHTS = "license.public_result_rights"
    LICENSE_RETAIN_RIGHTS = "license.retain_rights"
    # 权限与数据流（PRD 12.2-D）
    PERM_UNKNOWN_SCOPE = "perm.unknown_scope"
    PERM_HIGH_RISK = "perm.high_risk"
    PERM_NONE_DECLARED = "perm.none_declared"
    # 安全启发（PRD 12.2-E 的元数据级子集）
    SECRET_METADATA_HEURISTIC = "secret.metadata_heuristic"
    # 依赖（PRD 12.2-C）
    DEPS_MANIFEST_FORMAT = "deps.manifest_format"
    DEPS_UNTRUSTED_SOURCE = "deps.untrusted_source"
    # 流水线兜底
    PIPELINE_RULE_CRASH = "pipeline.rule_crash"


class RuleOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"            # 阻断候选信号；是否 QUARANTINED 由消费方决定
    WARN = "warn"
    INFO = "info"
    NEED_INFO = "need_info"  # 无法判断 / 需作者补充 / 需人工复核


@dataclass(frozen=True)
class RuleFinding:
    """单条检测发现。message 只含声明级信息，不得包含制品正文片段。"""

    rule_id: RuleId
    outcome: RuleOutcome
    message: str
    evidence_refs: tuple[EvidenceRef, ...] = field(default_factory=tuple)
