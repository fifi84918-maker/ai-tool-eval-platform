"""core 契约测试：仅覆盖状态机转移与 ID 纯函数，不测业务规则。"""

import pytest

from core.ids import dir_hash, sha256_hex, stable_skill_id
from core.state import (
    IllegalTransitionError,
    SkillStatus,
    StatusEvent,
    allowed_events,
    transition,
)


class TestIds:
    def test_sha256_deterministic(self):
        assert sha256_hex("abc") == sha256_hex("abc")
        assert sha256_hex(b"abc") == sha256_hex("abc")

    def test_sha256_known_vector(self):
        # SHA-256("abc") 标准测试向量
        assert (
            sha256_hex("abc")
            == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )

    def test_stable_skill_id_deterministic_and_distinct(self):
        a = stable_skill_id("github", "owner/repo")
        assert a == stable_skill_id("github", "owner/repo")
        assert a != stable_skill_id("hugging_face", "owner/repo")
        # 分隔符防拼接歧义：("ab","c") 与 ("a","bc") 不同
        assert stable_skill_id("ab", "c") != stable_skill_id("a", "bc")

    def test_dir_hash_order_independent(self):
        h1 = sha256_hex("file-1")
        h2 = sha256_hex("file-2")
        assert dir_hash([("a.md", h1), ("b.py", h2)]) == dir_hash(
            [("b.py", h2), ("a.md", h1)]
        )

    def test_dir_hash_content_sensitive(self):
        h1 = sha256_hex("file-1")
        h2 = sha256_hex("file-2")
        assert dir_hash([("a.md", h1)]) != dir_hash([("a.md", h2)])


class TestStateMachine:
    def test_happy_path_to_verified(self):
        s = SkillStatus.DISCOVERED
        for event, expected in [
            (StatusEvent.ARTIFACT_ACQUIRED, SkillStatus.ACQUIRED),
            (StatusEvent.STATIC_PASSED, SkillStatus.STATIC_REVIEWED),
            (StatusEvent.ADMISSION_PASSED, SkillStatus.RUNNABLE),
            (StatusEvent.NEUTRAL_TEST_DONE, SkillStatus.NEUTRAL_TESTED),
            (StatusEvent.EVIDENCE_THRESHOLD_MET, SkillStatus.VERIFIED),
        ]:
            s = transition(s, event)
            assert s is expected

    def test_metadata_only_then_acquired(self):
        s = transition(SkillStatus.DISCOVERED, StatusEvent.ARTIFACT_UNAVAILABLE)
        assert s is SkillStatus.METADATA_ONLY
        assert transition(s, StatusEvent.ARTIFACT_ACQUIRED) is SkillStatus.ACQUIRED

    def test_quarantine_and_lift(self):
        s = transition(SkillStatus.ACQUIRED, StatusEvent.STATIC_BLOCKED)
        assert s is SkillStatus.QUARANTINED
        assert (
            transition(s, StatusEvent.QUARANTINE_LIFTED) is SkillStatus.STATIC_REVIEWED
        )

    def test_stale_refresh_back_to_neutral_tested(self):
        # 已确认决策：STALE 经 REFRESH 直接回 NEUTRAL_TESTED，不重走静态检测
        s = transition(SkillStatus.VERIFIED, StatusEvent.ENV_OR_VERSION_EXPIRED)
        assert s is SkillStatus.STALE
        assert transition(s, StatusEvent.REFRESH) is SkillStatus.NEUTRAL_TESTED

    def test_native_tested_deferred_to_phase2(self):
        # TODO(Phase 2)：RUNNABLE 不允许直达 NATIVE_TESTED；
        # NATIVE_TEST_DONE 事件当前不被任何状态接受
        with pytest.raises(IllegalTransitionError):
            transition(SkillStatus.RUNNABLE, StatusEvent.NATIVE_TEST_DONE)
        for status in SkillStatus:
            if status is SkillStatus.REMOVED:
                continue
            assert StatusEvent.NATIVE_TEST_DONE not in allowed_events(status)
        # NATIVE_TESTED 保留下架出边
        assert allowed_events(SkillStatus.NATIVE_TESTED) == frozenset(
            {StatusEvent.SOURCE_REMOVED}
        )

    def test_removed_is_terminal(self):
        assert allowed_events(SkillStatus.REMOVED) == frozenset()
        for event in StatusEvent:
            with pytest.raises(IllegalTransitionError):
                transition(SkillStatus.REMOVED, event)

    def test_illegal_transition_raises(self):
        with pytest.raises(IllegalTransitionError):
            transition(SkillStatus.DISCOVERED, StatusEvent.NEUTRAL_TEST_DONE)
        with pytest.raises(IllegalTransitionError):
            transition(SkillStatus.METADATA_ONLY, StatusEvent.STATIC_PASSED)

    def test_reachability_from_discovered(self):
        # BFS 遍历转移表：Phase 0 中除 NATIVE_TESTED（TODO(Phase 2) 无转入边）
        # 外全部可达
        reachable = {SkillStatus.DISCOVERED}
        frontier = [SkillStatus.DISCOVERED]
        while frontier:
            current = frontier.pop()
            for event in allowed_events(current):
                nxt = transition(current, event)
                if nxt not in reachable:
                    reachable.add(nxt)
                    frontier.append(nxt)
        assert reachable == set(SkillStatus) - {SkillStatus.NATIVE_TESTED}

    def test_source_removed_allowed_from_all_non_terminal_states(self):
        for status in SkillStatus:
            if status is SkillStatus.REMOVED:
                continue
            assert transition(status, StatusEvent.SOURCE_REMOVED) is SkillStatus.REMOVED
