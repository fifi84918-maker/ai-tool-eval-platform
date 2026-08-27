"""共享枚举。口径来源：PRD v1.0（docs/prd.md），冲突时以 PRD 为准。"""

from enum import Enum


class SourceKind(str, Enum):
    """首期六类来源（PRD 7.2）。"""

    GITHUB = "github"
    HUGGING_FACE = "hugging_face"
    WORKBUDDY_MARKET = "workbuddy_market"
    QIANWEN_OFFICE = "qianwen_office"
    DOUBAO_WORK = "doubao_work"
    CREATOR_SUBMISSION = "creator_submission"


class EntityType(str, Enum):
    """三类能力分开建模，不混口径（D-011）。"""

    SKILL = "skill"
    CONNECTOR_MCP = "connector_mcp"
    EXPERT = "expert"


class LicenseClass(str, Enum):
    """许可证分级结论（详细 SPDX 标识存于字段，此处仅平台侧使用分级）。"""

    PERMISSIVE = "permissive"          # 允许测试与公开衍生结果
    RESTRICTED = "restricted"          # 有限使用：测后删副本，仅留哈希与结果
    UNKNOWN = "unknown"                # 未识别，须标记且需人工复核
    BLOCKED = "blocked"                # 明确禁止测试或展示


class PermScope(str, Enum):
    """权限声明范围（PRD 12.2-D）。"""

    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    SHELL_EXEC = "shell_exec"
    NETWORK = "network"
    BROWSER_CONTROL = "browser_control"
    MESSAGING_SEND = "messaging_send"
    CONTENT_PUBLISH = "content_publish"
    PAYMENT = "payment"
    APPROVAL = "approval"
    CAMERA_MIC_SCREEN = "camera_mic_screen"
    PERSONAL_DATA = "personal_data"
    CREDENTIALS = "credentials"


class EvidenceGrade(str, Enum):
    """证据等级（PRD 15.4）：A/B/C/D/U，无其他等级。"""

    A = "A"
    B = "B"
    C = "C"
    D = "D"   # 仅静态/兼容推断，不得展示动态效果结论
    U = "U"   # 尚未验证


class ScoreDimension(str, Enum):
    """八维评分（PRD 15.3；默认权重仅默认场景适用）。"""

    TASK_EFFECT = "task_effect"                  # 35%
    STABILITY = "stability"                      # 15%
    TRIGGER_QUALITY = "trigger_quality"          # 10%
    PERMISSION_PRIVACY = "permission_privacy"    # 10%
    COST_EFFICIENCY = "cost_efficiency"          # 10%
    PLATFORM_COMPAT = "platform_compat"          # 10%
    MAINTAINABILITY = "maintainability"          # 5%
    DOC_EXPLAINABILITY = "doc_explainability"    # 5%


class BundleTier(str, Enum):
    """三档 Bundle 方案（PRD 18.5）。"""

    LIGHT = "light"
    BALANCED = "balanced"
    ENHANCED = "enhanced"


class CompatStatus(str, Enum):
    """7 种兼容状态（PRD 17.3）；无加载/冒烟证据不得标 COMPATIBLE。"""

    NATIVE = "native"
    COMPATIBLE = "compatible"
    ADAPTABLE = "adaptable"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"
    UNVERIFIED = "unverified"
