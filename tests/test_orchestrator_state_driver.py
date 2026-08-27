"""状态事件驱动测试。"""

from core.state import SkillStatus, StatusEvent
from orchestrator.state_driver import drive_status


class TestDriveStatus:
    def test_happy_sequence(self):
        result = drive_status(
            SkillStatus.DISCOVERED,
            [
                StatusEvent.ARTIFACT_ACQUIRED,
                StatusEvent.STATIC_PASSED,
                StatusEvent.ADMISSION_PASSED,
                StatusEvent.NEUTRAL_TEST_DONE,
            ],
        )
        assert result.final_status is SkillStatus.NEUTRAL_TESTED
        assert len(result.applied) == 4 and not result.rejected

    def test_illegal_event_recorded_not_raised(self):
        result = drive_status(
            SkillStatus.DISCOVERED,
            [
                StatusEvent.NEUTRAL_TEST_DONE,   # 非法：跳过前置
                StatusEvent.ARTIFACT_ACQUIRED,   # 合法，应继续被应用
            ],
        )
        assert result.final_status is SkillStatus.ACQUIRED
        assert result.rejected == (
            (SkillStatus.DISCOVERED, StatusEvent.NEUTRAL_TEST_DONE),
        )

    def test_terminal_removed_reachable_and_sticky(self):
        result = drive_status(
            SkillStatus.ACQUIRED,
            [StatusEvent.SOURCE_REMOVED, StatusEvent.STATIC_PASSED],
        )
        assert result.final_status is SkillStatus.REMOVED
        # 终态后的事件全部被拒绝记录
        assert result.rejected == ((SkillStatus.REMOVED, StatusEvent.STATIC_PASSED),)

    def test_empty_events_noop(self):
        result = drive_status(SkillStatus.RUNNABLE, [])
        assert result.final_status is SkillStatus.RUNNABLE
        assert not result.applied and not result.rejected
