"""状态事件驱动：按序消费 core.state.transition，非法转移记录不中断。"""

from collections.abc import Iterable
from dataclasses import dataclass, field

from core.state import IllegalTransitionError, SkillStatus, StatusEvent, transition


@dataclass(frozen=True)
class DriveResult:
    """一次事件序列驱动的结果。

    applied：(事件, 转移后状态) 序列；rejected：(当时状态, 非法事件) 序列。
    """

    final_status: SkillStatus
    applied: tuple[tuple[StatusEvent, SkillStatus], ...] = field(default_factory=tuple)
    rejected: tuple[tuple[SkillStatus, StatusEvent], ...] = field(default_factory=tuple)


def drive_status(current: SkillStatus, events: Iterable[StatusEvent]) -> DriveResult:
    """依序应用事件；IllegalTransitionError 记入 rejected 并继续后续事件。"""
    applied: list[tuple[StatusEvent, SkillStatus]] = []
    rejected: list[tuple[SkillStatus, StatusEvent]] = []
    status = current
    for event in events:
        try:
            status = transition(status, event)
            applied.append((event, status))
        except IllegalTransitionError:
            rejected.append((status, event))
    return DriveResult(
        final_status=status, applied=tuple(applied), rejected=tuple(rejected)
    )
