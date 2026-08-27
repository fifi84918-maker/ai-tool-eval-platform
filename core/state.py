"""11 态收录状态机（PRD 6.3）：枚举 + 合法转移表 + 纯转移函数。

口径说明（Task 03 评审已确认）：
- 状态命名采用 PRD 6.3 的 11 态（冲突裁决顺序 PRD 优先）。
- STALE 回流：允许经 REFRESH 事件直接回 NEUTRAL_TESTED，不重走静态检测
  （STALE 通常只是版本/环境过期，结构未变）。
- QUARANTINED 可经人工复核（QUARANTINE_LIFTED）回 STATIC_REVIEWED。
- VERIFIED 门槛（证据等级 A/B）由评分层判定，状态机只接受
  EVIDENCE_THRESHOLD_MET 事件，不内置阈值。
- REMOVED 为终态，无恢复路径。

TODO(Phase 2)：NATIVE_TESTED 状态保留，但 Phase 0 不引入原生 Worker，
暂不定义其转入/转出路径（RUNNABLE 不允许直达 NATIVE_TESTED）。当前仅
保留 SOURCE_REMOVED 出边以维持"任何非终态都可下架"的全局不变量；
NATIVE_TEST_DONE 事件保留枚举位，无任何转移使用它。
"""

from enum import Enum


class SkillStatus(str, Enum):
    """PRD 6.3：每个 Skill 有且只有一个当前主状态。"""

    DISCOVERED = "DISCOVERED"
    METADATA_ONLY = "METADATA_ONLY"
    ACQUIRED = "ACQUIRED"
    STATIC_REVIEWED = "STATIC_REVIEWED"
    QUARANTINED = "QUARANTINED"
    RUNNABLE = "RUNNABLE"
    NEUTRAL_TESTED = "NEUTRAL_TESTED"
    NATIVE_TESTED = "NATIVE_TESTED"
    VERIFIED = "VERIFIED"
    STALE = "STALE"
    REMOVED = "REMOVED"


class StatusEvent(str, Enum):
    """显式转移事件。"""

    ARTIFACT_UNAVAILABLE = "artifact_unavailable"      # 仅取得元数据
    ARTIFACT_ACQUIRED = "artifact_acquired"            # 正常渠道取得测试副本
    STATIC_PASSED = "static_passed"                    # 静态检测通过
    STATIC_BLOCKED = "static_blocked"                  # 命中安全/许可阻断
    QUARANTINE_LIFTED = "quarantine_lifted"            # 人工复核解除隔离
    ADMISSION_PASSED = "admission_passed"              # 动态测试准入通过（PRD 13.1）
    NEUTRAL_TEST_DONE = "neutral_test_done"            # 完成中立环境测试
    NATIVE_TEST_DONE = "native_test_done"              # TODO(Phase 2)：暂无转移使用
    EVIDENCE_THRESHOLD_MET = "evidence_threshold_met"  # 达到规定证据等级
    ENV_OR_VERSION_EXPIRED = "env_or_version_expired"  # 版本或测试环境过期
    REFRESH = "refresh"                                # STALE 复测通过，回流已测状态
    SOURCE_REMOVED = "source_removed"                  # 来源删除/撤回/停止展示


# 合法转移表：{当前状态: {事件: 下一状态}}。不在表中的组合一律非法。
_TRANSITIONS: dict[SkillStatus, dict[StatusEvent, SkillStatus]] = {
    SkillStatus.DISCOVERED: {
        StatusEvent.ARTIFACT_UNAVAILABLE: SkillStatus.METADATA_ONLY,
        StatusEvent.ARTIFACT_ACQUIRED: SkillStatus.ACQUIRED,
        StatusEvent.SOURCE_REMOVED: SkillStatus.REMOVED,
    },
    SkillStatus.METADATA_ONLY: {
        StatusEvent.ARTIFACT_ACQUIRED: SkillStatus.ACQUIRED,
        StatusEvent.SOURCE_REMOVED: SkillStatus.REMOVED,
    },
    SkillStatus.ACQUIRED: {
        StatusEvent.STATIC_PASSED: SkillStatus.STATIC_REVIEWED,
        StatusEvent.STATIC_BLOCKED: SkillStatus.QUARANTINED,
        StatusEvent.SOURCE_REMOVED: SkillStatus.REMOVED,
    },
    SkillStatus.STATIC_REVIEWED: {
        StatusEvent.ADMISSION_PASSED: SkillStatus.RUNNABLE,
        StatusEvent.STATIC_BLOCKED: SkillStatus.QUARANTINED,
        StatusEvent.SOURCE_REMOVED: SkillStatus.REMOVED,
    },
    SkillStatus.QUARANTINED: {
        StatusEvent.QUARANTINE_LIFTED: SkillStatus.STATIC_REVIEWED,
        StatusEvent.SOURCE_REMOVED: SkillStatus.REMOVED,
    },
    SkillStatus.RUNNABLE: {
        StatusEvent.NEUTRAL_TEST_DONE: SkillStatus.NEUTRAL_TESTED,
        StatusEvent.STATIC_BLOCKED: SkillStatus.QUARANTINED,
        StatusEvent.SOURCE_REMOVED: SkillStatus.REMOVED,
    },
    SkillStatus.NEUTRAL_TESTED: {
        StatusEvent.EVIDENCE_THRESHOLD_MET: SkillStatus.VERIFIED,
        StatusEvent.ENV_OR_VERSION_EXPIRED: SkillStatus.STALE,
        StatusEvent.STATIC_BLOCKED: SkillStatus.QUARANTINED,
        StatusEvent.SOURCE_REMOVED: SkillStatus.REMOVED,
    },
    # TODO(Phase 2)：原生 Worker 上线后补充转入/转出路径。
    SkillStatus.NATIVE_TESTED: {
        StatusEvent.SOURCE_REMOVED: SkillStatus.REMOVED,
    },
    SkillStatus.VERIFIED: {
        StatusEvent.ENV_OR_VERSION_EXPIRED: SkillStatus.STALE,
        StatusEvent.STATIC_BLOCKED: SkillStatus.QUARANTINED,
        StatusEvent.SOURCE_REMOVED: SkillStatus.REMOVED,
    },
    SkillStatus.STALE: {
        StatusEvent.REFRESH: SkillStatus.NEUTRAL_TESTED,
        StatusEvent.SOURCE_REMOVED: SkillStatus.REMOVED,
    },
    SkillStatus.REMOVED: {},  # 终态
}


class IllegalTransitionError(ValueError):
    """在当前状态下事件不合法。"""

    def __init__(self, current: SkillStatus, event: StatusEvent) -> None:
        super().__init__(f"illegal transition: {current.value} --{event.value}-->")
        self.current = current
        self.event = event


def transition(current: SkillStatus, event: StatusEvent) -> SkillStatus:
    """纯函数：返回事件驱动后的下一状态；非法组合抛 IllegalTransitionError。"""
    try:
        return _TRANSITIONS[current][event]
    except KeyError:
        raise IllegalTransitionError(current, event) from None


def allowed_events(current: SkillStatus) -> frozenset[StatusEvent]:
    """当前状态下合法事件集合（纯查询，便于调用方预检）。"""
    return frozenset(_TRANSITIONS[current])
